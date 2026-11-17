"""Read-only inventories, isolated interpreter pollution probe and crash provenance."""
import json,os,subprocess,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-closure-20261019'
code="""import json,sys,importlib.util
from importlib.metadata import distributions
print(json.dumps(dict(prefix=sys.prefix,path=sys.path,ultralytics=str(importlib.util.find_spec('ultralytics')),packages=sorted((d.metadata['Name'],d.version) for d in distributions()))))
"""
result={}
for name in ['.venv-p1','.venv-rfdetr','.venv-nvidia']:
    result[name]=json.loads(subprocess.check_output([str(ROOT/name/'Scripts/python.exe'),'-I','-c',code],text=True))
env=dict(os.environ,PYTHONPATH=str(ROOT/'.venv-nvidia/Lib/site-packages'))
pollution=json.loads(subprocess.check_output([str(ROOT/'.venv-rfdetr/Scripts/python.exe'),'-I','-c',code],env=env,text=True))
assert pollution['ultralytics']=='None' and not any('.venv-nvidia' in x for x in pollution['path'])
assert result['.venv-p1']['ultralytics']==result['.venv-rfdetr']['ultralytics']=='None'
result['pollution_probe']=pollution
(OUT/'environments.json').write_text(json.dumps(result,indent=2),encoding='utf8')
old=ROOT/'artifacts/p37a-20261016/regression.log'
(OUT/'original-crash-provenance.json').write_text(json.dumps(dict(path=str(old),sha256=hashlib.file_digest(old.open('rb'),'sha256').hexdigest(),size=old.stat().st_size,mtime=old.stat().st_mtime),indent=2),encoding='utf8')
print({n:dict(packages=len(r['packages']),ultralytics=r['ultralytics']) for n,r in result.items()})
