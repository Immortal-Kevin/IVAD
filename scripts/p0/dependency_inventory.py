"""只读检查两环境和允许的本地 wheel 缓存，记录确切目标元数据。"""
import importlib.metadata
import json
import os
import subprocess
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = [('openvino', '2026.4.1', 'intel_infer / intel_train'), ('numpy', '2.5.4', 'intel_infer'), ('openvino-telemetry', '2025.2.0', 'intel_infer / intel_train'), ('torch', '2.14.1+xpu', 'intel_train'), ('torchvision', '0.29.1+xpu', 'intel_train')]


if __name__ == '__main__':
    result = dict(environments={}, targets=[], cache=[])
    for name in ['intel_infer', 'intel_train']:
        python = ROOT / '.venvs' / name / 'Scripts/python.exe'
        output = subprocess.check_output([str(python), '-c', 'import sys,json,importlib.metadata as m; print(json.dumps(dict(executable=sys.executable,prefix=sys.prefix,base_prefix=sys.base_prefix,packages={d.metadata["Name"]:d.version for d in m.distributions()})))'], timeout=15, text=True)
        result['environments'][name] = json.loads(output)
    cache = Path(os.environ['LOCALAPPDATA']) / 'pip/cache'
    for base in [cache, Path.home() / 'Downloads', ROOT / 'artifacts/p0/wheels']:
        candidates = list(base.rglob('*.whl')) if base == cache else list(base.glob('*.whl'))
        if base == cache:
            candidates += [p for p in base.rglob('*.body') if p.stat().st_size > 1024*1024]
        for path in candidates:
            try:
                if zipfile.is_zipfile(path):
                    with zipfile.ZipFile(path) as z:
                        names = [n for n in z.namelist() if n.endswith('.dist-info/WHEEL')]
                        result['cache'].append(dict(path=str(path), size=path.stat().st_size, wheel_metadata=[z.read(n).decode() for n in names]))
            except Exception as error:
                result['cache'].append(dict(path=str(path), error=str(error)))
    for package, version, environment in TARGETS:
        entry = dict(package=package, version=version, environment=environment, status='MISSING')
        if '+xpu' in version:
            entry.update(index=f'https://download.pytorch.org/whl/xpu/{package}/', abi='cp314', platform='win_amd64')
        else:
            with urllib.request.urlopen(f'https://pypi.org/pypi/{package}/{version}/json', timeout=10) as response:
                metadata = json.load(response)
            wheels = [a for a in metadata['urls'] if a['filename'].endswith('cp314-cp314-win_amd64.whl') or a['filename'].endswith('py3-none-any.whl')]
            entry['wheels'] = [dict(filename=a['filename'], url=a['url'], size=a['size'], sha256=a['digests']['sha256']) for a in wheels]
            entry['requires_dist'] = metadata['info']['requires_dist']
        result['targets'].append(entry)
        (ROOT / 'reports/raw/dependency_inventory_resume.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
        print(package, version, 'recorded', flush=True)

