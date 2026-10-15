import copy
from uuid import uuid4
from sqlalchemy import select, text
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import Camera,MediaAsset,ProjectRecord
from ivad_app.storage.project_store import row_dict

class CameraService:
    def __init__(self,store,logs):self.store,self.logs=store,logs
    @staticmethod
    def legacy(session,name):
        if not name:return None
        row=session.scalar(select(Camera).where(Camera.legacy_key==name))
        if not row:
            row=Camera(id=str(uuid4()),name=name,legacy_key=name,revision=1,history=[{'action':'IMPORT_LEGACY','at':utc_now()}]);session.add(row);session.flush()
        return row.id
    def list(self,root=None,available_only=False):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            return [row_dict(c) for c in session.scalars(select(Camera).order_by(Camera.name,Camera.id)) if not available_only or c.details.get('enabled',True)]
    @staticmethod
    def _snapshot(session):
        cameras={c.id:copy.deepcopy(row_dict(c)) for c in session.scalars(select(Camera))}
        # Capture actual persisted references/content, independent of GUI caches.
        tables=['projects','media_assets','frames','rois','annotations','annotation_revisions',
                'datasets','dataset_versions','dataset_samples','training_runs','model_versions','clip_labels','exports']
        references={t:session.execute(text('SELECT * FROM '+t+' ORDER BY rowid')).fetchall() for t in tables}
        return cameras,references
    @staticmethod
    def _verify(before,after,camera_id,mode):
        old,refs=before;new,newrefs=after
        expected=set(old)|{camera_id} if mode=='CREATE' else set(old)
        if set(new)!=expected or len(new)!=len(old)+(mode=='CREATE'):
            raise AppError('CAMERA_INTEGRITY','摄像头数量或UUID集合异常，事务已拒绝提交。')
        if mode=='CREATE' and camera_id in old:
            raise AppError('CAMERA_INTEGRITY','新建UUID已存在，事务已拒绝提交。')
        if any(new[k]!=v for k,v in old.items() if k!=camera_id) or refs!=newrefs:
            raise AppError('CAMERA_INTEGRITY','其他摄像头或历史关联发生变化，事务已拒绝提交。')
    def save(self,name,camera_id=None,revision=None,root=None,details=None,*,mode=None):
        mode=mode or ('EDIT' if camera_id else 'CREATE')
        if mode not in {'CREATE','EDIT'} or (mode=='CREATE' and camera_id) or (mode=='EDIT' and not camera_id):
            raise AppError('CAMERA_MODE','新建/编辑状态与UUID不一致，已拒绝保存。')
        name=name.strip()
        if not name or len(name)>200:raise AppError('CAMERA_NAME','摄像头名称不能为空且不超过200个字符。')
        try:
            with self.store.open(root) as (_,db,project_id),db.transaction(camera_write=True) as session:
                if list(session.scalars(select(ProjectRecord.id)))!=[project_id]:raise AppError('CAMERA_PROJECT','摄像头所属项目身份不一致，拒绝写入。')
                before=self._snapshot(session)
                row=session.get(Camera,camera_id) if mode=='EDIT' else None
                if mode=='EDIT' and (not row or row.revision!=revision):raise AppError('CAMERA_CONFLICT','摄像头被其他操作修改，请刷新。')
                if mode=='CREATE':
                    row=Camera(id=str(uuid4()),name=name,legacy_key=None,revision=0,history=[]);session.add(row)
                previous=copy.deepcopy(row.details or {})
                if details is not None:
                    info={k:str(details.get(k,'')).strip() for k in ['code','location','equipment']};info['enabled']=bool(details.get('enabled',True))
                    if any(len(info[k])>200 for k in ['code','location','equipment']):raise AppError('CAMERA_DETAILS','摄像头资料每项不超过200字。')
                    if info['code'] and any(c.id!=row.id and str(c.details.get('code','')).strip()==info['code'] for c in session.scalars(select(Camera))):raise AppError('CAMERA_CODE','项目内摄像头编号已存在，不会覆盖原记录。')
                    row.details=info
                history=copy.deepcopy(row.history);history.append({'action':mode,'previous_name':row.name,'name':name,'previous_details':previous,'details':copy.deepcopy(row.details or {}),'at':utc_now(),'by':'local_operator','project_id':project_id})
                row.name=name;row.revision+=1;row.history=history;session.flush()
                after=self._snapshot(session);self._verify(before,after,row.id,mode)
                codes=[str(c['details'].get('code','')).strip() for c in after[0].values() if c['details'].get('code')]
                if len(codes)!=len(set(codes)):raise AppError('CAMERA_INTEGRITY','编号唯一性验证失败。')
                result=copy.deepcopy(row_dict(row))
        except Exception:
            try:self.logs.exception('camera','摄像头保存事务失败，未报告成功；请检查诊断。')
            except Exception:pass
            raise
        # Commit has completed; a diagnostic logging failure must not imply rollback.
        try:self.logs.write('camera',f'{mode}已提交；项目{project_id}，摄像头{result["id"]}，数量{len(before[0])}→{len(after[0])}，完整性验证通过。')
        except Exception:result['diagnostic_warning']='数据已提交，但诊断日志写入失败；不能视为已回滚，请核查磁盘。'
        return result
    def associate(self,media_id,camera_id,expected_camera_id,root=None,expected_signature=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as session:
            if expected_signature:
                from ivad_app.services.media_lifecycle import MediaLifecycle
                if MediaLifecycle._dependencies(self,session,media_id,folder)['signature']!=expected_signature:raise AppError('CAMERA_LINK_CONFLICT','下游范围已改变，请重新确认影响范围。')
            row=session.get(MediaAsset,media_id)
            if not row:raise AppError('MEDIA_MISSING','录像不存在。')
            if row.camera_id!=expected_camera_id:raise AppError('CAMERA_LINK_CONFLICT','录像关联已改变，请重载后再关联。')
            camera=session.get(Camera,camera_id) if camera_id else None
            if camera_id and not camera:raise AppError('CAMERA_MISSING','摄像头不存在。')
            if camera and not camera.details.get('enabled',True):raise AppError('CAMERA_DISABLED','停用摄像头不能建立新关联。')
            children=list(session.scalars(select(MediaAsset).where(MediaAsset.parent_id==row.id))) if not row.parent_id else []
            rows=[row]+[m for m in children if m.lifecycle.get('camera_binding')!='explicit' and m.camera_id==row.camera_id]
            skipped=[m.id for m in children if m not in rows]
            for media in rows:
                info=copy.deepcopy(media.clip_info);history=list(info.get('camera_association_history',[]));history.append({'previous_id':media.camera_id,'camera_id':camera_id,'at':utc_now(),'by':'local_operator'})
                info['camera_association_history']=history;media.clip_info=info;media.camera_id=camera_id
                media.camera=camera.name if camera else ''
                life=copy.deepcopy(media.lifecycle);life['camera_binding']='explicit' if media.id==row.id else 'inherited';media.lifecycle=life
            result={'camera_id':camera_id,'media_ids':[m.id for m in rows],'preserved_explicit_clips':skipped}
        self.logs.write('camera','录像及来源片段的摄像头关联已事务保存。');return result
