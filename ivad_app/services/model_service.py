"""Project model registry; no unpickling in the GUI process and no deployment."""
import copy,shutil,math
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import ModelVersion
from ivad_app.storage.project_store import safe_path,file_hash
from ivad_app.storage.project_store import atomic_json

class ModelService:
    def __init__(self,store,logs):self.store,self.logs=store,logs
    def versions(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            return [dict(id=r.id,revision=r.revision,**r.details) for r in s.scalars(select(ModelVersion))]
    def register(self,path,details,root=None,*,trusted=False):
        source=Path(path)
        if not trusted:raise AppError('MODEL_TRUST','仅导入可信权重；PT文件可能执行代码，请明确确认来源可信。')
        if source.suffix.lower() not in {'.pt','.onnx'} or not source.is_file():raise AppError('MODEL_FORMAT','请选择存在的PT或ONNX模型。')
        mid=str(uuid4())
        with self.store.open(root) as (folder,db,_):
            target=folder/'models'/mid/source.name;target.parent.mkdir(parents=True)
            shutil.copyfile(source,target);digest=file_hash(target)
            if digest!=file_hash(source):raise AppError('MODEL_HASH','模型复制校验失败，未登记。')
            data=dict(copy.deepcopy(details),path=target.relative_to(folder).as_posix(),sha256=digest,state='EXPERIMENTAL',created_at=utc_now(),history=[{'action':'REGISTER','at':utc_now()}])
            with db.transaction() as s:s.add(ModelVersion(id=mid,details=data,revision=1))
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
        shutil.copyfile(source,stage/'model.pt' if source.suffix.lower()=='.pt' else stage/'model.onnx')
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
