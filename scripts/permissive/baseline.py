"""Local-only read-only source protection. Never runs application migrations."""
import hashlib
import json
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/permissive-20261102'
PROJECT = ROOT.parent / '示例项目/IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2'

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def snapshot(label):
    OUT.mkdir(parents=True, exist_ok=True)
    target = OUT / (label + '.json')
    if target.exists():
        raise RuntimeError('Evidence already exists')
    with sqlite3.connect((PROJECT / 'project.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        tables = {}
        for (name,) in db.execute("select name from sqlite_master where type='table' order by name"):
            tables[name] = sorted([dict(r) for r in db.execute('select * from "' + name.replace('"', '""') + '"')], key=lambda r: json.dumps(r, sort_keys=True))
        if label == 'before':
            with sqlite3.connect(OUT / 'original.backup.sqlite') as backup:
                db.backup(backup)
    files = {str(p): sha(p) for p in PROJECT.rglob('*') if p.is_file() and p.name not in {'project.sqlite', 'project.sqlite-wal', 'project.sqlite-shm'}}
    for record in tables.get('media_assets', []):
        p = Path(record.get('original_path') or '')
        if p.is_file():
            files[str(p)] = sha(p)
    # Capture pre-existing dirty work without staging it or committing private assets.
    initial = OUT / 'dirty-files.json'
    if label == 'before':
        names = subprocess.check_output(['git', 'ls-files', '-m', '-o', '--exclude-standard'], cwd=ROOT, text=True).splitlines()
        initial.write_text(json.dumps({n: sha(ROOT / n) for n in names if (ROOT / n).is_file() and not n.startswith('scripts/permissive/')}, indent=2), encoding='utf8')
        (OUT / 'tracked-before.patch').write_bytes(subprocess.check_output(['git', 'diff', '--binary'], cwd=ROOT))
    dirty = json.loads(initial.read_text(encoding='utf8'))
    preserved = {name: sha(ROOT / name) == value for name, value in dirty.items()}
    result = dict(tables=tables, files=files, dirty_preserved=preserved)
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    if label != 'before':
        before = json.loads((OUT / 'before.json').read_text(encoding='utf8'))
        assert before['tables'] == tables and before['files'] == files and all(preserved.values())
    print(json.dumps({'snapshot': label, 'protected_files': len(files), 'tables': {k: len(v) for k, v in tables.items()}, 'dirty_preserved': all(preserved.values())}))

if __name__ == '__main__':
    snapshot(sys.argv[1])
