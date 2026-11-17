"""A CUDA-only JSON-lines worker. Never imports IVAD databases, GUI or training."""
import sys
sys.dont_write_bytecode = True
for stream in (sys.stdin, sys.stdout, sys.stderr):
    if stream is not None and hasattr(stream, 'reconfigure'):
        stream.reconfigure(encoding='utf-8')
import argparse
import hashlib
import importlib.abc
import json
import math
import os
from pathlib import Path
import subprocess
import time
import traceback

WIRE = sys.stdout
sys.stdout = sys.stderr
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1',
                  DO_NOT_TRACK='1', TOKENIZERS_PARALLELISM='false', WANDB_DISABLED='true')

class OfflineBoundary(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'ultralytics', 'ultralytics_thop', 'ultralytics_platform', 'thop', 'rfdetr_plus'}:
            raise ImportError('演示程序禁止加载旧 YOLO / Plus：' + fullname)

sys.meta_path.insert(0, OfflineBoundary())
def audit(event, args):
    if event in {'socket.connect', 'socket.getaddrinfo', 'socket.bind'}:
        raise RuntimeError('离线演示禁止联网：' + event)
sys.addaudithook(audit)

def emit(kind, **data):
    WIRE.write(json.dumps(dict(event=kind, **data), ensure_ascii=False, allow_nan=False) + '\n')
    WIRE.flush()

def digest(path):
    with Path(path).open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--log-dir')
    args = parser.parse_args()
    if args.log_dir:
        from demo_rf.diagnostics import install, record
        install(args.log_dir, 'worker')
    import torch
    info = dict(torch=torch.__version__, torch_cuda=torch.version.cuda,
                cuda_available=torch.cuda.is_available(), cpu_fallback=False)
    try:
        driver = subprocess.run(['nvidia-smi', '--query-gpu=driver_version,name', '--format=csv,noheader'],
                                capture_output=True, text=True, timeout=8,
                                creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        info.update(driver_available=driver.returncode == 0, driver=driver.stdout.strip())
    except (OSError, subprocess.SubprocessError):
        info.update(driver_available=False, driver='未能调用nvidia-smi；以实际CUDA检查为准')
    if not info['cuda_available']:
        emit('error', message='NVIDIA CUDA不可用，请检查显卡和驱动；不会使用CPU神经网络推理。', gpu=info)
        return 2
    torch.cuda.set_device(0)
    props = torch.cuda.get_device_properties(0)
    free, total = torch.cuda.mem_get_info()
    info.update(name=props.name, compute_capability=list(torch.cuda.get_device_capability()),
                free_vram_bytes=free, total_vram_bytes=total, supported_arches=torch.cuda.get_arch_list())
    emit('gpu', gpu=info)
    if args.probe:
        return 0
    if free < 512 * 1024**2:
        raise RuntimeError('当前空闲显存不足512MiB，请关闭占用显存的程序后重试。')
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf8'))
    model = None
    entry = None
    forward_calls = [0]
    for line in sys.stdin:
        command = json.loads(line)
        if command['op'] == 'load':
            weights = Path(command['weights']).resolve(strict=True)
            sha = digest(weights)
            entry = next((m for m in manifest['models'] if m['sha256'] == sha), None)
            if entry is None or entry['architecture'] != 'RFDETRNano':
                raise ValueError('此模型未在本演示授权清单中；仅允许经核验SHA256的RF-DETR Nano权重。')
            from rfdetr import RFDETR, RFDETRNano
            from rfdetr.assets.coco_classes import COCO_CLASSES
            resolution = int(command.get('resolution', 384))
            if resolution not in {320, 384}:
                raise ValueError('仅允许Nano支持的320或384输入尺寸。')
            if entry['kind'] == 'public-coco':
                model = RFDETRNano(pretrain_weights=str(weights), device='cuda', resolution=resolution)
                class_map = COCO_CLASSES
                notice = '公共COCO通用模型，不代表煤厂故障识别能力。'
            elif entry['kind'] == 'company-authorized':
                model = RFDETR.from_checkpoint(weights, device='cuda', resolution=resolution)
                if not isinstance(model, RFDETRNano) or model.class_names != entry['class_names']:
                    raise ValueError('模型架构或类别与本次授权登记不一致。')
                class_map = dict(enumerate(model.class_names))
                notice = '实验模型 / 尚未经过现场验证。仅限金海泽地办公电脑本地演示，不向厂方提供软件副本。'
            else:
                raise ValueError('未经授权的权重类型。')
            model.model.model.to('cuda').eval()
            for parameter in model.model.model.parameters():
                parameter.requires_grad_(False)
            if any(not p.is_cuda for p in model.model.model.parameters()):
                raise RuntimeError('模型参数未全部位于CUDA；禁止CPU回退。')
            def proof(module, inputs):
                if any(not p.is_cuda for p in module.parameters()):
                    raise RuntimeError('检测到CPU模型前向，已停止。')
                forward_calls[0] += 1
            model.model.model.register_forward_pre_hook(proof)
            emit('loaded', weights_sha256=sha, architecture='RFDETRNano', resolution=resolution,
                 class_map=class_map, model_device='cuda:0', eval=True, gradients=False,
                 source=entry['source'], notice=notice)
        elif command['op'] == 'infer':
            if model is None:
                raise RuntimeError('模型尚未加载。')
            from PIL import Image
            with Image.open(command['image']) as image:
                image = image.convert('RGB')
                width, height = image.size
                torch.cuda.reset_peak_memory_stats()
                before = forward_calls[0]
                start = time.perf_counter()
                if args.log_dir: record(args.log_dir, 'worker', 'forward_start', frame_index=command['frame_index'])
                with torch.inference_mode():
                    detections = model.predict(image, threshold=float(command['threshold']), include_source_image=False)
                torch.cuda.synchronize()
                if args.log_dir: record(args.log_dir, 'worker', 'forward_complete', frame_index=command['frame_index'])
                milliseconds = (time.perf_counter()-start)*1000
            if forward_calls[0] <= before:
                raise RuntimeError('没有观察到真实CUDA模型前向。')
            objects = []
            background = 0
            names = detections.data.get('class_name', [])
            for i, (xyxy, confidence, cid) in enumerate(zip(detections.xyxy, detections.confidence, detections.class_id)):
                cid, confidence = int(cid), float(confidence)
                if cid not in class_map:
                    if i < len(names) and names[i] == '__background__':
                        background += 1
                        continue
                    raise ValueError('模型输出未知类别，拒绝伪造类别名称：'+str(cid))
                box = [float(x) for x in xyxy]
                if not all(math.isfinite(x) for x in box+[confidence]) or not 0 <= confidence <= 1:
                    raise ValueError('模型输出无效坐标或置信度。')
                x1, y1, x2, y2 = box
                if x1 > x2 or y1 > y2:
                    raise ValueError('模型输出反向框。')
                box = [max(0., min(width, x1)), max(0., min(height, y1)),
                       max(0., min(width, x2)), max(0., min(height, y2))]
                if box[0] >= box[2] or box[1] >= box[3]:
                    continue
                objects.append(dict(class_id=cid, category=class_map[cid], confidence=confidence, xyxy=box))
            forbidden = [n for n in sys.modules if n.split('.')[0] in {'ultralytics', 'rfdetr_plus'}]
            if forbidden:
                raise RuntimeError('禁止依赖被加载。')
            emit('prediction', frame_index=command['frame_index'], pts=command['pts'], time_base=command['time_base'],
                 time_seconds=command['time_seconds'], width=width, height=height, objects=objects,
                 inference_ms=milliseconds, cuda_forward_calls=forward_calls[0]-before,
                 peak_vram_bytes=torch.cuda.max_memory_allocated(), background_removed=background,
                 forbidden_modules=forbidden, device='cuda:0', actual_inference=True)
            del detections
        elif command['op'] == 'stop':
            break
        else:
            raise ValueError('未知Worker操作。')
    emit('stopped', loaded_modules=sorted(sys.modules), cuda_forward_calls=forward_calls[0])
    return 0

if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        message = '显存不足，Worker已停止并释放资源；请关闭其他GPU程序或改320输入后重试。' if 'out of memory' in str(exc).lower() else 'CUDA环境或模型处理失败：'+str(exc)
        traceback.print_exc(file=sys.stderr)
        # Process exit releases the CUDA context even if CUDA cleanup itself fails.
        if 'torch' in sys.modules:
            try: sys.modules['torch'].cuda.empty_cache()
            except Exception: traceback.print_exc(file=sys.stderr)
        emit('error', message=message, oom='out of memory' in str(exc).lower(), cpu_fallback=False)
        raise SystemExit(1)
