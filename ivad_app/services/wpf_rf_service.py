"""WPF adapter to existing queue, CUDA training and model registry services."""
import copy
import json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from ivad_app.services.ids_import_service import controlled, state
from ivad_app.datasets.ids_rfdetr import export_dataset
from ivad_app.storage.models import Dataset,DatasetVersion,DatasetSample,ExtractedFrame,Annotation
from ivad_app.storage.project_store import atomic_json,file_hash
from ivad_app.core.contracts import utc_now


def freeze(services, root):
    root=controlled(root); did=str(uuid4());vid=str(uuid4())
    folder=root/'datasets'/did/'v0001'
    manifest=export_dataset(root,folder)
    if state(root)['sha256']!=manifest['source_sha256']:
        raise ValueError('IDS_SNAPSHOT_CHANGED')
    samples=[]
    with services.store.open(str(root)) as (_,db,_),db.transaction() as s:
        for sample in manifest['samples']:
            frame=s.get(ExtractedFrame,sample['frame_id'])
            ann=s.scalar(select(Annotation).where(Annotation.frame_id==frame.id))
            payload=copy.deepcopy(ann.payload)
            for obj in payload['objects']:
                if obj['kind']=='polygon':
                    xs,ys=zip(*obj['geometry']);obj['kind']='box'
                    obj['geometry']=[min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)]
                    obj['conversion']='source polygon axis-aligned min/max bbox'
            samples.append(dict(sample,image=sample['split']+'/'+frame.id+Path(frame.path).suffix,
                split='val' if sample['split']=='valid' else sample['split'],
                media_id=frame.media_id,source_group_id=sample['group'],time_us=frame.time_us,
                width=frame.width,height=frame.height,annotation=payload,
                annotation_status=ann.status,annotation_source='Human Generated'))
        classes=[{'uuid':uid,'class_id':i,'name':manifest['class_names'][i]} for uid,i in manifest['class_map'].items()]
        frozen=dict(format='ivad-dataset',format_version=1,dataset_id=did,version_id=vid,
            version=1,classes=classes,samples=samples,strategy='source',ids=manifest,
            admission={'policy':'ids-confirmed-v1','split_status':'PASS'})
        atomic_json(folder/'manifest.json',frozen)
        s.add(Dataset(id=did,name='IDS confirmed',created_at=utc_now(),details={},revision=1));s.flush()
        s.add(DatasetVersion(id=vid,dataset_id=did,number=1,path=(folder/'manifest.json').relative_to(root).as_posix(),
            sha256=file_hash(folder/'manifest.json'),summary={'images':len(samples),'ids_sha256':manifest['source_sha256']},created_at=utc_now()));s.flush()
        for sample in samples:s.add(DatasetSample(id=str(uuid4()),version_id=vid,frame_id=sample['frame_id'],split=sample['split'],sha256=sample['sha256'],annotation=sample['annotation']))
    return vid


class WpfRFService:
    def __init__(self,repo,workspace):
        from ivad_app.core.application import ApplicationServices
        from .local_security import authorize
        authorize(Path(workspace)/'wpf-runtime','identity')
        self.services=ApplicationServices(Path(repo),Path(workspace)/'wpf-runtime',media_backend='windows-mf',lite=False)
        import os
        prefs=self.services.settings.preferences()
        prefs.setdefault('rfdetr_worker_python',str(Path(repo)/'.venv-rf-media-candidate/Scripts/python.exe'))
        if not prefs['rfdetr_worker_python']:prefs['rfdetr_worker_python']=str(Path(repo)/'.venv-rf-media-candidate/Scripts/python.exe')
        if os.environ.get('IVAD_RF_WORKER_PYTHON'):prefs['rfdetr_worker_python']=os.environ['IVAD_RF_WORKER_PYTHON']
        self.services.settings.save_preferences(prefs)

    def execute(self,r):
        root=str(controlled(r['root']));app=self.services;action=r['action']
        from .local_security import authorize,check_acl,sid
        authorize(root,action)
        if action=='gpu':return [dict(id=d.id,name=d.name,available=d.backend_available) for d in app.training.rf_devices()]
        if action=='registry':return app.models.versions(root,include_archived=True)
        if action=='runs':return app.training.runs(root,include_archived=True)
        if action=='job':return app.jobs.get(r['job_id'])
        if action=='cancel':app.jobs.cancel(r['job_id']);return {'cancel_requested':True}
        if action=='infer':
            import subprocess,os
            weights,entry=app.models.verify(r['model_id'],root)
            check_acl(weights,sid())
            with app.store.open(root) as (_,db,_),db.transaction() as s:
                frame=s.scalar(select(ExtractedFrame).order_by(ExtractedFrame.id))
                if not frame:raise ValueError('FRAME_REQUIRED')
                image=Path(root)/frame.path;image_hash=frame.sha256
            devices=[d for d in app.training.rf_devices() if d.backend_available]
            if not devices:raise ValueError('CUDA_REQUIRED')
            work=Path(root)/'inference'/str(uuid4());work.mkdir(parents=True)
            request=dict(repo=str(app.root),weights=str(weights),weights_sha256=entry['sha256'],
                image=str(image),image_sha256=image_hash,classes=len(entry['class_map']),
                gpu_uuid=devices[0].id.removeprefix('nvidia:'),output=str(work/'result.json'))
            atomic_json(work/'request.json',request)
            env=dict(os.environ,HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',WANDB_MODE='disabled')
            from .local_security import redact
            result=subprocess.run([str(app.training.rf.python()),'-I','-X','utf8',str(app.root/'ivad_app/compute/ids_inference_worker.py'),str(work/'request.json')],capture_output=True,text=True,encoding='utf8',errors='replace',env=env,timeout=180,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            (work/'worker.log').write_text(redact(result.stdout+'\n'+result.stderr),encoding='utf8')
            result.check_returncode()
            return json.loads((work/'result.json').read_text(encoding='utf8'))
        if action in ('train','validate'):
            if r.get('model_id'):
                weights,_=app.models.verify(r['model_id'],root);check_acl(weights,sid())
            vid=r.get('version_id') or freeze(app,root)
            devices=[d for d in app.training.rf_devices() if d.backend_available]
            if not devices:raise ValueError('CUDA_REQUIRED')
            payload=dict(root=root,backend='rfdetr',model='rfdetr-nano',version_id=vid,device_id=devices[0].id,
                parameters={'epochs':int(r.get('epochs',1)),'batch_size':2},operation=action,
                initial_model_id=r.get('model_id'))
            app.training.configuration_preflight(payload)
            return {'job_id':app.jobs.submit('p3_'+action,state(root)['project_id'],payload),'version_id':vid}
        raise ValueError('RF_ACTION_UNSUPPORTED')

    def close(self):self.services.close()
