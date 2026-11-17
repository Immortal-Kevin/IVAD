"""Read every installed distribution and hash every DLL/PYD; never install anything."""
from importlib import metadata
from pathlib import Path
import ctypes,hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[2];label=sys.argv[1];out=ROOT/'artifacts/p37a-20261016/license-audit'
subprocess.run([sys.executable,str(ROOT/'scripts/audit_release_dependencies.py'),'--label',label+'-all','--output',str(out),'--roots',*[d.metadata['Name'] for d in metadata.distributions() if d.metadata.get('Name')]],check=True)
inventory=json.loads((out/(label+'-all')/'inventory.json').read_text(encoding='utf8'));native=[]
for row in inventory['packages']:
    dist=metadata.distribution(row['name'])
    for entry in row['native_binaries']:
        path=Path(dist.locate_file(entry['path']));native.append(dict(component=row['name'],version=row['version'],path=entry['path'],sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),bytes=path.stat().st_size))
(out/(label+'-native.json')).write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(environment=label,packages=len(inventory['packages']),native=len(native))))
