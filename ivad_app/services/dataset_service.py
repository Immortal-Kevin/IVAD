from ivad_app.video.timestamps import frame_times
import copy, json, random, shutil
from collections import Counter
from PIL import Image
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, func
from ivad_app.core.contracts import AppError, utc_now
from ivad_app.storage.models import (Dataset, DatasetVersion, DatasetSample, ExportRecord, ExtractedFrame,
    Annotation, LabelCategory, MediaAsset, RegionOfInterest, VideoClipLabel, Camera)
from ivad_app.storage.project_store import file_hash, atomic_json, safe_path, row_dict
from ivad_app.annotations.geometry import validate_geometry
from ivad_app.datasets.exporters import export_snapshot
from ivad_app.services.annotation_service import AnnotationService

from ivad_app.services.dataset_lifecycle import DatasetLifecycle
from ivad_app.datasets.splitting import PRESETS,assign_groups,split_statistics

class DatasetService(DatasetLifecycle):
    def __init__(self,store,logs):self.store,self.logs=store,logs

    def camera_samples(self,camera_id=None,*,image_tag=None,fault_id=None,root=None,include_excluded=False):
        """Persisted camera reference samples; completion does not grant training approval."""
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(ExtractedFrame,Annotation,MediaAsset).join(Annotation,Annotation.frame_id==ExtractedFrame.id).join(MediaAsset,MediaAsset.id==ExtractedFrame.media_id)).all()
            result=[]
            for frame,doc,media in rows:
                if camera_id=='__unlinked__' and media.camera_id:continue
                if camera_id not in {None,'__unlinked__'} and media.camera_id!=camera_id:continue
                if not include_excluded and frame.handling.get('is_excluded'):continue
                if image_tag and doc.payload.get('image_tag')!=image_tag:continue
                faults={o.get('label_id') for o in doc.payload.get('objects',[])}|{doc.payload.get('image_label_id')}
                if fault_id and fault_id not in faults:continue
                result.append(dict(row_dict(frame),camera_id=media.camera_id,source_group_id=media.parent_id or media.id,image_tag=doc.payload.get('image_tag'),fault_ids=sorted(f for f in faults if f),review_status=doc.status,review_stale=frame.handling.get('review_stale',False),completion_state=AnnotationService.completion_state(frame,doc),annotation_revision=doc.revision))
            return result

    @staticmethod
    def source_root(media, media_map):
        seen=set()
        while media.parent_id:
            if media.id in seen or media.parent_id not in media_map:raise AppError('SOURCE_LINEAGE','来源链缺失或循环。')
            seen.add(media.id);media=media_map[media.parent_id]
        return media.id

    @staticmethod
    def check_truth(frame,doc,labels,folder,*,detection=True):
        if not doc or doc.revision<1 or doc.source!='Human Generated':return '未保存人工真值'
        if doc.status=='REJECTED':return '历史审核拒绝，需人工处理'
        if AnnotationService.completion_state(frame,doc)!='LABELED':return '未处理、冲突或已剔除'
        objects=doc.payload.get('objects',[])
        if doc.payload.get('image_tag')=='ABNORMAL' and not objects and detection:return '整帧异常 / 无目标框'
        try:
            seen=set()
            for obj in objects:
                from uuid import UUID
                UUID(obj['id'])
                if obj['id'] in seen:return '目标UUID重复'
                seen.add(obj['id'])
                if obj.get('source','Human Generated')!='Human Generated':return '非人工目标不能自动准入'
                if obj['kind'] not in {'box','polygon'}:return 'ROI不是检测对象'
                validate_geometry(obj['kind'],obj['geometry'],frame.width,frame.height)
                if obj.get('label_id') not in labels or not labels[obj['label_id']].enabled:return '类别缺失或停用'
            if doc.payload.get('image_label_id') and doc.payload['image_label_id'] not in labels:return '整帧类别缺失'
            path=safe_path(folder,frame.path)
            if not path.is_file() or file_hash(path)!=frame.sha256:return '图片缺失或哈希不符'
            with Image.open(path) as im:
                if im.size!=(frame.width,frame.height):return '图片尺寸不符'
                im.verify()
        except (AppError,OSError,ValueError,KeyError,TypeError) as exc:return '数据校验失败：'+str(exc)
        return ''

    def screening(self,root=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as session:
            labels={r.id:r for r in session.scalars(select(LabelCategory))};cameras={r.id:r for r in session.scalars(select(Camera))};media_map={r.id:r for r in session.scalars(select(MediaAsset))}
            rows=session.execute(select(ExtractedFrame,Annotation).outerjoin(Annotation,Annotation.frame_id==ExtractedFrame.id)).all();result=[]
            for frame,doc in rows:
                media=media_map[frame.media_id];objects=doc.payload.get('objects',[]) if doc else [];counts=Counter(o.get('label_id') for o in objects)
                issue=self.check_truth(frame,doc,labels,folder);camera=cameras.get(media.camera_id)
                if media.camera_id and not camera:issue='摄像头关联缺失'
                try:source=self.source_root(media,media_map)
                except AppError as exc:source=None;issue=exc.message
                tag=doc.payload.get('image_tag','UNKNOWN') if doc else 'UNKNOWN';faults=set(counts)|({doc.payload.get('image_label_id')} if doc else set())
                result.append(dict(row_dict(frame),**frame_times(row_dict(frame),row_dict(media),{k:row_dict(v) for k,v in media_map.items()}),camera_id=media.camera_id,camera_name=camera.name if camera else '未关联摄像头',media_name=media.name,source_path=media.original_path,source_group_id=source,image_tag=tag,objects=len(objects),fault_ids=sorted(f for f in faults if f),fault_text='、'.join((labels[k].name if k in labels else '缺失类别')+' ×'+str(v) for k,v in counts.items()) if objects else ('整帧异常 / 无目标框' if tag=='ABNORMAL' else '正常' if tag=='NORMAL' else '未知'),completion_state=AnnotationService.completion_state(frame,doc),review_status=doc.status if doc else 'DRAFT',eligible=not issue,issue=issue,excluded=bool(frame.handling.get('is_excluded')),annotation_revision=doc.revision if doc else 0))
            return result

    def split_preview(self,frame_ids,root=None,*,strategy='source',ratios=None,seed=123,allow_leakage=False,admission='experimental',preset=None,pipeline_fallback=False,fault_ids=None):
        if preset in PRESETS:ratios=PRESETS[preset];strategy='source'
        requested_strategy=strategy
        ratios=[70,20,10] if ratios is None else ratios
        if strategy not in {'source','camera','random','grouped'}:raise AppError('SPLIT_STRATEGY','划分策略无效。')
        if len(ratios)!=3 or any(type(v) not in {int,float} or v<0 for v in ratios) or sum(ratios)!=100:raise AppError('SPLIT_RATIOS','Train/Val/Test比例必须非负且合计100。')
        if strategy=='random' and not allow_leakage:raise AppError('LEAKAGE_CONSENT','随机划分有相邻帧泄漏风险，必须明确确认。')
        preview=self.preview(frame_ids,root,admission=admission);samples=preview['samples'];warnings=list(preview['warnings']);issues=list(preview['issues'])
        if fault_ids is not None:
            with self.store.open(root) as (_,db,_),db.transaction() as session:
                declared=[session.get(LabelCategory,f) for f in sorted(set(fault_ids))]
                if not declared or any(not c or not c.enabled for c in declared):issues.append('数据集声明的目标类别缺失或停用')
                else:preview['classes']=[{'uuid':c.id,'class_id':i,'name':c.name,'revision':c.revision,'enabled':c.enabled} for i,c in enumerate(declared)]
            if any(o['label_id'] not in fault_ids for s in samples for o in s['annotation']['objects']):issues.append('检测目标超出数据集声明故障类型')
        if preset=='small' and pipeline_fallback and allow_leakage and len({s['source_group_id'] for s in samples})<sum(r>0 for r in ratios):strategy='random';warnings.append('LIMITED：用户明确允许来源不足的隔离工程图片划分，连续帧存在泄漏风险。')
        def key(s):return s['frame_id'] if strategy=='random' else (s.get('source_group_id') or s['media_id']) if strategy=='source' else (s.get('camera_id') or ('unlinked:'+s.get('source_group_id',s['media_id']))) if strategy=='camera' else (s['camera'] or s.get('source_group_id',s['media_id']))
        groups=sorted({key(s) for s in samples});random.Random(int(seed)).shuffle(groups)
        n=len(groups);nt=min(n,max(1,round(n*ratios[0]/100))) if ratios[0] else 0;nv=min(n-nt,round(n*ratios[1]/100))
        assignment={g:'train' if i<nt else 'val' if i<nt+nv else 'test' for i,g in enumerate(groups)}
        active=[x for x,r in zip(['train','val','test'],ratios) if r>0]
        if n>=len(active):
            for i,split in enumerate(active):
                if split not in assignment.values():
                    counts=Counter(assignment.values());g=next(g for g in reversed(groups) if counts[assignment[g]]>1);assignment[g]=split
        if preset:assignment=assign_groups(samples,key,ratios,int(seed))
        for s in samples:s['split']=assignment[key(s)]
        counts={x:sum(s['split']==x for s in samples) for x in ['train','val','test']}
        limited=False
        if any(not counts[x] for x in active):limited=True;warnings.append('LIMITED：独立来源分组不足，部分集合为空，不能评价工业泛化。')
        if strategy=='camera' and any(not s.get('camera_id') for s in samples):limited=True;warnings.append('LIMITED：含未关联摄像头，暂以原视频来源分组，不能用于未见摄像头评估。')
        cross_sources={s['source_group_id'] for s in samples if len({b['split'] for b in samples if b['source_group_id']==s['source_group_id']})>1}
        if cross_sources:limited=True;warnings.append('LIMITED：同一原视频跨集合，仅用于工程管线测试。')
        near_cross=any(a['split']!=b['split'] and (int(a['perceptual_hash'],16)^int(b['perceptual_hash'],16)).bit_count()<=4 for i,a in enumerate(samples) for b in samples[:i])
        if near_cross:limited=True;warnings.append('LIMITED：跨集合存在高相似度画面，不能宣称独立工业验证。')
        if strategy=='random':limited=True;warnings.append('LIMITED：随机图片划分仅作工程管线测试，不可用于工业泛化结论。')
        statistics=split_statistics(samples,ratios)
        if preset:
            if not ratios[2]:limited=True;warnings.append('LIMITED：没有独立Test集，不生成最终泛化评估结论。')
            for name,stats in statistics.items():
                if stats['images'] and any(not stats['classes'].get(c['uuid'],0) for c in preview['classes']):limited=True;warnings.append('LIMITED：'+name+'缺少部分目标类别样本。')
        return dict(preview,preset=preset,statistics=statistics,effective_strategy=strategy,requested_strategy=requested_strategy,samples=samples,issues=issues,warnings=sorted(set(warnings)),split_counts=counts,expected_counts={x:len(samples)*r/100 for x,r in zip(['train','val','test'],ratios)},split_status='BLOCKED' if issues else 'LIMITED' if limited else 'PASS',source_groups=len({s['source_group_id'] for s in samples}),split_groups=n,cross_source_groups=len(cross_sources),near_duplicate_cross_split=near_cross)

    def candidates(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(ExtractedFrame,Annotation).join(Annotation,Annotation.frame_id==ExtractedFrame.id).where(Annotation.status.in_(['REVIEWED','APPROVED']))).all()
            return [dict(row_dict(frame),review_status=doc.status,image_tag=doc.payload['image_tag'],objects=len(doc.payload['objects']),types=sorted({o['kind'] for o in doc.payload['objects']}),annotation_revision=doc.revision) for frame,doc in rows if AnnotationService.completion_state(frame,doc)=='LABELED' and not frame.handling.get('review_stale')]

    def versions(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(DatasetVersion,Dataset.name).join(Dataset)).all()
            return [dict(row_dict(version),name=name) for version,name in rows]

    def preview(self,frame_ids,root=None,*,admission='reviewed'):
        if admission not in {'reviewed','experimental'}:raise AppError('ADMISSION','数据准入政策无效。')
        with self.store.open(root) as (folder,db,_),db.transaction() as session:
            samples=[];seen=set();warnings=[];issues=[];classes=set();revisions={}
            labels={r.id:r for r in session.scalars(select(LabelCategory))};media_map={r.id:r for r in session.scalars(select(MediaAsset))}
            for frame_id in dict.fromkeys(frame_ids):
                frame=session.get(ExtractedFrame,frame_id);doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
                if not frame or not doc or (admission=='reviewed' and doc.status not in {'REVIEWED','APPROVED'}):issues.append('图片不存在或未人工审核：'+frame_id);continue
                if admission=='experimental':
                    issue=self.check_truth(frame,doc,labels,folder)
                    if issue:issues.append(issue+'：'+frame_id);continue
                state=AnnotationService.processing_state(frame,doc)
                if (admission=='reviewed' and frame.handling.get('review_stale')) or AnnotationService.completion_state(frame,doc)!='LABELED':issues.append('标注未完成或内容已修改，需独立人工审核：'+frame_id);continue
                if state not in {'NORMAL','ABNORMAL'}:issues.append('图片未处理、待复核、剔除或存在冲突：'+frame_id);continue
                path=safe_path(folder,frame.path)
                if not path.is_file() or file_hash(path)!=frame.sha256:issues.append('图片缺失/哈希不符：'+frame_id);continue
                if frame.sha256 in seen:warnings.append('同SHA256重复图片已去重：'+frame_id);continue
                seen.add(frame.sha256);media=session.get(MediaAsset,frame.media_id)
                if media.camera_id and not session.get(Camera,media.camera_id):issues.append('摄像头关联缺失：'+frame_id);continue
                payload=copy.deepcopy(doc.payload)
                try:
                    for obj in payload['objects']:
                        validate_geometry(obj['kind'],obj['geometry'],frame.width,frame.height)
                        if not session.get(LabelCategory,obj['label_id']):raise AppError('CLASS_MAP','类别不存在。')
                        classes.add(obj['label_id'])
                except AppError as exc:issues.append(exc.message+' '+frame_id);continue
                if not payload['objects'] and payload['image_tag']=='ABNORMAL':warnings.append('异常图片没有目标标注，仅适合原生标签任务：'+frame_id)
                if not payload['objects'] and payload['image_tag']=='UNKNOWN':warnings.append('未知图片不会作为正常负样本：'+frame_id)
                samples.append({'frame_id':frame.id,'media_id':frame.media_id,'camera':media.camera_id or media.camera,'camera_id':media.camera_id,'source_group_id':self.source_root(media,media_map),'validation_level':'AUTO_CHECKED_HUMAN' if admission=='experimental' else 'INDEPENDENT_REVIEW','sha256':frame.sha256,'perceptual_hash':frame.perceptual_hash,'source_image':frame.path,'width':frame.width,'height':frame.height,'pts_us':frame.pts_us,'time_us':frame.time_us,'parameters':frame.parameters,'method':frame.method,'annotation':payload,'annotation_revision':doc.revision,'handling_revision':frame.handling.get('revision',0),'annotation_status':doc.status,'annotation_source':doc.source,'timing':frame_times(row_dict(frame),row_dict(media),{k:row_dict(v) for k,v in media_map.items()}),'media_lifecycle':copy.deepcopy(media.lifecycle),'media_parent_id':media.parent_id})
                revisions[frame.id]=doc.revision
            for i,a in enumerate(samples):
                if any((int(a['perceptual_hash'],16)^int(b['perceptual_hash'],16)).bit_count()<=4 for b in samples[:i]):
                    warnings.append('存在近重复画面；仅警告，不自动删除潜在关键异常。');break
            label_rows=[session.get(LabelCategory,label_id) for label_id in sorted(classes)]
            if not label_rows and samples:label_rows=list(session.scalars(select(LabelCategory).where(LabelCategory.enabled==1).order_by(LabelCategory.id)))
            mapping=[{'uuid':r.id,'class_id':index,'name':r.name,'revision':r.revision,'enabled':r.enabled} for index,r in enumerate(label_rows)]
            if not samples:issues.append('没有可冻结的已审核图片。')
            return {'samples':samples,'classes':mapping,'issues':issues,'warnings':sorted(set(warnings)),'revisions':revisions,'count':len(samples),'objects':sum(len(s['annotation']['objects']) for s in samples),'groups':len({s['camera'] or s.get('source_group_id',s['media_id']) for s in samples})}

    def freeze(self,context,payload):
        if 'draft_revision' in payload:payload=self.lifecycle_freeze_payload(payload)
        elif payload.get('dataset_id'):
            record=self.load_dataset(payload['dataset_id'],payload['root'])
            if record and record['details'].get('draft'):raise AppError('DRAFT_VALIDATION','持久化草稿必须按保存修订检查并冻结。')
        root=payload['root'];name=payload.get('name','').strip();strategy=payload.get('strategy','grouped')
        if not name or len(name)>120:raise AppError('DATASET_NAME','数据集名称不能为空且不超过120个字符。')
        if strategy not in {'grouped','random','source','camera'}:raise AppError('SPLIT_STRATEGY','划分策略无效。')
        if strategy=='random' and not payload.get('allow_leakage'):raise AppError('LEAKAGE_CONSENT','随机划分有相邻帧泄漏风险，必须明确确认。')
        ratios=payload.get('ratios',[70,20,10])
        if len(ratios)!=3 or any(v<0 for v in ratios) or sum(ratios)!=100:raise AppError('SPLIT_RATIOS','Train/Val/Test比例必须非负且合计100。')
        admission=payload.get('admission','reviewed')
        split=self.split_preview(payload['frame_ids'],root,strategy=strategy,ratios=ratios,seed=payload.get('seed',123),allow_leakage=payload.get('allow_leakage',False),admission=admission,preset=payload.get('preset'),pipeline_fallback=payload.get('pipeline_fallback',False),fault_ids=payload.get('fault_ids'))
        if split['issues']:raise AppError('DATASET_INVALID','冻结检查失败：'+'；'.join(split['issues'][:4]))
        if admission=='experimental' and split['split_status']=='LIMITED' and not payload.get('allow_limited'):raise AppError('SPLIT_LIMITED','来源不足或泄漏风险：仅明确同意工程管线测试后可冻结LIMITED实验版本。')
        strategy=split['effective_strategy'];ratios=list(PRESETS.get(payload.get('preset'),ratios))
        samples=split['samples'];warnings=split['warnings'];seed=int(payload.get('seed',123));splits=split['split_counts'];preview=split
        camera_ids=sorted({s['camera_id'] or '__unlinked__' for s in samples})
        if admission=='experimental' and len(camera_ids)>1 and not payload.get('allow_multi_camera'):raise AppError('MULTI_CAMERA_CONSENT','包含多个摄像头/未关联来源，必须明确同意共享数据集。')
        with self.store.open(root) as (folder,db,project_id):
            with db.transaction() as session:
                dataset=session.get(Dataset,payload['dataset_id']) if payload.get('dataset_id') else None
                if payload.get('dataset_id') and not dataset:raise AppError('DATASET_MISSING','原数据集不存在。')
                dataset_id=dataset.id if dataset else str(uuid4())
                number=(session.scalar(select(func.max(DatasetVersion.number)).where(DatasetVersion.dataset_id==dataset_id)) or 0)+1
                rois=[row_dict(r) for r in session.scalars(select(RegionOfInterest))]
                clips=[row_dict(r) for r in session.scalars(select(VideoClipLabel))]
                media_ids={s['media_id'] for s in samples};media=[row_dict(r) for r in session.scalars(select(MediaAsset).where(MediaAsset.id.in_(media_ids)))]
                label_library=[row_dict(r) for r in session.scalars(select(LabelCategory))]
            version_id=str(uuid4());base=folder/'datasets'/dataset_id;base.mkdir(parents=True,exist_ok=True)
            final=base/f'v{number:04d}';stage=base/f'.{version_id}.partial';stage.mkdir();(stage/'images').mkdir()
            snapshot={'format':'ivad-dataset','format_version':1,'project_id':project_id,'dataset_id':dataset_id,'version_id':version_id,'version':number,'name':name,'created_at':utc_now(),'dataset_scope':payload.get('dataset_scope'),'draft_revision':payload.get('draft_revision'),'draft_validation_signature':payload.get('draft_signature'),'preset':payload.get('preset'),'statistics':split['statistics'],'strategy':strategy,'ratios':ratios,'seed':seed,'classes':preview['classes'],'label_library':label_library,'samples':samples,'rois':rois,'clip_labels':clips,'media':media,'warnings':sorted(set(warnings))}
            if admission=='experimental':snapshot['admission']={'policy':'human-auto-v1','scope':'EXPERIMENT_ONLY','validation_level':'AUTO_CHECKED_HUMAN','independent_review':False,'split_status':split['split_status'],'allow_limited':bool(payload.get('allow_limited')),'validation_mode':payload.get('validation_mode','legacy'),'risk_ack':payload.get('risk_ack'),'allow_multi_camera':bool(payload.get('allow_multi_camera')),'camera_ids':camera_ids,'source_groups':split['source_groups'],'expected_counts':split['expected_counts'],'actual_counts':splits,'near_duplicate_cross_split':split['near_duplicate_cross_split']}
            for index,s in enumerate(samples):
                context.check();source=safe_path(folder,s['source_image']);filename=s['frame_id']+source.suffix
                shutil.copyfile(source,stage/'images'/filename)
                if file_hash(stage/'images'/filename,context.check)!=s['sha256']:raise AppError('IMAGE_CHANGED','图片在冻结期间发生变化，未提交版本。')
                s['image']='images/'+filename;context.progress((index+1)*90/len(samples))
            atomic_json(stage/'manifest.json',snapshot);checksum=file_hash(stage/'manifest.json');context.check()
            renamed=False
            try:
              with db.transaction(camera_write=True) as session:
                if 'draft_revision' in payload:
                    live_dataset=session.get(Dataset,dataset_id)
                    if not live_dataset or live_dataset.revision!=payload['draft_revision'] or live_dataset.details['draft']['state']!='VALIDATED' or live_dataset.details['draft']['validation']['signature']!=payload['draft_signature']:raise AppError('DRAFT_CONFLICT','冻结期间草稿发生变化，未提交。')
                current_media={r.id:r for r in session.scalars(select(MediaAsset))}
                for c in preview['classes']:
                    live_label=session.get(LabelCategory,c['uuid'])
                    if not live_label or live_label.revision!=c['revision'] or live_label.enabled!=c['enabled']:raise AppError('SNAPSHOT_CONFLICT','类别库在冻结期间发生变化。')
                for s in samples:
                    doc=session.scalar(select(Annotation).where(Annotation.frame_id==s['frame_id']))
                    frame=session.get(ExtractedFrame,s['frame_id'])
                    live_media=session.get(MediaAsset,frame.media_id)
                    if self.source_root(live_media,current_media)!=s['source_group_id'] or live_media.camera_id!=s['camera_id'] or live_media.parent_id!=s['media_parent_id'] or live_media.lifecycle!=s['media_lifecycle']:raise AppError('SNAPSHOT_CONFLICT','摄像头或来源在冻结期间发生变化。')
                    if not doc or doc.revision!=s['annotation_revision'] or frame.handling.get('revision',0)!=s['handling_revision'] or AnnotationService.processing_state(frame,doc) not in {'NORMAL','ABNORMAL'}:raise AppError('SNAPSHOT_CONFLICT','标注或剔除状态在冻结期间发生变化，已阻止不一致版本。')
                if not dataset:session.add(Dataset(id=dataset_id,name=name,created_at=utc_now()));session.flush()
                if final.exists():raise AppError('VERSION_EXISTS','版本目录已存在，禁止覆盖；请进行一致性检查。')
                stage.rename(final)
                renamed=True
                summary={'state':'FROZEN','draft_revision':payload.get('draft_revision'),'statistics':split['statistics'],'admission':snapshot.get('admission',{'policy':'reviewed-legacy'}),'images':len(samples),'objects':preview['objects'],'splits':splits,'classes':preview['classes'],'warnings':snapshot['warnings']}
                session.add(DatasetVersion(id=version_id,dataset_id=dataset_id,number=number,path=(final/'manifest.json').relative_to(folder).as_posix(),sha256=checksum,summary=summary,created_at=utc_now()));session.flush()
                for s in samples:session.add(DatasetSample(id=str(uuid4()),version_id=version_id,frame_id=s['frame_id'],split=s['split'],sha256=s['sha256'],annotation=s['annotation']))
            except Exception:
                if renamed and final.exists():final.rename(stage)
                raise
            context.progress(100);context.log('数据集版本已冻结，原版本不可覆盖。')
            return {'version_id':version_id,'dataset_id':dataset_id,'number':number,**summary}

    def snapshot(self,version_id,root=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as session:
            version=session.get(DatasetVersion,version_id)
            if not version:raise AppError('VERSION_MISSING','冻结版本不存在。')
            path=safe_path(folder,version.path);checksum=version.sha256
        if not path.is_file() or file_hash(path)!=checksum:raise AppError('VERSION_CHANGED','冻结版本清单缺失或被修改，禁止导出。')
        snapshot=json.loads(path.read_text(encoding='utf-8'))
        return path.parent,snapshot

    def check_version(self,version_id,root=None):
        folder,snapshot=self.snapshot(version_id,root);issues=[];seen=set();classes={c['uuid'] for c in snapshot['classes']}
        for sample in snapshot['samples']:
            try:
                path=safe_path(folder,sample['image'])
                if not path.is_file() or file_hash(path)!=sample['sha256']:raise AppError('VERSION_IMAGE','冻结图片缺失或哈希变化。')
                with Image.open(path) as im:
                    if im.size!=(sample['width'],sample['height']):raise AppError('VERSION_SIZE','冻结图片尺寸不符。')
                    im.verify()
                if sample['sha256'] in seen:raise AppError('VERSION_DUPLICATE','冻结版本存在重复图片。')
                seen.add(sample['sha256'])
                for obj in sample['annotation']['objects']:
                    if obj.get('label_id') not in classes:raise AppError('VERSION_CLASS','冻结类别映射不符。')
                    validate_geometry(obj['kind'],obj['geometry'],sample['width'],sample['height'])
            except (AppError,OSError,ValueError,KeyError) as exc:issues.append(sample['frame_id']+'：'+str(exc))
        return {'status':'BLOCKED' if issues else 'PASS','version_id':version_id,'images':len(snapshot['samples']),'classes':snapshot['classes'],'admission':snapshot.get('admission',{'policy':'reviewed-legacy'}),'issues':issues,'warnings':snapshot.get('warnings',[]),'source_trace':[dict(frame_id=s['frame_id'],media_id=s['media_id'],source_group_id=s.get('source_group_id'),camera_id=s.get('camera_id'),pts_us=s['pts_us'],annotation_revision=s['annotation_revision']) for s in snapshot['samples']]}

    def export(self,context,payload):
        root=payload['root'];version_id=payload['version_id'];format_name=payload['format'];parent=Path(payload['parent']).resolve()
        if not parent.is_dir():raise AppError('EXPORT_PATH','请选择可写的已有导出父目录。')
        source,snapshot=self.snapshot(version_id,root);export_id=str(uuid4())
        if shutil.disk_usage(parent).free<sum(safe_path(source,s['image']).stat().st_size for s in snapshot['samples'])+1024*1024:raise AppError('DISK_SPACE','导出磁盘空间不足。')
        stage=parent/f'.ivad-export-{export_id}.partial';final=parent/f"IVAD-{snapshot['dataset_id']}-v{snapshot['version']:04d}-{format_name}-{export_id[:8]}"
        stage.mkdir();warnings=export_snapshot(snapshot,source,stage,format_name,context.check);context.check()
        checksum=file_hash(stage/'export_manifest.json');stage.rename(final)
        try:
            with self.store.open(root) as (_,db,_),db.transaction() as session:
                session.add(ExportRecord(id=export_id,version_id=version_id,format=format_name,path=str(final),sha256=checksum,created_at=utc_now()))
        except Exception:
            final.rename(stage)
            raise
        context.progress(100);context.log('导出格式与文件校验通过，目标目录已提交。')
        return {'path':str(final),'format':format_name,'warnings':warnings,'manifest_sha256':checksum}
