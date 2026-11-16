"""离线文件 hash/ABI 全通过才生成严格安装清单；本脚本不安装。"""
import hashlib
import json
from pathlib import Path
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'reports/raw'
entries = json.loads((RAW / 'p0_full_offline_manifest.json').read_text(encoding='utf-8'))
directories = [ROOT / 'artifacts/p0/wheels', ROOT / 'artifacts/p0/offline_drop']
tags = set(sys_tags())
missing = []
verified = []
requirements = []
for entry in entries:
    name, version, _, artifact_tags = parse_wheel_filename(entry['filename'])
    assert canonicalize_name(entry['package']) == name
    assert version == Version(entry['version'])
    assert tags & artifact_tags, f'不兼容 ABI: {entry["filename"]}'
    candidates = [folder / entry['filename'] for folder in directories if (folder / entry['filename']).exists()]
    if not candidates:
        missing.append(entry['filename'])
        continue
    path = candidates[0]
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    assert digest == entry['sha256'], f'SHA256 mismatch: {path}'
    verified.append(entry['filename'])
    requirements.append(path.resolve().as_uri() + ' --hash=sha256:' + digest)
result = dict(status='BLOCKED' if missing else 'PASS', verified_wheels=len(verified), missing=missing, install_executed=False)
(RAW / 'offline_verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
if not missing:
    (RAW / 'verified_install_requirements.txt').write_text('\n'.join(requirements)+'\n', encoding='utf-8')
print(json.dumps(result, indent=2))
raise SystemExit(2 if missing else 0)
