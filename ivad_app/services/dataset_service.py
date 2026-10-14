import copy, json, random, shutil
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select, func
from ivad_app.core.contracts import AppError, utc_now
from ivad_app.storage.models import (Dataset, DatasetVersion, DatasetSample, ExportRecord, ExtractedFrame,
    Annotation, LabelCategory, MediaAsset, RegionOfInterest, VideoClipLabel)
from ivad_app.storage.project_store import file_hash, atomic_json, safe_path, row_dict
from ivad_app.annotations.geometry import validate_geometry
from ivad_app.datasets.exporters import export_snapshot
from ivad_app.services.annotation_service import AnnotationService

class DatasetService:
    def __init__(self,store,logs):self.store,self.logs=store,logs

    def candidates(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(ExtractedFrame,Annotation).join(Annotation,Annotation.frame_id==ExtractedFrame.id).where(Annotation.status.in_(['REVIEWED','APPROVED']))).all()
            return [dict(row_dict(frame),review_status=doc.status,image_tag=doc.payload['image_tag'],objects=len(doc.payload['objects']),types=sorted({o['kind'] for o in doc.payload['objects']}),annotation_revision=doc.revision) for frame,doc in rows if AnnotationService.processing_state(frame,doc) in {'NORMAL','ABNORMAL'}]

    def versions(self,root=None):
        with self.store.open(root) as (_,db,_),db.transaction() as session:
            rows=session.execute(select(DatasetVersion,Dataset.name).join(Dataset)).all()
            return [dict(row_dict(version),name=name) for version,name in rows]

    def preview(self,frame_ids,root=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as session:
            samples=[];seen=set();warnings=[];issues=[];classes=set();revisions={}
            for frame_id in dict.fromkeys(frame_ids):
                frame=session.get(ExtractedFrame,frame_id);doc=session.scalar(select(Annotation).where(Annotation.frame_id==frame_id))
                if not frame or not doc or doc.status not in {'REVIEWED','APPROVED'}:issues.append('图片不存在或未人工审核：'+frame_id);continue
                state=AnnotationService.processing_state(frame,doc)
                if state not in {'NORMAL','ABNORMAL'}:issues.append('图片未处理、待复核、剔除或存在冲突：'+frame_id);continue
                path=safe_path(folder,frame.path)
                if not path.is_file() or file_hash(path)!=frame.sha256:issues.append('图片缺失/哈希不符：'+frame_id);continue
                if frame.sha256 in seen:warnings.append('同SHA256重复图片已去重：'+frame_id);continue
                seen.add(frame.sha256);media=session.get(MediaAsset,frame.media_id)
                payload=copy.deepcopy(doc.payload)
                try:
                    for obj in payload['objects']:
                        validate_geometry(obj['kind'],obj['geometry'],frame.width,frame.height)
                        if not session.get(LabelCategory,obj['label_id']):raise AppError('CLASS_MAP','类别不存在。')
                        classes.add(obj['label_id'])
                except AppError as exc:issues.append(exc.message+' '+frame_id);continue
                if not payload['objects'] and payload['image_tag']=='ABNORMAL':warnings.append('异常图片没有目标标注，仅适合原生标签任务：'+frame_id)
                if not payload['objects'] and payload['image_tag']=='UNKNOWN':warnings.append('未知图片不会作为正常负样本：'+frame_id)
                samples.append({'frame_id':frame.id,'media_id':frame.media_id,'camera':media.camera_id or media.camera,'camera_id':media.camera_id,'source_group_id':media.parent_id or media.id,'sha256':frame.sha256,'perceptual_hash':frame.perceptual_hash,'source_image':frame.path,'width':frame.width,'height':frame.height,'pts_us':frame.pts_us,'time_us':frame.time_us,'parameters':frame.parameters,'method':frame.method,'annotation':payload,'annotation_revision':doc.revision,'handling_revision':frame.handling.get('revision',0),'annotation_status':doc.status,'annotation_source':doc.source})
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
        root=payload['root'];name=payload.get('name','').strip();strategy=payload.get('strategy','grouped')
        if not name or len(name)>120:raise AppError('DATASET_NAME','数据集名称不能为空且不超过120个字符。')
        if strategy not in {'grouped','random'}:raise AppError('SPLIT_STRATEGY','划分策略无效。')
        if strategy=='random' and not payload.get('allow_leakage'):raise AppError('LEAKAGE_CONSENT','随机划分有相邻帧泄漏风险，必须明确确认。')
        ratios=payload.get('ratios',[70,20,10])
        if len(ratios)!=3 or any(v<0 for v in ratios) or sum(ratios)!=100:raise AppError('SPLIT_RATIOS','Train/Val/Test比例必须非负且合计100。')
        preview=self.preview(payload['frame_ids'],root)
        if preview['issues']:raise AppError('DATASET_INVALID','冻结检查失败：'+'；'.join(preview['issues'][:4]))
        samples=preview['samples'];warnings=preview['warnings'];seed=int(payload.get('seed',123));rng=random.Random(seed)
        groups=sorted({(s['camera'] or s.get('source_group_id',s['media_id'])) if strategy=='grouped' else s['frame_id'] for s in samples});rng.shuffle(groups)
        count=len(groups);ntrain=max(1,round(count*ratios[0]/100)) if ratios[0]>0 else 0;ntrain=min(count,ntrain)
        nval=min(count-ntrain,round(count*ratios[1]/100));assignment={g:'train' if i<ntrain else 'val' if i<ntrain+nval else 'test' for i,g in enumerate(groups)}
        if count>=3 and all(r>0 for r in ratios):
            # 小组数时优先确保三份均非空，并仍然保持来源组不交叉。
            assignment[groups[0]]='train';assignment[groups[-2]]='val';assignment[groups[-1]]='test'
        for s in samples:s['split']=assignment[(s['camera'] or s.get('source_group_id',s['media_id'])) if strategy=='grouped' else s['frame_id']]
        if strategy=='random':warnings.append('用户选择随机划分；相邻帧/同录像数据泄漏风险仍存在。')
        splits={split:sum(s['split']==split for s in samples) for split in ['train','val','test']}
        if not splits['val'] or not splits['test']:warnings.append('独立来源组不足，验证/测试可能为空；工业训练前需增加独立来源。')
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
            snapshot={'format':'ivad-dataset','format_version':1,'project_id':project_id,'dataset_id':dataset_id,'version_id':version_id,'version':number,'name':name,'created_at':utc_now(),'strategy':strategy,'ratios':ratios,'seed':seed,'classes':preview['classes'],'label_library':label_library,'samples':samples,'rois':rois,'clip_labels':clips,'media':media,'warnings':sorted(set(warnings))}
            for index,s in enumerate(samples):
                context.check();source=safe_path(folder,s['source_image']);filename=s['frame_id']+source.suffix
                shutil.copyfile(source,stage/'images'/filename)
                if file_hash(stage/'images'/filename,context.check)!=s['sha256']:raise AppError('IMAGE_CHANGED','图片在冻结期间发生变化，未提交版本。')
                s['image']='images/'+filename;context.progress((index+1)*90/len(samples))
            atomic_json(stage/'manifest.json',snapshot);checksum=file_hash(stage/'manifest.json');context.check()
            renamed=False
            try:
              with db.transaction() as session:
                for s in samples:
                    doc=session.scalar(select(Annotation).where(Annotation.frame_id==s['frame_id']))
                    frame=session.get(ExtractedFrame,s['frame_id'])
                    if not doc or doc.revision!=s['annotation_revision'] or frame.handling.get('revision',0)!=s['handling_revision'] or AnnotationService.processing_state(frame,doc) not in {'NORMAL','ABNORMAL'}:raise AppError('SNAPSHOT_CONFLICT','标注或剔除状态在冻结期间发生变化，已阻止不一致版本。')
                if not dataset:session.add(Dataset(id=dataset_id,name=name,created_at=utc_now()));session.flush()
                if final.exists():raise AppError('VERSION_EXISTS','版本目录已存在，禁止覆盖；请进行一致性检查。')
                stage.rename(final)
                renamed=True
                summary={'images':len(samples),'objects':preview['objects'],'splits':splits,'classes':preview['classes'],'warnings':snapshot['warnings']}
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
