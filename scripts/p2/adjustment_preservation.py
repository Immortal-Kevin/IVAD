"""Read-only baseline check; writes exclusively to adjustment evidence."""
import json,hashlib,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'artifacts/p2-adjustment'
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads(path.read_text(encoding='utf-8-sig'))
results={}
rows=read(out/'baseline.json')
results['prior_p2_artifacts']=[{'path':r['path'],'unchanged':digest(ROOT/r['path'])==r['sha256']} for r in rows if r['path'].startswith('artifacts/')]
results['p2_reports_history']=[{'path':r['path'],'unchanged':digest(out/'history'/Path(r['path']).name)==r['sha256']} for r in rows if r['path'].startswith('reports/')]
rows=read(ROOT/'artifacts/p2/p1-assets-before.json')
results['p0_p1_history']=[{'path':r['path'],'unchanged':digest(ROOT/r['path'])==r['sha256']} for r in rows]
for name in ['p0-assets-before.json','p0-reports-before.json']:
    rows=read(ROOT/'artifacts/p1'/name);rows=[rows] if isinstance(rows,dict) else rows
    results[name]=[{'path':str(Path(r['Path']).relative_to(ROOT)),'unchanged':digest(Path(r['Path'])).lower()==r['Hash'].lower()} for r in rows]
for phase,venv,before in [('p0','.venv-nvidia',ROOT/'artifacts/p1/p0-packages-before.txt'),('p2','.venv-p1',ROOT/'requirements-p2-lock.txt')]:
    current=subprocess.check_output([str(ROOT/venv/'Scripts/python.exe'),'-m','pip','freeze'],text=True,encoding='utf-8')
    results[phase+'_packages_unchanged']=sorted(current.splitlines())==sorted(before.read_text(encoding='utf-8-sig').splitlines())
results['status']='PASS' if all(r['unchanged'] for key in ['prior_p2_artifacts','p2_reports_history','p0_p1_history','p0-assets-before.json','p0-reports-before.json'] for r in results[key]) and results['p0_packages_unchanged'] and results['p2_packages_unchanged'] else 'FAIL'
(out/'preservation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(results['status']);raise SystemExit(0 if results['status']=='PASS' else 1)
