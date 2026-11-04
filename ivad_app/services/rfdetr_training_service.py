"""RF-DETR orchestration in existing project/task/registry infrastructure."""
import copy
import json
import os
from pathlib import Path
import subprocess
import threading
import time
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,DeviceInfo,utc_now
from ivad_app.compute.rfdetr_contract import MODEL,parameters,PROTOCOL,signature
from ivad_app.datasets.rfdetr import export as export_coco
from ivad_app.storage.models import TrainingRun,ExtractedFrame
from ivad_app.storage.project_store import file_hash,atomic_json,safe_path
from ivad_app.annotations.geometry import validate_geometry

class RFDETRTrainingService:
    @staticmethod
    def stop_child(child):
        # Windows venv python.exe can be a launcher with a real Python descendant.
        # Kill only this owned worker's tree, never processes selected by GPU/name.
        if child.poll() is not None:return
        if os.name=='nt':
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True,timeout=10,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        else:child.terminate()
        child.wait(timeout=10)
    def __init__(self,store,datasets,models,devices,logs,root,settings):
        self.store,self.datasets,self.models,self.devices,self.logs,self.root,self.settings=store,datasets,models,devices,logs,Path(root),settings
        self._devices=None;self._probe_lock=threading.Lock()
    def python(self):
        from ivad_app.core.demo_policy import require
        require('ai')
        value=Path(self.settings.preferences().get('rfdetr_worker_python') or self.root/'.venv-rfdetr/Scripts/python.exe').resolve()
        if not value.is_file() or value.parent.parent.name in {'.venv-nvidia','.venv-p1'}:raise AppError('RF_ENV','请选择独立RF-DETR环境，不允许使用旧YOLO/GUI解释器。')
        return value
    def devices_snapshot(self):
        with self._probe_lock:
            if self._devices is not None:return self._devices
            python=self.python()
            probe=subprocess.run([str(python),'-I','-X','utf8',str(self.root/'ivad_app/compute/rfdetr_probe.py')],capture_output=True,text=True,encoding='utf8',timeout=90,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
            if probe.returncode:raise AppError('RF_GPU','独立RF环境GPU检查失败。')
            raw=json.loads(probe.stdout)
            if raw.get('errors'):raise AppError('RF_GPU','RF环境探测出错，不会使用旧环境替代。')
            self._devices=[DeviceInfo('nvidia:'+d['uuid'],d['name'],'RF-DETR CUDA',True,bool(raw['available'] and d['cuda_tensor_verified']),False,'RF CUDA Available' if d['cuda_tensor_verified'] else 'Error',dict(d,torch=raw['torch'],cuda=raw['cuda'])) for d in raw['devices']]
            return self._devices
    def snapshot(self,version_id,root):
        folder,snapshot=self.datasets.snapshot(version_id,root);admission=snapshot.get('admission',{});classes=snapshot['classes'];counts={s:0 for s in ['train','val','test']}
        seen_hashes=set();groups={}
        if not classes or len({c['uuid'] for c in classes})!=len(classes) or len({c['class_id'] for c in classes})!=len(classes):raise AppError('RF_CLASSES','类别映射为空或重复。')
        experimental=admission.get('policy')=='human-auto-v1' and admission.get('scope')=='EXPERIMENT_ONLY'
        if experimental and (admission.get('validation_level')!='AUTO_CHECKED_HUMAN' or admission.get('independent_review') is not False or admission.get('split_status') not in {'PASS','LIMITED'} or (admission.get('split_status')=='LIMITED' and not admission.get('allow_limited'))):raise AppError('RF_ADMISSION','实验准入或LIMITED确认缺失。')
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            for item in snapshot['samples']:
                frame=s.get(ExtractedFrame,item['frame_id']);annotation=item['annotation']
                allowed=(item.get('validation_level')=='AUTO_CHECKED_HUMAN' and item.get('annotation_source')=='Human Generated' and item['annotation_status']!='REJECTED') if experimental else item['annotation_status'] in {'REVIEWED','APPROVED'}
                if not frame or frame.handling.get('is_excluded') or frame.handling.get('completion_state')=='CONFLICT' or not allowed:raise AppError('RF_ADMISSION','剔除、冲突或未准入样本禁止训练。')
                objects=annotation['objects'];tag=annotation['image_tag']
                if tag not in {'NORMAL','ABNORMAL'} or (tag=='NORMAL' and (objects or annotation.get('image_label_id'))) or (tag=='ABNORMAL' and not objects):raise AppError('RF_TRUTH','正常/异常目标真值冲突；异常无框不能作为检测样本。')
                if any(o['kind']!='box' or o['label_id'] not in {c['uuid'] for c in classes} for o in objects):raise AppError('RF_TRUTH','本轮Nano Detection只接收已核实矩形框，禁止静默转换多边形。')
                for obj in objects:
                    if obj.get('source')!='Human Generated':raise AppError('RF_TRUTH','不能用自动预测替代已准入人工真值。')
                    validate_geometry(obj['kind'],obj['geometry'],item['width'],item['height'])
                image=safe_path(folder,item['image'])
                if not image.is_file() or file_hash(image)!=item['sha256']:raise AppError('RF_IMAGE','冻结图像缺失或SHA256改变。')
                if item['sha256'] in seen_hashes:raise AppError('RF_LEAKAGE','重复图片，拒绝跨集合泄漏。')
                seen_hashes.add(item['sha256'])
                split=item['split']
                if split not in counts:raise AppError('RF_SPLIT','不支持的数据划分。')
                group=(item.get('source_group_id') or item['media_id']) if experimental and snapshot['strategy']=='source' else (item.get('camera_id') or item.get('camera') or item.get('source_group_id') or item['media_id'])
                if group in groups and groups[group]!=split and not (experimental and snapshot['strategy']=='random' and admission.get('allow_limited')):raise AppError('RF_LEAKAGE','同摄像头或源录像跨集合，拒绝数据泄漏。')
                groups[group]=split
                counts[item['split']]+=1
        if not counts['train'] or not counts['val']:raise AppError('RF_SPLIT','须保留非空训练与验证划分，不会自动重新划分。')
        return folder,snapshot,counts
    def configuration_preflight(self,payload):
        from ivad_app.services.backend_policy import require_rf_request
        require_rf_request(payload)
        p=parameters(payload.get('parameters',{}));python=self.python();root=payload['root'];folder,snapshot,counts=self.snapshot(payload['version_id'],root)
        if payload.get('resume_run_id'):raise AppError('RF_RESUME','RF优化器断点恢复尚未验收；检查点保留，请用可信权重创建新实验。')
        gpu=next((d for d in self.devices_snapshot() if d.id==payload['device_id'] and d.backend_available),None)
        if gpu is None:raise AppError('RF_GPU','RF环境没有指定的可用CUDA GPU，不降级CPU。')
        if p['amp_dtype']=='bf16' and not gpu.details.get('bf16_supported'):raise AppError('RF_AMP','当前RF CUDA设备不支持BF16，请在高级参数选择FP32。')
        base=self.root/'artifacts/p36-rfdetr-20261016/weights/rf-detr-nano.pth'
        if payload.get('initial_model_id'):
            base,entry=self.models.verify(payload['initial_model_id'],root)
            if entry.get('backend')!='rfdetr' or entry.get('model')!=MODEL or entry.get('artifact_format')!='rf-detr-weights-pth':raise AppError('RF_WEIGHTS','只能使用RF-DETR Nano权重，拒绝YOLO/ONNX/恢复检查点。')
            if [c['uuid'] for c in entry['class_map']]!=[c['uuid'] for c in snapshot['classes']]:raise AppError('RF_CLASSES','初始模型与冻结数据类别UUID不匹配。')
        elif payload.get('operation')=='validate':raise AppError('RF_WEIGHTS','独立验证请选择已登记RF权重。')
        if not base.is_file() or base.suffix.lower()!='.pth':raise AppError('RF_WEIGHTS','可信Nano PTH缺失；不会下载或回退旧引擎。')
        digest=file_hash(base)
        if not payload.get('initial_model_id') and digest!='d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d':raise AppError('RF_WEIGHTS','官方Nano预训练权重哈希不符。')
        return dict(counts=counts,parameters=p,weights_sha256=digest,weights=str(base.resolve()),worker=str(python),dataset_id=snapshot['dataset_id'],dataset_sha256=file_hash(folder/'manifest.json'),gpu_uuid=gpu.id.removeprefix('nvidia:'),protocol_sha256=signature(dict(PROTOCOL,resolution=p['resolution'])))
    def put(self,rid,data,root):
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            row=s.get(TrainingRun,rid)
            if row:row.details=copy.deepcopy(data);row.revision+=1
            else:s.add(TrainingRun(id=rid,details=copy.deepcopy(data),revision=1))
    def train(self,context,payload):
        report=self.configuration_preflight(payload);root=payload['root'];folder,snapshot,_=self.snapshot(payload['version_id'],root);rid=str(uuid4())
        with self.store.open(root) as (project,_,_):work=project/'training'/rid;work.mkdir(parents=True)
        data=dict(state='PREPARING',backend='rfdetr',model=MODEL,operation=payload.get('operation','train'),version_id=payload['version_id'],dataset_id=snapshot['dataset_id'],parameters=report['parameters'],device_id=payload['device_id'],created_at=utc_now(),path=work.relative_to(project).as_posix(),counts=report['counts'],job_id=context.job_id,initial_sha256=report['weights_sha256'])
        self.put(rid,data,root);child=None
        try:
            context.check();export_coco(folder/'manifest.json',work/'dataset');context.check()
            req=dict(work=str(work.resolve()),data=str((work/'dataset').resolve()),weights=report['weights'],weights_sha256=report['weights_sha256'],device_uuid=report['gpu_uuid'],parameters=report['parameters'],operation=data['operation'],class_names=[c['name'] for c in sorted(snapshot['classes'],key=lambda c:c['class_id'])])
            atomic_json(work/'request.json',req)
            env=dict(os.environ,PYTHONUTF8='1',CUDA_VISIBLE_DEVICES=report['gpu_uuid'])
            with context.service.gate.acquire(payload['device_id'],context.cancel),(work/'worker-console.log').open('w',encoding='utf8') as log:
                context.check();data['state']='RUNNING';self.put(rid,data,root)
                from .local_security import drain_redacted
                from threading import Thread
                child=subprocess.Popen([report['worker'],'-I','-X','utf8',str(self.root/'ivad_app/compute/rfdetr_train_worker.py'),str(work/'request.json')],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,encoding='utf8',errors='replace',env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                reader=Thread(target=drain_redacted,args=(child.stdout,log),daemon=True);reader.start()
                stopping=None
                try:
                    while child.poll() is None:
                        if context.cancel.is_set():
                            (work/'cancel.request').touch();stopping=stopping or time.monotonic()
                            if time.monotonic()-stopping>20:
                                data['forced_stop']=True;self.stop_child(child)
                        progress=work/'progress.json'
                        if progress.exists():
                            try:
                                value=json.loads(progress.read_text(encoding='utf8'))
                                if value!=data.get('progress'):data['progress']=value;self.put(rid,data,root)
                            except (ValueError,OSError):pass
                        time.sleep(.1)
                finally:
                    if child.poll() is None:self.stop_child(child)
                    reader.join()
            context.check()
            result=json.loads((work/'result.json').read_text(encoding='utf8')) if (work/'result.json').exists() else {}
            if child.returncode or result.get('status')!='PASS':raise AppError('RF_OOM' if result.get('oom') else 'RF_WORKER',result.get('error','RF Worker异常退出；保留日志，不登记模型。'))
            if result['protocol_sha256']!=report['protocol_sha256'] or result.get('parity',{}).get('status')!='PASS':raise AppError('RF_PARITY','评估协议或重载一致性失败，禁止登记。')
            if self.datasets.snapshot(payload['version_id'],root)[1]!=snapshot:raise AppError('RF_SNAPSHOT','冻结数据在任务期间改变。')
            if file_hash(Path(result['weights']))!=result['weights_sha256']:raise AppError('RF_HASH','结果权重哈希不符。')
            with context.service.lock:
                context.check()
                if data['operation']=='validate':
                    mid=payload['initial_model_id'];self.models.record_validation(mid,result,payload['version_id'],root)
                else:
                    data['result']=result
                    mapping=[dict(c,model_class_id=i,coco_category_id=c['class_id']) for i,c in enumerate(sorted(snapshot['classes'],key=lambda c:c['class_id']))]
                    mid=self.models.register(result['weights'],dict(backend='rfdetr',model=MODEL,architecture='nano',artifact_format='rf-detr-weights-pth',task='detect',run_id=rid,dataset_version=payload['version_id'],dataset_sha256=report['dataset_sha256'],class_map=mapping,class_map_sha256=signature(mapping),input_size=report['parameters']['resolution'],parameters=report['parameters'],metrics=result['metrics'],validation_passed=True,gpu_evidence=result['evidence'],evaluation_protocol=result['protocol'],evaluation_protocol_sha256=result['protocol_sha256'],parity=result['parity'],license='RF-DETR Nano Apache-2.0; distribution audit separate',dataset_admission=snapshot.get('admission',{}),source='RF-DETR CUDA training / EXPERIMENTAL / LIMITED when applicable'),root,trusted=True,training_completion=(rid,data))
                if data['operation']=='validate':
                    data.update(state='SUCCEEDED',model_id=mid,result=result,completed_at=utc_now());self.put(rid,data,root)
            return dict(run_id=rid,model_id=mid,metrics=result['metrics'],committed_training=True)
        except Exception as exc:
            data.update(state='CANCELLED' if context.cancel.is_set() else 'FAILED',error=str(exc),completed_at=utc_now());self.put(rid,data,root);raise
