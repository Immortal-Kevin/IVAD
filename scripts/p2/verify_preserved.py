"""Read-only comparison of P0/P1 historical evidence and package baselines."""
import hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'artifacts/p2';results={}
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
baseline=json.loads((out/'p1-assets-before.json').read_text(encoding='utf-8-sig'))
results['p1_files']=[{'path':r['path'],'unchanged':(ROOT/r['path']).is_file() and digest(ROOT/r['path'])==r['sha256']} for r in baseline]
for name in ['p0-assets-before.json','p0-reports-before.json']:
    baseline=json.loads((ROOT/'artifacts/p1'/name).read_text(encoding='utf-8-sig'));baseline=[baseline] if isinstance(baseline,dict) else baseline
    results[name]=[{'path':str(Path(r['Path']).relative_to(ROOT)),'unchanged':Path(r['Path']).is_file() and digest(Path(r['Path'])).lower()==r['Hash'].lower()} for r in baseline]
for phase,venv,baseline in [('p0','.venv-nvidia',ROOT/'artifacts/p1/p0-packages-before.txt'),('p1','.venv-p1',out/'p1-packages-before.txt')]:
    current=subprocess.check_output([str(ROOT/venv/'Scripts/python.exe'),'-m','pip','freeze'],text=True,encoding='utf-8')
    previous=set(baseline.read_text(encoding='utf-8-sig').splitlines());now=set(current.splitlines())
    results[phase+'_packages']={'old_versions_preserved':previous<=now,'added':sorted(now-previous),'missing_or_changed':sorted(previous-now)}
results['status']='PASS' if all(r['unchanged'] for key in ['p1_files','p0-assets-before.json','p0-reports-before.json'] for r in results[key]) and all(results[p+'_packages']['old_versions_preserved'] for p in ['p0','p1']) else 'FAIL'
(out/'preservation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8');print(results['status']);raise SystemExit(0 if results['status']=='PASS' else 1)
