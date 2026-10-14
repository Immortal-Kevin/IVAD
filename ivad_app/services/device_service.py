"""硬件枚举、后端可用与历史实测状态分别报告。"""
import json, subprocess, threading, re
from dataclasses import asdict, replace
from pathlib import Path
from sqlalchemy import select, delete
from ivad_app.core.contracts import AppError, DeviceInfo, utc_now
from ivad_app.storage.models import DeviceRecord
from ivad_app.compute.registry import WorkerRegistry

CREATE_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0)

class NvidiaWorker:
    def __init__(self, root: Path, python: Path):
        self.root, self.python = root, python

    def _validated(self, raw: dict, device: dict) -> bool:
        try:
            folder = self.root / 'artifacts/p0'
            probe = json.loads((folder / 'cuda-probe.json').read_text(encoding='utf-8'))
            models = json.loads((folder / 'yolo-results.json').read_text(encoding='utf-8'))
            benchmark = json.loads((folder / 'benchmark-supplement.json').read_text(encoding='utf-8'))
            versions = dict(line.split('==', 1) for line in (folder / 'requirements-lock.txt').read_text(encoding='utf-8').splitlines() if '==' in line)
            smi = (folder / 'nvidia-smi-p0-complete.txt').read_text(encoding='utf-8-sig')
            return (probe['status'] == 'PASS' and probe['gpu'] == device['name'] and probe['torch'] == raw['torch']
                    and probe['cuda'] == raw['cuda'] and raw['ort'] == versions['onnxruntime-gpu']
                    and device['uuid'] in smi and bool(re.search(r'Driver Version\s*:\s*' + re.escape(device['driver']), smi))
                    and all(models[n]['ort_status'] == models[n]['train_status'] == benchmark['models'][n]['status'] == 'PASS' for n in ['yolo26n', 'yolo11n']))
        except (OSError, ValueError, KeyError, TypeError): return False

    def probe(self) -> list[DeviceInfo]:
        if not self.python.is_file():
            raise AppError('WORKER_MISSING', 'NVIDIA Worker解释器不存在，请在系统设置中选择项目GPU环境。')
        try:
            completed = subprocess.run([str(self.python), '-I', '-X', 'utf8', str(self.root / 'ivad_app/compute/nvidia_probe.py')], capture_output=True, text=True, encoding='utf-8', timeout=90, creationflags=CREATE_NO_WINDOW)
            if completed.returncode:
                raise AppError('WORKER_ERROR', 'NVIDIA Worker执行失败，请查看设备检查日志。')
            raw = json.loads(completed.stdout)
        except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
            raise AppError('WORKER_ERROR', 'GPU检查失败或超时，请核实Worker环境与驱动。') from exc
        rows = []
        for device in raw['devices']:
            available = bool(raw['available'] and device['cuda_tensor_verified'])
            ort_available = 'CUDAExecutionProvider' in raw.get('providers', [])
            validated = available and ort_available and self._validated(raw, device)
            details = dict(device, torch=raw.get('torch'), cuda=raw.get('cuda'), ort=raw.get('ort'), ort_available=ort_available,
                           ort_validated=bool(validated and ort_available), evidence='P0实际模型测试与当前软硬件匹配' if validated else '没有匹配的实际模型测试证据', checked_at=utc_now())
            rows.append(DeviceInfo('nvidia:' + device['uuid'], device['name'], 'NVIDIA CUDA / ORT CUDA', True, available, validated, 'Backend Validated' if validated else 'Backend Available' if available else 'Error', details))
        if not rows:
            raise AppError('GPU_MISSING', '未检测到可用NVIDIA GPU；AI任务不可用，不会降级CPU。')
        if raw.get('errors'):
            raise AppError('WORKER_ERROR', 'GPU运行库检查出错；AI任务不可用。')
        return rows

    def require_gpu(self, device_id: str) -> DeviceInfo:
        match = next((d for d in self.probe() if d.id == device_id and d.backend_available), None)
        if not match: raise AppError('GPU_UNAVAILABLE', '指定GPU不可用，禁止CPU-only fallback。')
        return match

class DeviceService:
    def __init__(self, db, settings, logs, root: Path, *, lite: bool = False):
        self.db, self.settings, self.logs, self.root = db, settings, logs, root
        self.lite = lite
        self.devices: list[DeviceInfo] = []
        self.lock = threading.RLock()
        self.workers = WorkerRegistry()
        self.workers.register('nvidia_cuda', NvidiaWorker)

    def probe(self) -> list[DeviceInfo]:
        # 耗时子进程不持有状态锁，GUI读取snapshot不等待GPU检查。
        prefs = self.settings.preferences()
        python = Path(prefs['worker_python']) if prefs.get('worker_python') else self.root / '.venv-nvidia/Scripts/python.exe'
        if self.lite:
            devices = self._hardware_only('P2 Lite 未提供AI Worker；仅检测硬件，不执行CUDA、训练或推理。')
            devices = [replace(device, status='Worker Not Installed' if device.hardware_detected else 'NOT TESTED', details=dict(device.details, worker_installed=False, cuda_test_status='NOT TESTED', evidence='仅硬件枚举；不能作为AI实测通过')) for device in devices]
        else:
            try:
                devices = self.workers.create('nvidia_cuda', self.root, python).probe()
            except AppError as exc:
                devices = self._hardware_only(exc.message)
                self.logs.exception('device', exc.message)
        intel_name, intel_detected = 'Intel GPU', False
        try:
            command = "Get-CimInstance Win32_VideoController | Where-Object Name -Match 'Intel' | Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
            raw = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command], capture_output=True, text=True, encoding='utf-8', timeout=15, creationflags=CREATE_NO_WINDOW)
            if raw.returncode == 0 and raw.stdout.strip():
                value = json.loads(raw.stdout)
                intel_name = ', '.join(value) if isinstance(value, list) else value
                intel_detected = True
        except (OSError, ValueError, subprocess.TimeoutExpired): pass
        devices.append(DeviceInfo('intel:unverified', intel_name, 'Intel XPU / OpenVINO GPU', intel_detected, False, False, 'Not Tested', {'evidence': 'Intel独立历史P0 BLOCKED；此环境不安装Intel运行库', 'checked_at': utc_now()}))
        with self.lock: self.devices = devices
        with self.db.transaction() as session:
            session.execute(delete(DeviceRecord))  # 只替换当前枚举缓存；历史检查保留日志。
            for device in devices:
                session.add(DeviceRecord(id=device.id, payload=asdict(device), checked_at=utc_now()))
        self.logs.write('device', '硬件/后端检查完成：' + '; '.join(d.name + ' / ' + d.status for d in devices))
        return list(devices)

    def _hardware_only(self, error: str) -> list[DeviceInfo]:
        """Worker失效时仍独立枚举物理GPU，不能混淆硬件与后端状态。"""
        try:
            raw = subprocess.check_output(['nvidia-smi', '--query-gpu=uuid,name,driver_version,memory.total,memory.free,memory.used', '--format=csv,noheader,nounits'], text=True, timeout=10, creationflags=CREATE_NO_WINDOW)
            rows = []
            for line in raw.strip().splitlines():
                uuid, name, driver, total, free, used = [v.strip() for v in line.split(',')]
                capability='NOT TESTED'
                try:
                    result=subprocess.run(['nvidia-smi','--id='+uuid,'--query-gpu=compute_cap','--format=csv,noheader'],capture_output=True,text=True,timeout=5,creationflags=CREATE_NO_WINDOW)
                    if result.returncode==0 and re.fullmatch(r'\d+\.\d+',result.stdout.strip()):capability=result.stdout.strip()
                except (OSError,subprocess.SubprocessError):pass
                rows.append(DeviceInfo('nvidia:' + uuid, name, 'NVIDIA CUDA / ORT CUDA', True, False, False, 'Error', {'driver': driver, 'total_mib': int(total), 'free_mib': int(free), 'used_mib': int(used), 'compute_capability':capability,'error': error, 'checked_at': utc_now()}))
            if rows: return rows
        except (OSError, ValueError, subprocess.SubprocessError): pass
        return [DeviceInfo('nvidia:error', 'NVIDIA检查失败', 'NVIDIA CUDA / ORT CUDA', False, False, False, 'Error', {'error': error, 'hardware_status': 'Not Verified', 'checked_at': utc_now()})]
    def snapshot(self) -> list[DeviceInfo]:
        with self.lock: return list(self.devices)

    def require_gpu(self, device_id: str) -> DeviceInfo:
        if self.lite:
            raise AppError('LITE_AI_DISABLED', 'P2 Lite 未启用AI Worker，禁止训练、推理和CPU-only fallback。')
        if not device_id:
            preferred = self.settings.preferences().get('preferred_gpu', '')
            device_id = preferred or next((d.id for d in self.snapshot() if d.id.startswith('nvidia:') and d.backend_available), '')
        if device_id.lower() == 'cpu':
            raise AppError('GPU_REQUIRED', '禁止CPU-only AI任务，不会自动降级CPU。')
        # 必须是本会话真实探测结果，不能仅凭数据库旧缓存运行AI。
        with self.lock:
            match = next((d for d in self.devices if d.id == device_id), None)
            if not match or not match.backend_available:
                raise AppError('GPU_UNAVAILABLE', '所选GPU后端不可用，AI任务已被拒绝。')
            return match
