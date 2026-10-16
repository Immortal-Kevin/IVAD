"""Isolated -I interpreter and intentional package contamination negative checks."""
import json,os,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-20261016';python=ROOT/'.venv-rfdetr/Scripts/python.exe'
probe="import sys,importlib.util,json;from importlib.metadata import distributions;print(json.dumps(dict(prefix=sys.prefix,path=sys.path,ultralytics_spec=str(importlib.util.find_spec('ultralytics')),packages=sorted(d.metadata['Name'] for d in distributions()))))"
env=dict(os.environ,PYTHONPATH=str(ROOT/'.venv-nvidia/Lib/site-packages'))
result=subprocess.run([str(python),'-I','-c',probe],env=env,capture_output=True,text=True,encoding='utf8',check=True)
clean=json.loads(result.stdout);assert clean['ultralytics_spec']=='None';assert not any(n.lower().startswith('ultralytics') for n in clean['packages']);assert not any('.venv-nvidia' in p for p in clean['path'])
fake=OUT/'intentional-contamination';(fake/'ultralytics').mkdir(parents=True,exist_ok=True);(fake/'ultralytics/__init__.py').write_text("raise RuntimeError('must never execute')",encoding='utf8')
work=OUT/'rejected-pollution';work.mkdir(exist_ok=True);request=work/'request.json';request.write_text(json.dumps(dict(work=str(work))),encoding='utf8')
wrapper="import sys,runpy;sys.path.insert(0,sys.argv.pop(1));sys.argv.pop(0);runpy.run_path(sys.argv[0],run_name='__main__')"
rejected=subprocess.run([str(python),'-I','-c',wrapper,str(fake),str(ROOT/'ivad_app/compute/rfdetr_train_worker.py'),str(request)],capture_output=True,text=True,encoding='utf8');r=json.loads((work/'result.json').read_text(encoding='utf8'))
assert r['status']=='BLOCKED' and 'forbidden packages' in r['error']
clean.update(pollution_negative=r,status='PASS',inherited_old_pythonpath_ignored=True)
(OUT/'zero-dependency.json').write_text(json.dumps(clean,ensure_ascii=False,indent=2),encoding='utf8');print('PASS: isolated environment and contaminated path rejection')
