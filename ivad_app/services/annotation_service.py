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
        if camera and not media.camera_id: raise AppError('ROI_CAMERA','当前视频未关联摄像头。ROI 为可选辅助信息，不影响基础标注；如需保存 ROI，请选择关联当前视频。')
        return 'camera:'+media.camera_id if camera else 'media:'+media.id

    def load(self,frame_id,root=None,camera_roi=False):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            frame=session.get(ExtractedFrame,frame_id)
            if not frame: raise AppError('FRAME_MISSING','候选帧不存在。')
            media=session.get(MediaAsset,frame.media_id)
            # Optional camera ROI must never prevent loading ordinary annotations.
            effective_camera_roi=bool(camera_roi and media.camera_id)
            scope=self.scope(media,effective_camera_roi)
            doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
            roi=session.scalar(select(RegionOfInterest).where(RegionOfInterest.scope==scope))
            payload=copy.deepcopy(doc.payload) if doc else {'objects':[],'image_tag':'UNKNOWN','image_label_id':None,'coordinate_system':'image_pixels','width':frame.width,'height':frame.height}
            objects=copy.deepcopy(roi.payload.get('objects',[])) if roi else []
            for obj in objects:
                if obj['kind']=='roi_box':obj['geometry']=[v*(frame.width if i%2==0 else frame.height) for i,v in enumerate(obj['geometry'])]
                else:obj['geometry']=[[x*frame.width,y*frame.height] for x,y in obj['geometry']]
            return {'frame':dict(row_dict(frame),media_id=media.id,camera_id=media.camera_id),'payload':payload,'revision':doc.revision if doc else 0,'status':doc.status if doc else 'DRAFT','source':'Human Generated','scope':scope,'roi_revision':roi.revision if roi else 0,'roi_objects':objects,'camera_roi':effective_camera_roi,'camera_available':bool(media.camera_id),'processing_state':self.processing_state(frame,doc),'completion_state':self.completion_state(frame,doc),'notice':'' if media.camera_id else '当前视频未配置摄像头编号。ROI 为可选辅助信息，不影响基础标注。'}

    def save(self,frame_id,payload,status,expected_revision,roi_objects=None,expected_roi_revision=0,camera_roi=False,root=None,completion_state=None):
        if (status is not None and status not in REVIEW_STATES) or payload.get('image_tag') not in IMAGE_TAGS: raise AppError('ANNOTATION_STATE','图片标签或审核状态无效。')
        if completion_state not in {None,'UNLABELED','LABELED'}:raise AppError('COMPLETION_STATE','标注完成状态无效。')
        objects=copy.deepcopy(payload.get('objects',[])); seen=set()
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            frame=session.get(ExtractedFrame,frame_id)
            if not frame: raise AppError('FRAME_MISSING','候选帧不存在。')
            if frame.handling.get('is_excluded'):raise AppError('FRAME_EXCLUDED','图片已剔除，请先恢复再修改标注。')
            doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
            if (doc.revision if doc else 0)!=expected_revision: raise AppError('ANNOTATION_CONFLICT','标注被其他操作修改，已阻止覆盖；请重新载入。')
            preserve_review=status is None
            status=(doc.status if doc else 'DRAFT') if preserve_review else status
            truth_changed=not doc or any(doc.payload.get(k)!=payload.get(k) for k in ['objects','image_tag','image_label_id'])
            if payload['image_tag']=='NORMAL':
                if objects or payload.get('image_label_id'):raise AppError('NORMAL_CONFLICT','正常帧不能包含故障目标或整帧故障类别，请明确确认转换。')
                if doc and (doc.payload.get('objects') or doc.payload.get('image_label_id') or (doc.payload.get('image_tag')=='ABNORMAL' and doc.status in {'REVIEWED','APPROVED'})) and not payload.get('normal_conversion_confirmed'):
                    raise AppError('NORMAL_CONFIRM_REQUIRED','当前图片已有异常标注，改为正常可能清除相关内容。请明确确认。')
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
            saved.pop('normal_conversion_confirmed',None)
            if not doc:
                doc=Annotation(id=str(uuid4()),frame_id=frame_id,payload={},status='DRAFT',revision=0,source='Human Generated',updated_at=utc_now());session.add(doc);session.flush()
            doc.payload=saved;doc.status=status;doc.revision+=1;doc.updated_at=utc_now();doc.source='Human Generated'
            handling=copy.deepcopy(frame.handling)
            handling['completion_state']=completion_state or ('LABELED' if payload['image_tag'] in {'NORMAL','ABNORMAL'} else 'UNLABELED')
            handling['review_stale']=bool(handling.get('review_stale') or truth_changed) if preserve_review else False
            handling['revision']=handling.get('revision',0)+1;handling['completion_updated_at']=utc_now();frame.handling=handling
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
                    roi=RegionOfInterest(id=str(uuid4()),scope=scope,media_id=frame.media_id,camera=media.camera,camera_id=media.camera_id if camera_roi else None,payload={'objects':[],'history':[]},revision=0,updated_at=utc_now());session.add(roi)
                history=copy.deepcopy(roi.payload.get('history',[]))
                history.append({'revision':roi.revision+1,'objects':normalized,'source':'Human Generated','updated_at':utc_now()})
                roi.payload={'objects':normalized,'history':history,'coordinate_system':'normalized_video'};roi.revision+=1;roi.updated_at=utc_now();roi_revision=roi.revision
            result={'revision':doc.revision,'roi_revision':roi_revision,'status':doc.status,'completion_state':self.completion_state(frame,doc)}
        self.logs.write('annotation','人工标注与ROI已事务保存，保留修改版本。');return result

    @staticmethod
    def processing_state(frame,doc):
        if frame.handling.get('is_excluded'):return 'EXCLUDED'
        if not doc:return 'UNPROCESSED'
        tag=doc.payload.get('image_tag','UNKNOWN')
        if tag=='NORMAL' and (doc.payload.get('objects') or doc.payload.get('image_label_id')):return 'CONFLICT'
        return {'NORMAL':'NORMAL','ABNORMAL':'ABNORMAL','UNKNOWN':'UNCERTAIN'}.get(tag,'CONFLICT')

    @classmethod
    def completion_state(cls,frame,doc):
        if cls.processing_state(frame,doc) not in {'NORMAL','ABNORMAL'}:return 'UNLABELED'
        return frame.handling.get('completion_state','LABELED')

    def review_frames(self,expected,status,root=None):
        if status not in REVIEW_STATES:raise AppError('REVIEW_STATE','审核状态无效。')
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            for fid,revision in expected.items():
                frame=session.get(ExtractedFrame,fid);doc=session.scalar(select(Annotation).where(Annotation.frame_id==fid))
                if not frame or not doc or doc.revision!=revision:raise AppError('REVIEW_CONFLICT','标注已改变，审核批次未提交。')
                if frame.handling.get('is_excluded') or (status in {'REVIEWED','APPROVED'} and self.completion_state(frame,doc)!='LABELED'):raise AppError('REVIEW_INCOMPLETE','只能人工审核有效且已完成的标注，剔除/未知/冲突不能放行。')
                doc.status=status;doc.revision+=1;doc.updated_at=utc_now()
                session.add(AnnotationRevision(id=str(uuid4()),annotation_id=doc.id,revision=doc.revision,payload=copy.deepcopy(doc.payload),status=status,source=doc.source,created_at=utc_now()))
                handling=copy.deepcopy(frame.handling);handling.update(review_stale=False,reviewed_at=utc_now(),revision=handling.get('revision',0)+1);frame.handling=handling
        return len(expected)

    def frames_status(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(ExtractedFrame,Annotation).outerjoin(Annotation,Annotation.frame_id==ExtractedFrame.id)).all()
            return {f.id:{'processing_state':self.processing_state(f,d),'completion_state':self.completion_state(f,d),'review_stale':f.handling.get('review_stale',False),'annotation_revision':d.revision if d else 0,'handling_revision':f.handling.get('revision',0),'review_status':d.status if d else 'DRAFT'} for f,d in rows}

    def batch_preview(self,frame_ids,action,root=None):
        if action not in {'normal','exclude','restore'}:raise AppError('FRAME_ACTION','帧操作无效。')
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            eligible=[];skipped=[];annotated=referenced=0
            for fid in dict.fromkeys(frame_ids):
                f=session.get(ExtractedFrame,fid);d=session.scalar(select(Annotation).where(Annotation.frame_id==fid))
                if not f:skipped.append({'id':fid,'reason':'图片不存在'});continue
                from ivad_app.storage.models import DatasetSample
                ref=bool(session.scalar(select(DatasetSample.id).where(DatasetSample.frame_id==fid)))
                state=self.processing_state(f,d);has_truth=bool(d and (d.payload.get('objects') or d.payload.get('image_label_id') or d.status in {'REVIEWED','APPROVED'}))
                annotated+=int(has_truth);referenced+=int(ref)
                reason=None
                if action=='normal' and (state not in {'UNPROCESSED','NORMAL'} or has_truth):reason='异常/待复核/已审核/冲突/已剔除，禁止批量覆盖'
                if action=='exclude' and (state=='EXCLUDED' or has_truth or ref):reason='已剔除、已有标注/审核或被冻结数据集引用，需保留'
                if action=='restore' and state!='EXCLUDED':reason='尚未剔除'
                if reason:skipped.append({'id':fid,'reason':reason});continue
                eligible.append({'id':fid,'annotation_revision':d.revision if d else 0,'handling_revision':f.handling.get('revision',0),'previous_state':state})
            return {'action':action,'selected':len(dict.fromkeys(frame_ids)),'eligible':eligible,'skipped':skipped,'annotated':annotated,'referenced':referenced}

    def batch_apply(self,preview,reason='',root=None,actor='local_operator'):
        action=preview['action']
        if action=='exclude' and not reason.strip():raise AppError('EXCLUSION_REASON','请选择或填写剔除原因。')
        current=self.batch_preview([r['id'] for r in preview['eligible']],action,root)
        if current['eligible']!=preview['eligible'] or current['skipped']:raise AppError('BATCH_CONFLICT','预览后数据或引用已改变，批次没有写入，请重新检查。')
        now=utc_now()
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            from ivad_app.storage.models import DatasetSample
            for item in preview['eligible']:
                f=session.get(ExtractedFrame,item['id']);d=session.scalar(select(Annotation).where(Annotation.frame_id==f.id))
                if (d.revision if d else 0)!=item['annotation_revision'] or f.handling.get('revision',0)!=item['handling_revision']:raise AppError('BATCH_CONFLICT','图片在批量操作期间被修改，整个批次已回滚。')
                if action=='exclude' and session.scalar(select(DatasetSample.id).where(DatasetSample.frame_id==f.id)):raise AppError('FRAME_REFERENCED','图片在预览后被数据集引用，整个批次已回滚。')
                if action=='normal':
                    if not d:
                        d=Annotation(id=str(uuid4()),frame_id=f.id,payload={},status='DRAFT',revision=0,source='Human Generated',updated_at=now);session.add(d);session.flush()
                    payload={'objects':[],'image_tag':'NORMAL','image_label_id':None,'coordinate_system':'image_pixels','width':f.width,'height':f.height,'operator':actor,'operation':'BATCH_NORMAL'}
                    d.payload=payload;d.revision+=1;d.status='DRAFT';d.updated_at=now
                    handling=copy.deepcopy(f.handling);handling.update(completion_state='LABELED',review_stale=True,revision=handling.get('revision',0)+1);f.handling=handling
                    session.add(AnnotationRevision(id=str(uuid4()),annotation_id=d.id,revision=d.revision,payload=payload,status=d.status,source='Human Generated',created_at=now))
                else:
                    handling=copy.deepcopy(f.handling);history=list(handling.get('history',[]));history.append({'action':action,'at':now,'by':actor,'reason':reason,'previous_state':item['previous_state']})
                    handling.update(history=history,revision=item['handling_revision']+1,is_excluded=action=='exclude')
                    if action=='exclude':handling.update(previous_state=item['previous_state'],exclusion_reason=reason,excluded_at=now,excluded_by=actor)
                    else:handling['restored_at']=now
                    f.handling=handling
        self.logs.write('annotation',f'帧操作 {action}：已处理{len(preview["eligible"])}，跳过{len(preview["skipped"])}，保留历史。')
        return {'changed':len(preview['eligible']),'skipped':preview['skipped']}

    def revisions(self,frame_id,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
            return [row_dict(r) for r in session.scalars(select(AnnotationRevision).where(AnnotationRevision.annotation_id==doc.id).order_by(AnnotationRevision.revision.desc()))] if doc else []

    def restore_revision(self,frame_id,revision,expected_revision,root=None):
        rows=self.revisions(frame_id,root);target=next((r for r in rows if r['revision']==revision),None)
        if not target:raise AppError('REVISION_MISSING','历史标注版本不存在。')
        payload=copy.deepcopy(target['payload']);payload['operation']='RESTORE_REVISION';payload['restored_revision']=revision
        return self.save(frame_id,payload,target['status'],expected_revision,root=root)

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
