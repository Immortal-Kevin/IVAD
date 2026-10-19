"""P37D read-only inventory/protection. Does not build or authorize delivery."""
import argparse
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/p37d-20261019'
ENVIRONMENTS = {'gui': '.venv-p1', 'rf': '.venv-rfdetr',
                'legacy': '.venv-nvidia', 'lite-build': '.venv-distribution'}


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write(name, value):
    target = OUT / name
    # Historical evidence must never be overwritten by a rerun.
    with target.open('x', encoding='utf8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def snapshot():
    historical = json.loads((ROOT / 'artifacts/p37a-closure-20261019/before.json').read_text(encoding='utf8'))
    source = Path(historical['root'])
    with sqlite3.connect((source / 'project.sqlite').as_uri() + '?mode=ro', uri=True) as db:
        db.row_factory = sqlite3.Row
        names = [r[0] for r in db.execute("select name from sqlite_master where type='table' order by name")]
        tables = {n: sorted([dict(r) for r in db.execute('select * from "' + n.replace('"', '""') + '"')],
                            key=lambda row: json.dumps(row, sort_keys=True)) for n in names}
    files = {str(p): sha(p) for p in source.rglob('*') if p.is_file()
             and p.name not in {'project.sqlite', 'project.sqlite-wal', 'project.sqlite-shm'}}
    for row in tables['media_assets']:
        path = Path(row['original_path']) if row.get('original_path') else None
        if path and path.is_file():
            files[str(path.resolve())] = sha(path)
    keep = ['docs/P37_IMPLEMENTATION_PLAN.md', 'reports/P36_GIT_CLOSEOUT_AND_P37_PLANNING.md',
            'artifacts/p37a-20261016/regression.log',
            'artifacts/p37a-closure-20261019/windows-events.json',
            'artifacts/p37a-closure-20261019/wer-details.txt']
    protected = {name: sha(ROOT / name) for name in keep}
    environments = {}
    for label, folder in ENVIRONMENTS.items():
        inventory = json.loads((ROOT / f'legal/licenses/p37l/{label}/inventory.json').read_text(encoding='utf8'))
        site = ROOT / folder / 'Lib/site-packages'
        paths = {site / row['path'] for row in inventory['native']}
        paths.update(site / notice['installed_path'] for pkg in inventory['packages'] for notice in pkg['notices'])
        paths.update(site.glob('*.dist-info/METADATA'))
        environments[label] = {str(p.resolve()): sha(p) for p in sorted(paths) if p.is_file()}
    branches = {name: subprocess.check_output(['git', 'rev-parse', name], cwd=ROOT, text=True).strip()
                for name in ['nvidia-first', 'feature/p37a-rfdetr-training']}
    return dict(tables=tables, files=files, protected=protected, environments=environments, branches=branches)


def plan():
    selected = {'alembic', 'av', 'greenlet', 'mako', 'markupsafe', 'numpy', 'pillow',
                'pyside6', 'pyside6_addons', 'pyside6_essentials', 'pyyaml', 'shiboken6',
                'sqlalchemy', 'typing_extensions'}
    inventory = json.loads((ROOT / 'legal/licenses/p37l/gui/inventory.json').read_text(encoding='utf8'))
    packages = [p for p in inventory['packages'] if p['component'].lower() in selected]
    return dict(status='INPUT_PLAN_ONLY_NOT_PAYLOAD',
                baseline=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                gui_packages=packages,
                qt_module_allowlist=['Qt6Core.dll', 'Qt6Gui.dll', 'Qt6Widgets.dll', 'Qt6Svg.dll', 'qwindows.dll'],
                qt_plugins='Image/style plugins require a separate measured allowlist; not yet approved.',
                excluded=['ultralytics', 'ultralytics-platform', 'ultralytics-thop', 'old YOLO workers',
                          'old environments', 'opencv video backend', 'private data', 'private weights',
                          'project catalog', 'recent paths', 'historical reports and screenshots'],
                rf_worker='NOT RESOLVED: retain RF GUI/Registry; no verified portable worker closure yet.',
                nvidia_payload='NOT SELECTED; no redistribution approval inferred from wheel installation.',
                findings=['av15.1 wheel has x264/x265 DLLs; must replace the linked binary closure.',
                          'Existing spec builds P2 Lite and must not be relabeled as a full P37D package.',
                          'Source RF preflight lacks fresh VRAM admission; target 4GB must remain unapproved.'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('mode', choices=['before', 'after', 'plan'])
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    if args.mode == 'plan':
        result = plan()
        write('D1-input-plan.json', result)
        print('Input plan only:', len(result['gui_packages']), 'GUI packages; not a candidate payload')
    elif args.mode == 'before':
        result = snapshot()
        write('protection-before.json', result)
        print('Read-only protection baseline:', len(result['files']), 'project/media files')
    else:
        current = snapshot()
        before = json.loads((OUT / 'protection-before.json').read_text(encoding='utf8'))
        write('protection-after.json', current)
        result = {key: before[key] == current[key] for key in before}
        result['file_count'] = len(current['files'])
        write('protection-result.json', result)
        print(result)
        if not all(result[key] for key in before):
            raise SystemExit('Protection mismatch; investigate without restoring/deleting user assets')


if __name__ == '__main__':
    main()
