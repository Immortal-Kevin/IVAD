"""Compare both numeric environments on the exact same checkpoint and data."""
import hashlib,json,subprocess,sys
from pathlib import Path
repo=Path(__file__).resolve().parents[2]
request=Path(sys.argv[1]);candidate=Path(sys.argv[2]);out=Path(sys.argv[3]);out.mkdir(exist_ok=False)
base=json.loads(request.read_text(encoding='utf8'))
trained=json.loads((request.parent/'result.json').read_text(encoding='utf8'))
results={}
for name,python in [('baseline',repo/'.venv-rf-media-candidate/Scripts/python.exe'),('candidate',candidate)]:
    work=out/name;work.mkdir()
    req=dict(base,operation='validate',work=str(work),weights=trained['weights'],weights_sha256=trained['weights_sha256'])
    file=work/'request.json';file.write_text(json.dumps(req),encoding='utf8')
    with (work/'console-private.log').open('w',encoding='utf8') as log:
        subprocess.run([str(python),'-I','-X','utf8',str(repo/'ivad_app/compute/rfdetr_train_worker.py'),str(file)],stdout=log,stderr=log,check=True,timeout=300)
    results[name]=json.loads((work/'result.json').read_text(encoding='utf8'))
a,b=results.values();delta={k:abs(a['metrics'][k]-b['metrics'][k]) for k in a['metrics']}
result={'status':'PASS' if all(v<=1e-4 for v in delta.values()) and a['prediction_trace_sha256']==b['prediction_trace_sha256'] else 'FAIL',
    'delta':delta,'tolerance':1e-4,'same_prediction_trace':a['prediction_trace_sha256']==b['prediction_trace_sha256'],
    'weights_sha256':trained['weights_sha256'],'baseline_metrics':a['metrics'],'candidate_metrics':b['metrics'],
    'license_status':'BLOCKED','scope':'same frozen synthetic data, same checkpoint, CUDA validation; not industrial accuracy'}
(out/'comparison.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
assert result['status']=='PASS'
