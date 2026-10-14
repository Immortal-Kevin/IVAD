import copy
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import Camera,MediaAsset
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
    def list(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            return [row_dict(c) for c in session.scalars(select(Camera).order_by(Camera.name,Camera.id))]
    def save(self,name,camera_id=None,revision=None,root=None):
        name=name.strip()
        if not name or len(name)>200:raise AppError('CAMERA_NAME','摄像头名称不能为空且不超过200个字符。')
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            row=session.get(Camera,camera_id) if camera_id else None
            if camera_id and (not row or row.revision!=revision):raise AppError('CAMERA_CONFLICT','摄像头被其他操作修改，请刷新。')
            if not row:
                row=Camera(id=str(uuid4()),name=name,legacy_key=None,revision=0,history=[]);session.add(row)
            history=copy.deepcopy(row.history);history.append({'action':'RENAME' if row.revision else 'CREATE','previous_name':row.name,'name':name,'at':utc_now(),'by':'local_operator'})
            row.name=name;row.revision+=1;row.history=history;session.flush();result=row_dict(row)
        self.logs.write('camera','摄像头已保存，UUID保持稳定。');return result
    def associate(self,media_id,camera_id,expected_camera_id,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            row=session.get(MediaAsset,media_id)
            if not row:raise AppError('MEDIA_MISSING','录像不存在。')
            parent=session.get(MediaAsset,row.parent_id) if row.parent_id else row
            if row.camera_id!=expected_camera_id:raise AppError('CAMERA_LINK_CONFLICT','录像关联已改变，请重载后再关联。')
            camera=session.get(Camera,camera_id) if camera_id else None
            if camera_id and not camera:raise AppError('CAMERA_MISSING','摄像头不存在。')
            rows=list(session.scalars(select(MediaAsset).where((MediaAsset.id==parent.id)|(MediaAsset.parent_id==parent.id))))
            for media in rows:
                info=copy.deepcopy(media.clip_info);history=list(info.get('camera_association_history',[]));history.append({'previous_id':media.camera_id,'camera_id':camera_id,'at':utc_now(),'by':'local_operator'})
                info['camera_association_history']=history;media.clip_info=info;media.camera_id=camera_id
                media.camera=camera.name if camera else ''
            result={'camera_id':camera_id,'media_ids':[m.id for m in rows]}
        self.logs.write('camera','录像及来源片段的摄像头关联已事务保存。');return result
