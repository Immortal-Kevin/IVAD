"""Project model registry; no unpickling in the GUI process and no deployment."""
import copy,shutil,math
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import ModelVersion,Camera,LabelCategory,SettingRecord,RegionOfInterest,MediaAsset,TrainingRun
from ivad_app.storage.project_store import safe_path,file_hash
from ivad_app.storage.project_store import atomic_json

class ModelService:
    def __init__(self,store,logs):self.store,self.logs=store,logs
    def versions(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            return [dict(id=r.id,revision=r.revision,**r.details) for r in s.scalars(select(ModelVersion))]
    def camera_configurations(self,camera_id=None,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            row=session.get(SettingRecord,'camera_detector_configurations')
            records=copy.deepcopy(row.value.get('items',[])) if row else []
            return [r for r in records if camera_id is None or r['camera_id']==camera_id]
    def configure_camera(self,camera_id,model_version_id,fault_ids,root=None,*,roi_scope=None):
        """Configuration metadata only. No inference, scheduling or production release."""
        with self.store.open(root) as (_,db,_),db.transaction(camera_write=True) as session:
            if not session.get(Camera,camera_id):raise AppError('CAMERA_MISSING','当前项目摄像头不存在。')
            if not session.get(ModelVersion,model_version_id):raise AppError('MODEL_MISSING','当前项目模型版本不存在。')
            faults=sorted(set(fault_ids))
            if any(not session.get(LabelCategory,f) for f in faults):raise AppError('LABEL_MISSING','故障类型不存在。')
            if roi_scope:
                roi=session.scalar(select(RegionOfInterest).where(RegionOfInterest.scope==roi_scope))
                source=session.get(MediaAsset,roi.media_id) if roi else None
                if not roi or not (roi_scope=='camera:'+camera_id or (source and source.camera_id==camera_id and roi_scope=='media:'+source.id)):raise AppError('ROI_CAMERA','ROI不属于当前摄像头。')
            row=session.get(SettingRecord,'camera_detector_configurations')
            if not row:row=SettingRecord(key='camera_detector_configurations',value={'items':[]});session.add(row)
            items=copy.deepcopy(row.value.get('items',[]))
            record={'id':str(uuid4()),'camera_id':camera_id,'model_version_id':model_version_id,'fault_ids':faults,'roi_scope':roi_scope,'created_at':utc_now(),'enabled':False,'purpose':'configuration_only'}
            items.append(record);row.value={'items':items}
            return record
    def register(self,path,details,root=None,*,trusted=False,training_completion=None):
        source=Path(path)
        if not trusted:raise AppError('MODEL_TRUST','仅导入可信权重；PT文件可能执行代码，请明确确认来源可信。')
        allowed={'.pt','.onnx'}
        if details.get('backend')=='rfdetr':
            if details.get('model')!='rfdetr-nano' or details.get('artifact_format')!='rf-detr-weights-pth' or details.get('parity',{}).get('status')!='PASS' or not details.get('evaluation_protocol_sha256'):raise AppError('RF_MODEL_GATE','RF权重需先通过可信CUDA加载、统一评估与重载一致性检查。恢复CKPT不能登记为推理权重。')
            allowed={'.pth'}
        if source.suffix.lower() not in allowed or not source.is_file():raise AppError('MODEL_FORMAT','模型文件格式与后端/用途不匹配。')
        mid=str(uuid4())
        with self.store.open(root) as (folder,db,_):
            target=folder/'models'/mid/source.name;target.parent.mkdir(parents=True)
            shutil.copyfile(source,target);digest=file_hash(target)
            if digest!=file_hash(source):raise AppError('MODEL_HASH','模型复制校验失败，未登记。')
            data=dict(copy.deepcopy(details),path=target.relative_to(folder).as_posix(),sha256=digest,state='EXPERIMENTAL',created_at=utc_now(),history=[{'action':'REGISTER','at':utc_now()}])
            with db.transaction() as s:
                s.add(ModelVersion(id=mid,details=data,revision=1))
                if training_completion:
                    rid,run_data=training_completion;row=s.get(TrainingRun,rid)
                    if row is None:raise AppError('RF_RUN_MISSING','训练记录缺失，模型登记事务回滚。')
                    row.details=dict(copy.deepcopy(run_data),state='SUCCEEDED',model_id=mid,completed_at=utc_now());row.revision+=1
        return mid
    def verify(self,mid,root=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as s:
            row=s.get(ModelVersion,mid)
            if not row:raise AppError('MODEL_MISSING','模型版本不存在。')
            p=safe_path(folder,row.details['path'])
            if not p.is_file() or file_hash(p)!=row.details['sha256']:raise AppError('MODEL_HASH','模型缺失或SHA256不符。')
            if row.details.get('onnx'):
                artifact=safe_path(folder,row.details['onnx']['path'])
                if not artifact.is_file() or file_hash(artifact)!=row.details['onnx']['sha256']:raise AppError('MODEL_HASH','ONNX工件缺失或SHA256不符。')
            return p,copy.deepcopy(row.details)
    def export(self,mid,parent,root=None):
        source,data=self.verify(mid,root);parent=Path(parent)
        if not parent.is_dir():raise AppError('MODEL_EXPORT','请选择已有输出目录。')
        target=parent/('IVAD-model-'+mid+'-'+uuid4().hex[:8]);stage=target.with_name('.'+target.name+'.partial');stage.mkdir()
        shutil.copyfile(source,stage/('model'+source.suffix.lower()))
        with self.store.open(root) as (folder,_,_):
            if data.get('onnx'):shutil.copyfile(safe_path(folder,data['onnx']['path']),stage/'model.onnx')
        manifest=dict(data,model_version_id=mid,files={p.name:file_hash(p) for p in stage.iterdir()},note='模型工件导出，不含应用程序。工业准确率与商业部署许可未验收。')
        atomic_json(stage/'model_manifest.json',manifest);stage.rename(target);return str(target)
    def record_validation(self,mid,result,version_id,root=None):
        self.verify(mid,root)
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            row=s.get(ModelVersion,mid);data=copy.deepcopy(row.details)
            data.setdefault('validations',[]).append({'at':utc_now(),'dataset_version':version_id,'result':result})
            if data['state']=='EXPERIMENTAL':data.update(metrics=result['metrics'],validation_passed=True,gpu_evidence=dict(data.get('gpu_evidence',{}),**result['evidence']),validation_dataset=version_id)
            row.details=data;row.revision+=1
    def transition(self,mid,state,expected_revision,root=None,*,approved=False,rollback=False,thresholds=None):
        self.verify(mid,root)
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            row=s.get(ModelVersion,mid)
            if row.revision!=expected_revision:raise AppError('MODEL_CONFLICT','模型状态已更新，请刷新。')
            data=copy.deepcopy(row.details);old=data['state'];metrics=data.get('metrics',{})
            if data.get('backend')=='rfdetr' and state=='PRODUCTION':raise AppError('RF_EXPERIMENTAL','P3.7-A RF模型仅允许工程实验，不授权生产发布。')
            if state=='CANDIDATE':
                thresholds=thresholds if thresholds is not None else {'precision':.5,'recall':.5,'map50':.5,'map50_95':.25}
                if set(thresholds)!={'precision','recall','map50','map50_95'} or any(not isinstance(v,(int,float)) or not math.isfinite(v) or not 0<=v<=1 for v in thresholds.values()):raise AppError('MODEL_GATE','候选指标门槛需为0–1。')
                if old!='EXPERIMENTAL' or not data.get('validation_passed') or not (data.get('gpu_evidence',{}).get('weight_changed') or data.get('gpu_evidence',{}).get('cuda_forward')) or not all(isinstance(metrics.get(k),(int,float)) and math.isfinite(metrics[k]) for k in ['precision','recall','map50','map50_95']):raise AppError('MODEL_GATE','需真实GPU验证及完整有限指标后才可申请候选；不代表工业合格。')
                if any(metrics[k]<value for k,value in thresholds.items()):raise AppError('MODEL_GATE','验证指标未达到所选候选门槛。')
                data['candidate_thresholds']=dict(thresholds)
            elif state=='PRODUCTION':
                if not approved:raise AppError('MODEL_APPROVAL','生产注册状态需用户在GUI中明确批准。')
                if old!='CANDIDATE' and not (rollback and any(h.get('to')=='PRODUCTION' for h in data['history'])):raise AppError('MODEL_GATE','仅候选模型或曾发布的历史版本可设为生产。')
                for other in s.scalars(select(ModelVersion)):
                    if other.id!=mid and other.details.get('state')=='PRODUCTION':
                        od=copy.deepcopy(other.details);od['state']='CANDIDATE';od['history'].append({'action':'REPLACED','by':mid,'at':utc_now()});other.details=od;other.revision+=1
            else:raise AppError('MODEL_STATE','不支持该状态变更。')
            data['state']=state;data['history'].append({'action':'ROLLBACK' if rollback else 'TRANSITION','from':old,'to':state,'at':utc_now(),'actor':'local_operator','approved':approved});row.details=data;row.revision+=1
        return mid
