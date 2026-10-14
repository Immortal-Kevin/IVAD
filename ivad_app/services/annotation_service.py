import copy, json
from uuid import uuid4, UUID
from sqlalchemy import select
from ivad_app.core.contracts import AppError, utc_now
from ivad_app.storage.models import (LabelCategory, Annotation, AnnotationRevision, ExtractedFrame,
    MediaAsset, RegionOfInterest, VideoClipLabel, DatasetVersion)
from ivad_app.storage.project_store import row_dict
from ivad_app.annotations.geometry import validate_geometry

REVIEW_STATES={'DRAFT','REVIEWED','APPROVED','REJECTED'}
IMAGE_TAGS={'NORMAL','ABNORMAL','UNKNOWN'}
TEMPLATES=['皮带异物','落料口堵煤','异常积煤','煤流中断','未知异常']

class AnnotationService:
    def __init__(self, store, media, logs): self.store,self.media,self.logs=store,media,logs

    def labels(self, root=None, *, initialize=True):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=list(session.scalars(select(LabelCategory).order_by(LabelCategory.name)))
            if not rows and initialize:
                for name in TEMPLATES: session.add(LabelCategory(id=str(uuid4()),name=name,description='可编辑模板；没有对应已发布模型',device_type='',parent_id=None,annotation_type='box',enabled=1,revision=1))
                session.flush(); rows=list(session.scalars(select(LabelCategory).order_by(LabelCategory.name)))
            return [row_dict(r) for r in rows]

    def save_label(self, value, root=None):
        name=value.get('name','').strip()
        if not name or len(name)>120: raise AppError('LABEL_NAME','类别名称不能为空且不超过120个字符。')
        if value.get('annotation_type','box') not in {'box','polygon','image','clip'}: raise AppError('LABEL_TYPE','默认标注类型无效。')
        label_id=value.get('id') or str(uuid4()); parent=value.get('parent_id') or None
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            row=session.get(LabelCategory,label_id)
            if row and row.revision!=value.get('revision'): raise AppError('LABEL_CONFLICT','类别已被其他操作修改，请刷新后再保存。')
            ancestor=parent; seen={label_id}
            while ancestor:
                if ancestor in seen: raise AppError('LABEL_CYCLE','父级类别不能形成循环。')
                seen.add(ancestor); target=session.get(LabelCategory,ancestor)
                if not target: raise AppError('LABEL_PARENT','父级类别不存在。')
                ancestor=target.parent_id
            if not row:
                row=LabelCategory(id=label_id,name=name,description='',device_type='',parent_id=None,annotation_type='box',enabled=1,revision=0);session.add(row)
            row.name=name;row.description=value.get('description','');row.device_type=value.get('device_type','');row.parent_id=parent
            row.annotation_type=value.get('annotation_type','box');row.enabled=int(bool(value.get('enabled',True)));row.revision+=1
            session.flush(); result=row_dict(row)
        self.logs.write('annotation','故障类别已保存，UUID保持稳定。');return result

    def delete_label(self,label_id,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            needle='"'+label_id+'"'
            for model,column in [(Annotation,'payload'),(AnnotationRevision,'payload'),(RegionOfInterest,'payload'),(DatasetVersion,'summary')]:
                if any(needle in json.dumps(getattr(r,column)) for r in session.scalars(select(model))):
                    raise AppError('LABEL_REFERENCED','类别被标注/历史版本引用，不能删除；可禁用。')
            if session.scalar(select(VideoClipLabel.id).where(VideoClipLabel.label_id==label_id)) or session.scalar(select(LabelCategory.id).where(LabelCategory.parent_id==label_id)):
                raise AppError('LABEL_REFERENCED','类别被片段或子类别引用，不能删除；可禁用。')
            row=session.get(LabelCategory,label_id)
            if row: session.delete(row)

    @staticmethod
    def scope(media, camera=False):
        if camera and not media.camera: raise AppError('ROI_CAMERA','当前视频未配置摄像头编号。ROI 为可选辅助信息，不影响基础标注；如需保存 ROI，请选择关联当前视频。')
        return 'camera:'+media.camera if camera else 'media:'+media.id

    def load(self,frame_id,root=None,camera_roi=False):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            frame=session.get(ExtractedFrame,frame_id)
            if not frame: raise AppError('FRAME_MISSING','候选帧不存在。')
            media=session.get(MediaAsset,frame.media_id)
            # Optional camera ROI must never prevent loading ordinary annotations.
            effective_camera_roi=bool(camera_roi and media.camera)
            scope=self.scope(media,effective_camera_roi)
            doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
            roi=session.scalar(select(RegionOfInterest).where(RegionOfInterest.scope==scope))
            payload=copy.deepcopy(doc.payload) if doc else {'objects':[],'image_tag':'UNKNOWN','image_label_id':None,'coordinate_system':'image_pixels','width':frame.width,'height':frame.height}
            objects=copy.deepcopy(roi.payload.get('objects',[])) if roi else []
            for obj in objects:
                if obj['kind']=='roi_box':obj['geometry']=[v*(frame.width if i%2==0 else frame.height) for i,v in enumerate(obj['geometry'])]
                else:obj['geometry']=[[x*frame.width,y*frame.height] for x,y in obj['geometry']]
            return {'frame':row_dict(frame),'payload':payload,'revision':doc.revision if doc else 0,'status':doc.status if doc else 'DRAFT','source':'Human Generated','scope':scope,'roi_revision':roi.revision if roi else 0,'roi_objects':objects,'camera_roi':effective_camera_roi,'camera_available':bool(media.camera),'notice':'' if media.camera else '当前视频未配置摄像头编号。ROI 为可选辅助信息，不影响基础标注。'}

    def save(self,frame_id,payload,status,expected_revision,roi_objects=None,expected_roi_revision=0,camera_roi=False,root=None):
        if status not in REVIEW_STATES or payload.get('image_tag') not in IMAGE_TAGS: raise AppError('ANNOTATION_STATE','图片标签或审核状态无效。')
        objects=copy.deepcopy(payload.get('objects',[])); seen=set()
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            frame=session.get(ExtractedFrame,frame_id)
            if not frame: raise AppError('FRAME_MISSING','候选帧不存在。')
            doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
            if (doc.revision if doc else 0)!=expected_revision: raise AppError('ANNOTATION_CONFLICT','标注被其他操作修改，已阻止覆盖；请重新载入。')
            old_labels={o['id']:o.get('label_id') for o in doc.payload.get('objects',[])} if doc else {}
            for obj in objects:
                try:UUID(obj['id'])
                except (ValueError,KeyError,TypeError):raise AppError('ANNOTATION_ID','标注UUID无效。')
                if obj['id'] in seen:raise AppError('ANNOTATION_ID','标注UUID重复。')
                seen.add(obj['id']);validate_geometry(obj['kind'],obj['geometry'],frame.width,frame.height)
                if obj['kind'] not in {'box','polygon'}:raise AppError('ROI_SEPARATE','ROI必须独立保存，不是训练目标。')
                label=session.get(LabelCategory,obj.get('label_id'))
                if not label:raise AppError('LABEL_MISSING','标注故障类别不存在。')
                if not label.enabled and old_labels.get(obj['id'])!=label.id:raise AppError('LABEL_DISABLED','停用类别不能分配给新标注，历史标注可保留。')
                if obj.get('source','Human Generated')!='Human Generated':raise AppError('SOURCE_UNSUPPORTED','P2仅保存人工真值，不将AI建议自动转为真值。')
                obj['source']='Human Generated'
            if payload.get('image_label_id') and not session.get(LabelCategory,payload['image_label_id']):raise AppError('LABEL_MISSING','图片故障类别不存在。')
            saved=dict(payload,objects=objects,coordinate_system='image_pixels',width=frame.width,height=frame.height)
            if not doc:
                doc=Annotation(id=str(uuid4()),frame_id=frame_id,payload={},status='DRAFT',revision=0,source='Human Generated',updated_at=utc_now());session.add(doc);session.flush()
            doc.payload=saved;doc.status=status;doc.revision+=1;doc.updated_at=utc_now();doc.source='Human Generated'
            session.add(AnnotationRevision(id=str(uuid4()),annotation_id=doc.id,revision=doc.revision,payload=saved,status=status,source='Human Generated',created_at=utc_now()))
            roi_revision=expected_roi_revision
            if roi_objects is not None:
                media=session.get(MediaAsset,frame.media_id);scope=self.scope(media,camera_roi)
                roi=session.scalar(select(RegionOfInterest).where(RegionOfInterest.scope==scope))
                if (roi.revision if roi else 0)!=expected_roi_revision:raise AppError('ROI_CONFLICT','ROI被其他操作修改，请重新载入。')
                normalized=copy.deepcopy(roi_objects)
                roi_ids=set()
                for obj in normalized:
                    try:UUID(obj['id'])
                    except (ValueError,KeyError,TypeError):raise AppError('ROI_ID','ROI UUID无效。')
                    if obj['id'] in roi_ids:raise AppError('ROI_ID','ROI UUID重复。')
                    roi_ids.add(obj['id']);obj['source']='Human Generated'
                    if obj['kind'] not in {'roi_box','roi_polygon'}:raise AppError('ROI_TYPE','ROI类型无效。')
                    validate_geometry(obj['kind'],obj['geometry'],frame.width,frame.height)
                    if obj['kind']=='roi_box':obj['geometry']=[v/(frame.width if i%2==0 else frame.height) for i,v in enumerate(obj['geometry'])]
                    else:obj['geometry']=[[x/frame.width,y/frame.height] for x,y in obj['geometry']]
                if not roi:
                    roi=RegionOfInterest(id=str(uuid4()),scope=scope,media_id=frame.media_id,camera=media.camera,payload={'objects':[],'history':[]},revision=0,updated_at=utc_now());session.add(roi)
                history=copy.deepcopy(roi.payload.get('history',[]))
                history.append({'revision':roi.revision+1,'objects':normalized,'source':'Human Generated','updated_at':utc_now()})
                roi.payload={'objects':normalized,'history':history,'coordinate_system':'normalized_video'};roi.revision+=1;roi.updated_at=utc_now();roi_revision=roi.revision
            result={'revision':doc.revision,'roi_revision':roi_revision,'status':doc.status}
        self.logs.write('annotation','人工标注与ROI已事务保存，保留修改版本。');return result

    def clips(self,media_id,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            return [row_dict(r) for r in session.scalars(select(VideoClipLabel).where(VideoClipLabel.media_id==media_id,VideoClipLabel.deleted==0).order_by(VideoClipLabel.start_us))]

    def save_clip(self,value,root=None):
        if value.get('tag') not in IMAGE_TAGS or value.get('status') not in REVIEW_STATES:raise AppError('CLIP_STATE','片段标签/审核状态无效。')
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            media=session.get(MediaAsset,value['media_id']);start=int(value['start_us']);end=int(value['end_us'])
            if not media or not 0<=start<end<=media.video['duration_us']:raise AppError('CLIP_RANGE','片段范围必须在视频有效时段内。')
            if value.get('label_id') and not session.get(LabelCategory,value['label_id']):raise AppError('LABEL_MISSING','片段类别不存在。')
            clip=session.get(VideoClipLabel,value.get('id',''))
            if clip and (clip.revision!=value.get('revision') or clip.media_id!=media.id):raise AppError('CLIP_CONFLICT','片段被其他操作修改，请刷新。')
            if not clip:
                clip=VideoClipLabel(id=str(uuid4()),media_id=media.id,start_us=start,end_us=end,tag=value['tag'],label_id=None,status='DRAFT',revision=0,source='Human Generated',updated_at=utc_now(),history=[],deleted=0);session.add(clip)
            history=list(clip.history)
            history.append({'revision':clip.revision+1,'start_us':start,'end_us':end,'tag':value['tag'],'label_id':value.get('label_id'),'status':value['status'],'updated_at':utc_now()})
            clip.start_us=start;clip.end_us=end;clip.tag=value['tag'];clip.label_id=value.get('label_id');clip.status=value['status'];clip.revision+=1;clip.updated_at=utc_now();clip.history=history
            session.flush();return row_dict(clip)

    def delete_clip(self,clip_id,revision,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            clip=session.get(VideoClipLabel,clip_id)
            if not clip or clip.revision!=revision:raise AppError('CLIP_CONFLICT','片段不存在或版本已变化。')
            clip.deleted=1;clip.revision+=1;clip.updated_at=utc_now()
