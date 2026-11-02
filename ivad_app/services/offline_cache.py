"""Exact cache admission; legacy caches remain readable, never guessed as new runs."""
import hashlib,json
from pathlib import Path
from ivad_app.core.contracts import AppError
from ivad_app.storage.project_store import file_hash

class OfflineCache:
    def cache_identity(self,payload):
        import av  # Historical YOLO cache protocol only, never RF composition.
        root=payload['root'];media=self.s.media.get(payload['media_id'],root);_,model=self.s.models.verify(payload['model_id'],root)
        python=Path(self.s.settings.preferences().get('worker_python') or self.s.root/'.venv-nvidia/Scripts/python.exe');environment={}
        for name in ['torch','torchvision','ultralytics','PIL']:
            path=python.parent.parent/'Lib/site-packages'/name/'__init__.py'
            environment[name]=file_hash(path) if path.is_file() else 'missing'
        value=dict(version='p35-pil-rgb-ultralytics-v1',media_id=media['id'],source_sha256=file_hash(Path(media['accessible_path'])),video=media['video'],model_id=payload['model_id'],model_sha256=model['sha256'],class_map=model['class_map'],dataset_version=model['dataset_version'],device_id=payload['device_id'],camera_context=payload.get('camera_id'),start_us=round(float(payload['start'])*1e6),end_us=round(float(payload['end'])*1e6),confidence=float(payload['confidence']),preprocess=dict(imgsz=640,rect=True,color='RGB',half=False,decoder='PyAV '+av.__version__),postprocess=dict(iou=.45,max_det=300,nms='Ultralytics'),worker_sha256=file_hash(self.s.root/'ivad_app/compute/offline_worker.py'))
        value['environment']=environment;value['worker_python']=str(python.resolve());value['precision']='FP32'
        value['identity_schema']=2;value['provenance']={k:media.get(k) for k in ['project_id','parent_id','clip_info','camera_id','kind','lifecycle']}
        value['implementation']={name:file_hash(self.s.root/name) for name in ['ivad_app/services/offline_demo_service.py','ivad_app/video/reader.py','ivad_app/video/timestamps.py']}
        return dict(signature=hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest(),configuration=value)
    def matching_cache(self,payload):
        identity=self.cache_identity(payload)
        for path in sorted((Path(payload['root'])/'demos').glob('*/manifest.json'),reverse=True):
            try:
                m=json.loads(path.read_text(encoding='utf8'))
                if m.get('identity')==identity:self.load(path.parent);return str(path.parent)
            except (OSError,ValueError,KeyError,AppError):continue
        return None
