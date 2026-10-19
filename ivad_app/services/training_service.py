"""P3 frozen-data preflight and isolated NVIDIA process orchestration."""
import json,os,subprocess,time,copy,math
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from PIL import Image
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import TrainingRun,ExtractedFrame
from ivad_app.storage.project_store import file_hash,safe_path,atomic_json
from ivad_app.datasets.exporters import export_snapshot
from ivad_app.compute.model_adapters import ADAPTERS,adapter
from ivad_app.annotations.geometry import validate_geometry

MODELS={name:value for name,value in ADAPTERS.items() if name in {'yolo26n','yolo11n'}}
DEFAULTS={'epochs':20,'imgsz':640,'batch':4,'lr0':0.01,'optimizer':'SGD','weight_decay':0.0005,'augment':True,'patience':10,'seed':123,'amp':False}

def validate_parameters(values):
    p=dict(DEFAULTS,**values)
    for key,lo,hi in [('epochs',1,10000),('imgsz',64,2048),('batch',1,64),('patience',0,10000),('seed',0,2147483647)]:
        if isinstance(p[key],bool) or not isinstance(p[key],int) or not lo<=p[key]<=hi:raise AppError('TRAIN_PARAMETER',f'{key}数值超出范围。')
    if p['imgsz']%32:raise AppError('TRAIN_PARAMETER','图像尺寸须为32的整数倍。')
    for key,lo,hi in [('lr0',0.000001,1),('weight_decay',0,1)]:
        if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or not lo<=p[key]<=hi:raise AppError('TRAIN_PARAMETER',f'{key}数值无效。')
    if p['optimizer'] not in {'SGD','Adam','AdamW','auto'} or type(p['amp']) is not bool or type(p['augment']) is not bool:raise AppError('TRAIN_PARAMETER','优化器/增强/精度设置无效。')
    if set(p)-set(DEFAULTS):raise AppError('TRAIN_PARAMETER','不支持的训练参数。')
    return p

class TrainingService:
    def __init__(self,store,datasets,models,devices,logs,root,settings):self.store,self.datasets,self.models,self.devices,self.logs,self.root,self.settings=store,datasets,models,devices,logs,Path(root),settings
    def configuration_preflight(self,payload):
        from ivad_app.core.demo_policy import require
        require('ai')
        """Validate a proposed job without creating a run or launching a worker."""
        raise AppError('LEGACY_READ_ONLY','旧训练后端仅保留历史源码，不允许新任务。')
        if payload.get('model')=='rfdetr-nano':raise AppError('TRAIN_MODEL','RF-DETR必须使用独立Adapter，禁止通过旧YOLO服务执行。')
        root=payload['root'];name=payload['model'];adapter(name,payload.get('operation','train'))
        parameters=validate_parameters(payload.get('parameters',{}));device=self.devices.require_gpu(payload['device_id'])
        if not device.id.startswith('nvidia:'):raise AppError('TRAIN_BACKEND','仅支持已检查的NVIDIA CUDA后端。')
        python=Path(self.settings.preferences().get('worker_python') or self.root/'.venv-nvidia/Scripts/python.exe')
        if not python.is_file():raise AppError('WORKER_MISSING','GPU环境解释器不存在。')
        _,snapshot,counts=self.preflight(payload['version_id'],root)
        base=self.root/'artifacts/p0'/f'{name}.pt'
        if payload.get('initial_model_id'):
            base,entry=self.models.verify(payload['initial_model_id'],root)
            if entry.get('model')!=name:raise AppError('TRAIN_MODEL','初始权重架构与基础模型不一致。')
        if payload.get('resume_run_id'):
            old=next((r for r in self.runs(root) if r['id']==payload['resume_run_id']),None)
            if not old or old['version_id']!=payload['version_id'] or old['model']!=name or old['state'] not in {'FAILED','CANCELLED'}:raise AppError('TRAIN_RESUME','只允许恢复相同数据版本和架构的中断任务。已完成模型请用初始权重微调。')
            with self.store.open(root) as (folder,_,_):base=safe_path(folder,old['path'])/'run/weights/resume.pt'
            parameters=validate_parameters(old['parameters'])
        if payload.get('operation')=='validate' and not payload.get('initial_model_id'):raise AppError('VALIDATE_MODEL','独立验证请选择已登记的初始模型。')
        if not base.is_file():raise AppError('TRAIN_WEIGHTS','初始权重或可恢复检查点不存在；不会自动下载。')
        return {'counts':counts,'parameters':parameters,'weights_sha256':file_hash(base),'worker':str(python),'dataset_id':snapshot['dataset_id']}
    def runs(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as s:return [dict(id=r.id,**r.details) for r in s.scalars(select(TrainingRun))]
    def preflight(self,version_id,root=None):
        folder,snap=self.datasets.snapshot(version_id,root);seen=set();groups={};counts={'train':0,'val':0,'test':0};classes=snap['classes']
        if not classes or [r['class_id'] for r in classes]!=list(range(len(classes))):raise AppError('TRAIN_CLASSES','类别映射为空或不连续。')
        policy=snap.get('admission',{});experimental=policy.get('policy')=='human-auto-v1' and policy.get('scope')=='EXPERIMENT_ONLY'
        if experimental and (policy.get('validation_level')!='AUTO_CHECKED_HUMAN' or policy.get('independent_review') is not False or policy.get('split_status') not in {'PASS','LIMITED'} or (policy.get('split_status')=='LIMITED' and not policy.get('allow_limited'))):raise AppError('TRAIN_ADMISSION','实验版本准入证据或风险确认无效。')
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            for sample in snap['samples']:
                state=sample['annotation']['image_tag'];objects=sample['annotation']['objects'];live=s.get(ExtractedFrame,sample['frame_id'])
                if not live or live.handling.get('is_excluded') or not ((sample.get('validation_level')=='AUTO_CHECKED_HUMAN' and sample.get('annotation_source')=='Human Generated' and sample['annotation_status']!='REJECTED') if experimental else sample['annotation_status'] in {'REVIEWED','APPROVED'}) or state not in {'NORMAL','ABNORMAL'} or (state=='NORMAL' and (objects or sample['annotation'].get('image_label_id'))) or (state=='ABNORMAL' and not objects):raise AppError('TRAIN_ANNOTATION','未知/剔除/未审核/冲突/异常无框样本不能用于目标检测训练。')
                for obj in objects:
                    if obj['kind'] not in {'box','polygon'} or obj['label_id'] not in {r['uuid'] for r in classes}:raise AppError('TRAIN_CLASSES','目标类型或类别映射无效，ROI不作为检测目标。')
                    validate_geometry(obj['kind'],obj['geometry'],sample['width'],sample['height'])
                path=safe_path(folder,sample['image'])
                if not path.is_file() or file_hash(path)!=sample['sha256']:raise AppError('TRAIN_IMAGE','冻结图片缺失或哈希变化。')
                with Image.open(path) as im:
                    if im.size!=(sample['width'],sample['height']):raise AppError('TRAIN_IMAGE','图片尺寸与快照不一致。')
                    im.verify()
                if sample['sha256'] in seen:raise AppError('TRAIN_LEAKAGE','重复图片，拒绝跨集合泄漏。')
                seen.add(sample['sha256']);split=sample['split']
                if split not in counts:raise AppError('TRAIN_SPLIT','不支持的数据划分。')
                counts[split]+=1
                group=(sample.get('source_group_id') or sample['media_id']) if experimental and snap['strategy']=='source' else (sample.get('camera_id') or sample.get('camera') or sample.get('source_group_id') or sample['media_id'])
                if group in groups and groups[group]!=split and not (experimental and snap['strategy']=='random' and policy.get('allow_limited')):raise AppError('TRAIN_LEAKAGE','同摄像头或源录像跨集合，拒绝数据泄漏。')
                groups[group]=split
        if not counts['train'] or not counts['val']:raise AppError('TRAIN_SPLIT','训练与验证集均须非空，请增加独立摄像头/录像组重新冻结。')
        return folder,snap,counts
    def _put(self,rid,data,root):
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            row=s.get(TrainingRun,rid)
            if row:row.details=copy.deepcopy(data);row.revision+=1
            else:s.add(TrainingRun(id=rid,details=copy.deepcopy(data),revision=1))
    def train(self,context,payload):
        raise AppError('LEGACY_READ_ONLY','旧训练后端仅保留历史源码，不允许新任务。')
        root=payload['root'];parameters=validate_parameters(payload.get('parameters',{}));name=payload.get('model','yolo26n')
        operation=payload.get('operation','train')
        if name not in MODELS:raise AppError('TRAIN_MODEL','该模型适配器尚不支持训练。')
        adapter(name,operation)
        device=self.devices.require_gpu(payload.get('device_id',''))
        if not device.id.startswith('nvidia:'):raise AppError('TRAIN_BACKEND','本轮仅实现NVIDIA CUDA训练，Intel接口未验收。')
        python=Path(self.settings.preferences().get('worker_python') or self.root/'.venv-nvidia/Scripts/python.exe')
        if not python.is_file():raise AppError('WORKER_MISSING','GPU环境解释器不存在。')
        source,snapshot,counts=self.preflight(payload['version_id'],root)
        base=self.root/'artifacts/p0'/f'{name}.pt';resume=False
        if operation=='validate' and not payload.get('initial_model_id'):raise AppError('VALIDATE_MODEL','请选择已登记的模型版本进行独立验证。')
        if payload.get('initial_model_id'):
            base,entry=self.models.verify(payload['initial_model_id'],root)
            if entry.get('model')!=name:raise AppError('TRAIN_MODEL','初始模型适配器与所选架构不一致。')
        if payload.get('resume_run_id'):
            previous=next((r for r in self.runs(root) if r['id']==payload['resume_run_id']),None)
            if not previous or previous['version_id']!=payload['version_id'] or previous['model']!=name:raise AppError('TRAIN_RESUME','恢复需相同数据集版本与模型架构。')
            with self.store.open(root) as (folder,_,_):base=safe_path(folder,previous['path'])/'run/weights/resume.pt'
            parameters=validate_parameters(previous['parameters']);resume=True
        if not base.is_file():raise AppError('TRAIN_WEIGHTS','本地初始权重或可恢复检查点不存在；不会自动下载。')
        rid=str(uuid4())
        with self.store.open(root) as (folder,_,_):work=folder/'training'/rid;work.mkdir(parents=True)
        data={'state':'PREPARING','operation':operation,'model':name,'version_id':payload['version_id'],'dataset_id':snapshot['dataset_id'],'parameters':parameters,'device_id':device.id,'created_at':utc_now(),'path':work.relative_to(folder).as_posix(),'counts':counts,'job_id':context.job_id,'initial_sha256':file_hash(base),'resume':resume}
        self._put(rid,data,root)
        try:
            exported=work/'dataset';exported.mkdir();export_snapshot(snapshot,source,exported,'yolo_detect',context.check)
            # This copied training workspace may get YOLO cache files; the frozen snapshot stays immutable.
            import yaml
            config=yaml.safe_load((exported/'data.yaml').read_text(encoding='utf8'));config['path']=str(exported.resolve());(exported/'data.yaml').write_text(yaml.safe_dump(config,allow_unicode=True),encoding='utf8')
            request=dict(operation=operation,class_count=len(snapshot['classes']),class_names=[c['name'] for c in snapshot['classes']],model=name,weights=str(base.resolve()),weights_sha256=file_hash(base),device_uuid=device.id.removeprefix('nvidia:'),device_index=int(device.details.get('index',0)),parameters=parameters,data=str(exported/'data.yaml'),work=str(work),resume=resume)
            atomic_json(work/'request.json',request);data['state']='RUNNING';self._put(rid,data,root)
            env=dict(os.environ,PYTHONUTF8='1',CUDA_VISIBLE_DEVICES=request['device_uuid'],YOLO_CONFIG_DIR=str(work/'yolo-config'),YOLO_AUTOINSTALL='false',YOLO_OFFLINE='true',MPLCONFIGDIR=str(work/'matplotlib'))
            with context.service.gate.acquire(device.id,context.cancel),(work/'worker-console.log').open('w',encoding='utf8') as log:
                child=subprocess.Popen([str(python),'-I','-X','utf8',str(self.root/'ivad_app/compute/train_worker.py'),str(work/'request.json')],stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                cancelled=None
                try:
                    while child.poll() is None:
                        if context.cancel.is_set():
                            (work/'cancel.request').touch();cancelled=cancelled or time.monotonic()
                            if time.monotonic()-cancelled>20:child.terminate()
                        if (work/'progress.json').exists():
                            try:
                                progress=json.loads((work/'progress.json').read_text(encoding='utf8'))
                                if progress!=data.get('progress'):data['progress']=progress;self._put(rid,data,root)
                                context.service._change(context.job_id,progress=min(99,round(progress.get('epoch',0)*100/parameters['epochs'])))
                            except (OSError,ValueError):pass
                        time.sleep(.2)
                finally:
                    if child.poll() is None:child.terminate();child.wait(timeout=10)
            context.check()
            result=json.loads((work/'result.json').read_text(encoding='utf8')) if (work/'result.json').exists() else {}
            if result.get('oom'):raise AppError('TRAIN_OOM','GPU显存不足；请减小批次或图像尺寸后重试。日志和已有检查点保留，不切换CPU。')
            if child.returncode or result.get('status')!='PASS':raise AppError('TRAIN_FAILED','GPU训练/验证失败：'+result.get('error','Worker异常退出，请查看保留的worker-console.log。'))
            if self.datasets.snapshot(payload['version_id'],root)[1]!=snapshot:raise AppError('TRAIN_SNAPSHOT','训练期间冻结清单发生变化。')
            if result.get('onnx'):result['onnx']['path']=Path(result['onnx']['path']).relative_to(folder).as_posix()
            if operation=='validate':
                mid=payload['initial_model_id'];self.models.record_validation(mid,result,payload['version_id'],root)
            else:mid=self.models.register(work/'run/weights/best.pt',dict(model=name,task='detect',run_id=rid,dataset_version=payload['version_id'],class_map=snapshot['classes'],input_size=parameters['imgsz'],preprocess='Ultralytics RGB / 255, CHW, letterbox; FP32 ONNX',postprocess='raw non-end2end + NMS; conf=.25, iou=.45',metrics=result['metrics'],validation_passed=True,gpu_evidence=result['evidence'],onnx=result.get('onnx'),license='Ultralytics AGPL-3.0 / Enterprise; commercial deployment NOT APPROVED',dataset_admission=snapshot.get('admission',{'policy':'reviewed-legacy'}),source='local CUDA training; industrial accuracy NOT TESTED'),root,trusted=True)
            data.update(state='SUCCEEDED',result=result,model_id=mid,completed_at=utc_now());self._put(rid,data,root);context.progress(100)
            return {'run_id':rid,'model_id':mid,'path':str(work),'metrics':result['metrics']}
        except Exception as exc:
            data.update(state='CANCELLED' if context.cancel.is_set() else 'FAILED',error=str(exc),completed_at=utc_now());self._put(rid,data,root);raise
    def validate(self,context,payload):return self.train(context,dict(payload,operation='validate',resume_run_id=None))
