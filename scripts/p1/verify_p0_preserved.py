"""比对P1前P0根文件/报告hash与环境包快照，不改动P0。"""
import hashlib, json, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/p1'
result = {'root_files': [], 'reports': [], 'packages_unchanged': False}
for category, file in [('root_files', 'p0-assets-before.json'), ('reports', 'p0-reports-before.json')]:
    baseline = json.loads((OUT / file).read_text(encoding='utf-8-sig'))
    if isinstance(baseline, dict): baseline = [baseline]
    for row in baseline:
        path = Path(row['Path'])
        match = path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest().lower() == row['Hash'].lower()
        result[category].append({'relative_path': path.relative_to(ROOT).as_posix(), 'unchanged': match})
current = subprocess.check_output([str(ROOT / '.venv-nvidia/Scripts/python.exe'), '-m', 'pip', 'freeze'], text=True, encoding='utf-8')
before = (OUT / 'p0-packages-before.txt').read_text(encoding='utf-8-sig')
result['packages_unchanged'] = sorted(before.splitlines()) == sorted(current.splitlines())
result['status'] = 'PASS' if result['packages_unchanged'] and all(r['unchanged'] for category in ['root_files', 'reports'] for r in result[category]) else 'FAIL'
(OUT / 'p0-preservation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(result['status'], len(result['root_files']), 'P0 root files;', len(result['reports']), 'reports; packages unchanged:', result['packages_unchanged'])
raise SystemExit(0 if result['status'] == 'PASS' else 1)
