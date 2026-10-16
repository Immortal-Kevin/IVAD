"""Draft lifecycle stored transactionally inside the existing Dataset aggregate."""
import copy,json,hashlib
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import Dataset,Annotation,ExtractedFrame,Camera,LabelCategory,MediaAsset
from ivad_app.storage.project_store import row_dict

class DatasetLifecycle:
    def list_datasets(self,root=None):
        with self.store.open(root) as (_,db,pid),db.transaction() as s:
            return [dict(row_dict(d),project_id=d.details.get('project_id',pid)) for d in s.scalars(select(Dataset).order_by(Dataset.created_at))]

    def training_versions(self,root=None):
        result=[]
        for version in self.versions(root):
            splits=version['summary'].get('splits',{})
            if not splits.get('train') or not splits.get('val'):continue
            try:self.snapshot(version['id'],root)
            except AppError:continue
            result.append(version)
        return result

    def load_dataset(self,dataset_id,root=None):
        return next((d for d in self.list_datasets(root) if d['id']==dataset_id),None)

    def save_draft(self,payload,root=None):
        name=payload.get('name','').strip();did=payload.get('dataset_id') or str(uuid4());expected=payload.get('expected_revision',0)
        if not name or len(name)>120:raise AppError('DATASET_NAME','请输入1–120字符的数据集名称。')
        if payload.get('task','detect')!='detect':raise AppError('DATASET_TASK','本轮草稿仅支持Detection。')
        cameras=set(payload.get('camera_ids',[]));faults=set(payload.get('fault_ids',[]));ids=list(dict.fromkeys(payload.get('frame_ids',[])))
        if not cameras or not faults:raise AppError('DATASET_SCOPE','必须明确目标摄像头及故障类型。')
        if len(cameras)>1 and not payload.get('allow_multi_camera'):raise AppError('MULTI_CAMERA_CONSENT','多摄像头草稿需要明确共享授权。')
        with self.store.open(root) as (_,db,pid),db.transaction(camera_write=True) as s:
            if payload.get('project_id',pid)!=pid:raise AppError('DATASET_PROJECT','项目UUID不匹配。')
            d=s.get(Dataset,did)
            if (d.revision if d else 0)!=expected:raise AppError('DRAFT_CONFLICT','草稿已被其他操作修改，请重新打开，内存修改仍保留。')
            if d and d.details.get('project_id',pid)!=pid:raise AppError('DATASET_PROJECT','数据集所属项目不匹配。')
            if any(c!='__unlinked__' and not s.get(Camera,c) for c in cameras):raise AppError('DATASET_CAMERA','目标摄像头不存在。')
            if any(not s.get(LabelCategory,f) or not s.get(LabelCategory,f).enabled for f in faults):raise AppError('DATASET_FAULT','目标故障类型不存在或停用。')
            members=[]
            for fid in ids:
                frame=s.get(ExtractedFrame,fid);doc=s.scalar(select(Annotation).where(Annotation.frame_id==fid))
                if not frame or not doc:raise AppError('DRAFT_MEMBER','草稿图片或已保存标注不存在：'+fid)
                media=s.get(MediaAsset,frame.media_id)
                if (media.camera_id or '__unlinked__') not in cameras:raise AppError('DATASET_CAMERA','图片不属于已授权摄像头。')
                if any(o.get('label_id') not in faults for o in doc.payload.get('objects',[])):raise AppError('DATASET_FAULT','图片含其他故障类别，请明确选择多类别；不会静默丢弃目标。')
                members.append({'frame_id':fid,'annotation_id':doc.id,'annotation_revision':doc.revision})
            now=utc_now()
            if not d:d=Dataset(id=did,name=name,created_at=now,details={},revision=0);s.add(d)
            d.name=name;d.revision+=1;d.details={'project_id':pid,'task':'detect','camera_ids':sorted(cameras),'fault_ids':sorted(faults),'allow_multi_camera':bool(payload.get('allow_multi_camera')),'updated_at':now,'draft':{'state':'DRAFT','revision':d.revision,'members':members,'settings':copy.deepcopy(payload.get('settings',{})),'saved_at':now,'validation':None}}
            s.flush();result=dict(row_dict(d),project_id=pid)
        return result

    @staticmethod
    def validation_signature(plan):
        value={'samples':plan['samples'],'classes':plan['classes'],'issues':plan['issues'],'split_counts':plan['split_counts'],'split_status':plan['split_status'],'warnings':plan.get('warnings',[]),'configuration':plan.get('configuration')}
        return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode('utf-8')).hexdigest()

    def draft_plan(self,dataset_id,root=None,expected_revision=None):
        d=self.load_dataset(dataset_id,root)
        if not d or not d['details'].get('draft'):raise AppError('DRAFT_MISSING','请先保存数据集草稿。')
        if expected_revision is not None and d['revision']!=expected_revision:raise AppError('DRAFT_CONFLICT','草稿修订已变化，请重新载入。')
        draft=d['details']['draft'];settings=draft['settings'];ids=[m['frame_id'] for m in draft['members']]
        mode=settings.get('validation_mode');engineering=mode=='engineering'
        if mode not in {None,'engineering','strict'}:raise AppError('DATASET_MODE','数据集验证模式无效。')
        settings=dict(settings)
        if mode:settings.update(allow_leakage=engineering,allow_limited=engineering)
        plan=self.split_preview(ids,root,strategy=settings.get('strategy','source'),ratios=settings.get('ratios',[70,20,10]),seed=settings.get('seed',123),allow_leakage=settings.get('allow_leakage',False),admission='experimental',preset=settings.get('preset','standard'),pipeline_fallback=bool(settings.get('allow_leakage') and settings.get('allow_limited')),fault_ids=d['details']['fault_ids'])
        with self.store.open(root) as (_,db,_),db.transaction() as s:
            for item in draft['members']:
                doc=s.get(Annotation,item['annotation_id']);frame=s.get(ExtractedFrame,item['frame_id'])
                if not doc or doc.frame_id!=item['frame_id'] or doc.revision!=item['annotation_revision']:plan['issues'].append('草稿保存后标注修订已变化，请重新保存：'+item['frame_id'])
                if frame:
                    mid=s.get(MediaAsset,frame.media_id)
                    if (mid.camera_id or '__unlinked__') not in d['details']['camera_ids']:plan['issues'].append('图片摄像头超出数据集授权')
        if any(o['label_id'] not in d['details']['fault_ids'] for sample in plan['samples'] for o in sample['annotation']['objects']):plan['issues'].append('目标类别超出数据集故障范围')
        plan['configuration']=settings
        if mode=='strict' and plan['split_status']!='PASS':plan['issues'].append('严格验证未通过：独立来源、集合完整性或泄漏检查不足。请补充独立样本。')
        if plan['issues']:plan['split_status']='BLOCKED'
        plan['risk_confirmation_required']=engineering and plan['split_status']=='LIMITED' and draft.get('risk_ack')!=self.validation_signature(plan)
        return d,plan

    def acknowledge_draft_risk(self,dataset_id,signature,root=None,expected_revision=None):
        d,plan=self.draft_plan(dataset_id,root,expected_revision)
        if plan['issues'] or not plan['risk_confirmation_required'] or signature!=self.validation_signature(plan):raise AppError('DATASET_RISK','检查结果已变化，请重新检查并确认。')
        with self.store.open(root) as (_,db,_),db.transaction(camera_write=True) as s:
            live=s.get(Dataset,dataset_id)
            if live.revision!=d['revision']:raise AppError('DRAFT_CONFLICT','风险确认时草稿已变化。')
            details=copy.deepcopy(live.details);details['draft']['risk_ack']=signature;live.details=details

    def validate_draft(self,dataset_id,root=None,expected_revision=None):
        d,plan=self.draft_plan(dataset_id,root,expected_revision);signature=self.validation_signature(plan)
        report={k:copy.deepcopy(plan[k]) for k in ['split_status','count','objects','classes','warnings','issues','split_counts','statistics','source_groups','effective_strategy','preset']}
        with self.store.open(root) as (_,db,_),db.transaction(camera_write=True) as s:
            live=s.get(Dataset,dataset_id)
            if not live or live.revision!=d['revision']:raise AppError('DRAFT_CONFLICT','校验期间草稿发生变化，请重试。')
            details=copy.deepcopy(live.details);draft=details['draft'];draft['state']='DRAFT' if plan['issues'] or plan['risk_confirmation_required'] else 'VALIDATED';draft['validation']={'signature':signature,'at':utc_now(),'report':report};live.details=details
        return {'dataset':self.load_dataset(dataset_id,root),'plan':plan}

    def lifecycle_freeze_payload(self,payload):
        d,plan=self.draft_plan(payload['dataset_id'],payload['root'],payload['draft_revision']);draft=d['details']['draft'];validation=draft.get('validation')
        if draft['state']!='VALIDATED' or not validation or plan['issues'] or validation['signature']!=self.validation_signature(plan):raise AppError('DRAFT_VALIDATION','草稿未检查通过或源数据已变化，请保存并重新检查。')
        settings=dict(draft['settings'])
        if settings.get('validation_mode'):
            engineering=settings['validation_mode']=='engineering'
            settings.update(allow_leakage=engineering,allow_limited=engineering and draft.get('risk_ack')==validation['signature'])
        return dict(payload,validation_mode=settings.get('validation_mode','legacy'),risk_ack=draft.get('risk_ack'),dataset_scope={k:copy.deepcopy(d['details'][k]) for k in ['project_id','task','camera_ids','fault_ids']},fault_ids=d['details']['fault_ids'],name=d['name'],frame_ids=[m['frame_id'] for m in draft['members']],strategy=settings.get('strategy','source'),ratios=settings.get('ratios',[70,20,10]),seed=settings.get('seed',123),allow_leakage=settings.get('allow_leakage',False),allow_limited=settings.get('allow_limited',False),allow_multi_camera=d['details']['allow_multi_camera'],admission='experimental',preset=settings.get('preset','standard'),pipeline_fallback=bool(settings.get('allow_leakage') and settings.get('allow_limited')),draft_signature=validation['signature'])
