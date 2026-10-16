"""Controlled fault injection against real services; not a real CUDA OOM claim."""
import json,sys,time,threading
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.core.application import ApplicationServices
OUT=ROOT/'artifacts/p37a-20261016';s=ApplicationServices(ROOT,OUT/'fault-runtime');results={}
try:
    project=s.projects.open(str(OUT/'project-copy'));gpu=s.training.rf_devices()[0].id
    payload=dict(root=project.root,model='rfdetr-nano',version_id='fd9a3ba2-ed9b-4698-8838-5002b036fef0',device_id=gpu,parameters={'epochs':1})
    before={r['id'] for r in s.models.versions(project.root)}
    for fault in ['oom','crash','parity']:
        class Child:
            returncode=0 if fault=='parity' else 1
            def __init__(self,args,**kwargs):
                req=json.loads(Path(args[-1]).read_text(encoding='utf8'))
                result=dict(status='PASS',protocol_sha256='bad',parity=dict(status='BLOCKED')) if fault=='parity' else dict(status='BLOCKED',oom=fault=='oom',error='CONTROLLED TEST FIXTURE '+fault)
                (Path(req['work'])/'result.json').write_text(json.dumps(result),encoding='utf8')
            def poll(self):return self.returncode
        with patch('ivad_app.services.rfdetr_training_service.subprocess.Popen',Child):
            jid=s.jobs.submit('p3_train',project.id,payload)
            while s.jobs.get(jid)['state'] not in {'FAILED','SUCCEEDED'}:time.sleep(.1)
            row=s.jobs.get(jid);assert row['state']=='FAILED';assert {r['id'] for r in s.models.versions(project.root)}==before
            results[fault]=dict(status='PASS',evidence='CONTROLLED INJECTION, not real CUDA fault',job_id=jid,error=row['error'])
    # Queue cancellation: keep the queue occupied without touching GPU.
    entered=threading.Event();release=threading.Event()
    def blocker(ctx,p):entered.set();release.wait(5);ctx.check();return {}
    s.jobs.register('p2_fixture',blocker);first=s.jobs.submit('p2_fixture');assert entered.wait(3)
    waiting=s.jobs.submit('p3_train',project.id,payload);s.jobs.cancel(waiting);release.set();s.jobs.queue.join()
    assert s.jobs.get(waiting)['state']=='CANCELLED';assert {r['id'] for r in s.models.versions(project.root)}==before
    results['queued_cancel']=dict(status='PASS',job_id=waiting)
    with patch.object(s.training.rf,'devices_snapshot',return_value=[]):
        try:s.training.configuration_preflight(payload);raise AssertionError('GPU absence accepted')
        except Exception as e:assert getattr(e,'code',None)=='RF_GPU'
    results['gpu_unavailable']=dict(status='PASS',evidence='CONTROLLED unavailable probe')
    results['original_models_present']=all(any(r['id']==mid for r in s.models.versions(project.root)) for mid in ['4a1c7df7-dec7-427b-8861-6b247ef3ebbd','dd2e7eec-2d1a-4840-8df4-4f6112ce805e','2814763f-1877-40b4-96e2-bccb396fbb6c'])
finally:s.close()
(OUT/'failure-checks.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(results,ensure_ascii=False))
