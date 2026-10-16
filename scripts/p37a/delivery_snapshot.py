"""Capture test-copy records for reports, without editing projects."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.core.application import ApplicationServices
OUT=ROOT/'artifacts/p37a-20261016';s=ApplicationServices(ROOT,OUT/'delivery-read-runtime')
try:
    root=str(OUT/'project-copy');models=s.models.versions(root);runs=s.training.runs(root)
    selected=[r for r in runs if r.get('backend')=='rfdetr']
    results=[]
    for run in selected:
        result=run.get('result',{})
        results.append({k:run.get(k) for k in ['id','state','model_id','job_id','error','operation']}|{k:result.get(k) for k in ['metrics','seconds','peak_allocated_bytes','weights_sha256','protocol_sha256','prediction_trace_sha256','prediction_frames','evidence']})
    verify=[]
    for m in models:
        path,data=s.models.verify(m['id'],root);verify.append(dict(id=m['id'],model=m['model'],state=m['state'],sha256=data['sha256'],backend=data.get('backend','legacy'),dataset_sha256=data.get('dataset_sha256'),evaluation_protocol_sha256=data.get('evaluation_protocol_sha256')))
    (OUT/'delivery-snapshot.json').write_text(json.dumps(dict(runs=results,models=verify),ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(models=len(models),rf_runs=len(selected),verified_models=len(verify))))
finally:s.close()
