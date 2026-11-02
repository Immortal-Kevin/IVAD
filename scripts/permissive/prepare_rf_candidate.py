"""Create an isolated, NON-DISTRIBUTABLE RF media-removal candidate.

No old environment changes. This is NOT the final permissive runtime:
certifi/tqdm and unresolved native notices still block license acceptance.
"""
import hashlib
import json
import shutil
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / '.venv-rfdetr/Lib/site-packages'
TARGET = ROOT / '.venv-rf-media-candidate'
OUT = ROOT / 'artifacts/permissive-20261102/rf-environment.json'

def omit(directory, names):
    excluded = []
    for name in names:
        lower = name.lower()
        if lower in {'av','av.libs','__pycache__'} or lower.startswith('av-') and lower.endswith('.dist-info') or lower.startswith('opencv_videoio_ffmpeg'):
            excluded.append(name)
    return excluded

if __name__ == '__main__':
    if TARGET.exists() or OUT.exists():
        raise RuntimeError('Refusing to overwrite candidate or evidence')
    required = sum(p.stat().st_size for p in SOURCE.rglob('*') if p.is_file())
    if shutil.disk_usage(ROOT).free < required * 1.2:
        raise RuntimeError('Not enough free space for independent environment')
    venv.EnvBuilder(with_pip=False).create(TARGET)
    shutil.copytree(SOURCE, TARGET / 'Lib/site-packages', dirs_exist_ok=True, ignore=omit)
    excluded = []
    for p in SOURCE.rglob('*'):
        if p.is_file() and '__pycache__' not in p.parts and not (TARGET / 'Lib/site-packages' / p.relative_to(SOURCE)).exists():
            with p.open('rb') as f:
                excluded.append(dict(path=str(p.relative_to(SOURCE)), sha256=hashlib.file_digest(f,'sha256').hexdigest()))
    OUT.write_text(json.dumps(dict(source=str(SOURCE), target=str(TARGET), excluded=excluded,
                                   PACKAGING_FREEZE=True, DISTRIBUTION_STATUS='BLOCKED',
                                   remaining=['certifi MPL-2.0','tqdm MPL-2.0 AND MIT','native/license provenance gaps']), indent=2), encoding='utf8')
    print(json.dumps(dict(target=str(TARGET), excluded_files=len(excluded))))
