"""One short CUDA run through the real job/registry services on the protected copy."""
import json,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.core.application import ApplicationServices
OUT=ROOT/'artifacts/p37a-20261016';copy=OUT/'project-copy'
s=ApplicationServices(ROOT,OUT/'service-runtime')
try:
    project=s.projects.open(str(copy));device=next(d for d in s.training.rf_devices() if d.backend_available)
    payload=dict(root=str(copy),version_id='fd9a3ba2-ed9b-4698-8838-5002b036fef0',model='rfdetr-nano',device_id=device.id,parameters={'epochs':1},operation='train')
    report=s.training.configuration_preflight(payload)
    jid=s.jobs.submit('p3_train',project.id,payload)
    (OUT/'active-service-job.json').write_text(json.dumps(dict(job_id=jid,payload=payload,preflight=report),indent=2),encoding='utf8')
    deadline=time.monotonic()+600
    while s.jobs.get(jid)['state'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:
        if time.monotonic()>deadline:s.jobs.cancel(jid);raise RuntimeError('Timed out')
        time.sleep(.5)
    result=s.jobs.get(jid);(OUT/'service-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));assert result['state']=='SUCCEEDED'
finally:s.close()
