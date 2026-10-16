"""Build an independent test copy from a read-only baseline; no original writes."""
import json,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'artifacts/p37a-20261016'
inventory=json.loads((out/'before/inventory.json').read_text(encoding='utf8'))
source=Path(inventory['root']);target=out/'project-copy'
if target.exists():raise SystemExit('Copy exists; refusing overwrite')
target.mkdir()
shutil.copyfile(out/'before/project.backup.sqlite',target/'project.sqlite')
shutil.copyfile(source/'project.json',target/'project.json')
for name in ['datasets','models','frames']:
    if (source/name).exists():shutil.copytree(source/name,target/name)
for row in inventory['tables']['model_versions']:
    details=json.loads(row['details'])
    if details.get('onnx'):
        relative=details['onnx']['path'];src=(source/relative).resolve();dst=(target/relative).resolve()
        assert src.is_relative_to(source.resolve()) and dst.is_relative_to(target.resolve())
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
(target/'evidence').mkdir(exist_ok=True)
(out/'test-project.json').write_text(json.dumps(dict(root=str(target),original=str(source)),ensure_ascii=False,indent=2),encoding='utf8')
print(target)
