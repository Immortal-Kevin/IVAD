"""Current data audit, independent exports and CUDA reload via production job facade."""
import json,shutil,sqlite3,sys,time,importlib.abc,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
OUT=ROOT/'artifacts/p37a-closure-20261019'
BASE=OUT
if len(sys.argv)>1:OUT=BASE/sys.argv[1];OUT.mkdir(exist_ok=False)
from ivad_app.services.backend_policy import classification
from ivad_app.core.application import ApplicationServices
from ivad_app.storage.project_store import file_hash
from tests.test_p2_media import Context

class NoUltralytics(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'ultralytics','ultralytics_thop','ultralytics_platform','thop','rfdetr_plus'}:
            raise RuntimeError('Forbidden import: '+fullname)
sys.meta_path.insert(0,NoUltralytics())
before=json.loads((BASE/'before.json').read_text(encoding='utf8'));source=Path(before['root']);copy=OUT/'project-copy'
copy.mkdir()
with sqlite3.connect((source/'project.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(copy/'project.sqlite') as dst:src.backup(dst)
shutil.copyfile(source/'project.json',copy/'project.json')
for name in ['datasets','models']:shutil.copytree(source/name,copy/name)
for row in before['tables']['model_versions']:
    details=json.loads(row['details'])
    if details.get('onnx'):
        relative=details['onnx']['path'];src=(source/relative).resolve();dst=(copy/relative).resolve()
        assert src.is_relative_to(source.resolve()) and dst.is_relative_to(copy.resolve())
        if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
s=ApplicationServices(ROOT,OUT/'runtime');report={}
try:
    p=s.projects.open(str(copy));runs=s.training.runs(str(copy),include_archived=True);models=s.models.versions(str(copy),include_archived=True)
    report['runs']=runs;report['models']=models
    report['counts']={kind:{c:sum(r['archive_classification']==c for r in rows) for c in ['ACTIVE_RFDETR','LEGACY_READ_ONLY','UNKNOWN']} for kind,rows in [('runs',runs),('models',models)]}
    vid=before['tables']['dataset_versions'][0]['id'];folder,snap,counts=s.training.rf.snapshot(vid,str(copy))
    frames={r['id']:r for r in before['tables']['frames']};media={r['id']:r for r in before['tables']['media_assets']};labels={c['uuid'] for c in snap['classes']}
    assert all(x.get('camera_id')==media[x['media_id']]['camera_id'] and x['media_id']==frames[x['frame_id']]['media_id'] for x in snap['samples'])
    assert all(o['label_id'] in labels for x in snap['samples'] for o in x['annotation']['objects'])
    report['dataset']=dict(version_id=vid,name=before['tables']['datasets'][0]['name'],images=len(snap['samples']),objects=sum(len(x['annotation']['objects']) for x in snap['samples']),normal=sum(x['annotation']['image_tag']=='NORMAL' for x in snap['samples']),split=counts,sha256=file_hash(folder/'manifest.json'),camera_media_frame_links=True,class_map=snap['classes'])
    assert report['dataset']['images']==200 and report['dataset']['objects']==402
    report['exports']=[]
    for fmt in ['ivad_native','coco']:
        result=s.datasets.export(Context(),dict(root=str(copy),version_id=vid,format=fmt,parent=str(OUT)))
        target=Path(result['path']);native=json.loads((target/'ivad_native.json').read_text(encoding='utf8'))
        assert len(native['samples'])==200 and sum(len(x['annotation']['objects']) for x in native['samples'])==402
        if fmt=='coco':
            docs=[json.loads(x.read_text(encoding='utf8')) for x in target.glob('instances_*.json')]
            assert sum(len(x['images']) for x in docs)==200 and sum(len(x['annotations']) for x in docs)==402
        report['exports'].append(result)
    report['verified_models']=[dict(id=m['id'],sha256=file_hash(s.models.verify(m['id'],str(copy))[0])) for m in models]
    report['caches']=[]
    for path in sorted((source/'demos').glob('*/manifest.json')):
        try:
            cache=s.offline.load(path.parent);report['caches'].append(dict(path=str(path.parent),status='PASS',model_id=cache['model_id'],frames=len(cache['frames'])))
        except Exception as exc:report['caches'].append(dict(path=str(path.parent),status='UNAVAILABLE',error=str(exc)))
    gpu=next(d for d in s.training.rf_devices() if d.backend_available)
    model=next(m for m in models if m['archive_classification']=='ACTIVE_RFDETR' and m.get('evaluation_protocol_sha256'))
    payload=dict(root=str(copy),version_id=vid,model='rfdetr-nano',device_id=gpu.id,initial_model_id=model['id'],parameters=model['parameters'],operation='validate')
    s.training.configuration_preflight(payload)
    jid=s.jobs.submit('p3_validate',p.id,payload);deadline=time.monotonic()+300
    while s.jobs.get(jid)['state'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:
        if time.monotonic()>deadline:s.jobs.cancel(jid);raise RuntimeError('CUDA reload timeout')
        time.sleep(.2)
    job=s.jobs.get(jid);report['cuda_job']=job
    assert job['state']=='SUCCEEDED',job
    assert len(s.models.versions(str(copy),include_archived=True))==len(models)
    report['loaded_modules']=[name for name in sys.modules if name.startswith(('ultralytics','thop','rfdetr_plus','ivad_app.services.training_service'))]
    assert report['loaded_modules']==[]
    report['status']='PASS'
finally:
    (OUT/'acceptance-evidence.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8');s.close()
print(json.dumps({k:report[k] for k in ['status','counts','dataset','cuda_job']},ensure_ascii=False))
