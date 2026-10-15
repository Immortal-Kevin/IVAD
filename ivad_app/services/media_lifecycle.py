"""Dependency-aware reversible removal; no cascade or external source deletion."""
import copy,hashlib,json
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError,utc_now
from ivad_app.storage.models import MediaAsset,ExtractedFrame,Annotation,AnnotationRevision,DatasetSample,TrainingRun,ModelVersion,RegionOfInterest,VideoClipLabel,JobRecord
from ivad_app.storage.project_store import safe_path,file_hash

class MediaLifecycle:
    def _dependencies(self,s,mid,folder):
        media=s.get(MediaAsset,mid)
        if not media:raise AppError('MEDIA_MISSING','媒体记录不存在。')
        children=list(s.scalars(select(MediaAsset).where(MediaAsset.parent_id==mid)));mids={mid,*[r.id for r in children]}
        frames=list(s.scalars(select(ExtractedFrame).where(ExtractedFrame.media_id.in_(mids))));fids={f.id for f in frames}
        docs=list(s.scalars(select(Annotation).where(Annotation.frame_id.in_(fids)))) if fids else []
        versions={r.version_id for r in s.scalars(select(DatasetSample).where(DatasetSample.frame_id.in_(fids)))} if fids else set()
        runs=[r for r in s.scalars(select(TrainingRun)) if r.details.get('version_id') in versions];rids={r.id for r in runs}
        models=[r for r in s.scalars(select(ModelVersion)) if r.details.get('dataset_version') in versions or r.details.get('run_id') in rids or any(v.get('dataset_version') in versions for v in r.details.get('validations',[]))]
        rois=list(s.scalars(select(RegionOfInterest).where(RegionOfInterest.media_id.in_(mids))))
        labels=list(s.scalars(select(VideoClipLabel).where(VideoClipLabel.media_id.in_(mids))))
        revisions=list(s.scalars(select(AnnotationRevision).where(AnnotationRevision.annotation_id.in_([r.id for r in docs])))) if docs else []
        with self.logs.db.transaction() as catalog:
            jobs=[j for j in catalog.scalars(select(JobRecord).where(JobRecord.state.in_(['QUEUED','RUNNING']))) if j.payload.get('root')==str(folder) and (j.payload.get('media_id') in mids or j.payload.get('version_id') in versions or j.kind=='p2_import')]
        counts=dict(clips=len(children),frames=len(frames),annotations=len(docs),annotation_revisions=len(revisions),dataset_versions=len(versions),training_runs=len(runs),model_versions=len(models),rois=len(rois),clip_labels=len(labels),active_jobs=len(jobs))
        signature=hashlib.sha256(json.dumps(dict(counts=counts,frames=sorted(fids),versions=sorted(versions),camera_id=media.camera_id,lifecycle=media.lifecycle,state=media.state),sort_keys=True).encode()).hexdigest()
        return dict(media_id=mid,name=media.name,mode=media.mode,counts=counts,has_dependencies=any(counts.values()),signature=signature,camera_id=media.camera_id)
    def dependencies(self,media_id,root=None):
        with self.store.open(root) as (folder,db,_),db.transaction() as s:return self._dependencies(s,media_id,folder)
    def remove(self,media_id,root=None,*,hide_only=False,cleanup_copy=False,expected_signature=None,restore=False):
        staged=None;original=None;committed=False
        with self.store.open(root) as (folder,db,_):
            try:
                with db.transaction() as s:
                    preview=self._dependencies(s,media_id,folder);row=s.get(MediaAsset,media_id)
                    if expected_signature and expected_signature!=preview['signature']:raise AppError('MEDIA_CHANGED','依赖或配置已改变，请重新查看影响范围。')
                    if not restore and not hide_only and preview['has_dependencies']:raise AppError('MEDIA_REFERENCED','存在下游引用，只允许隐藏/停用，禁止危险移除。')
                    if cleanup_copy and (hide_only or restore or preview['has_dependencies'] or row.mode!='COPY'):raise AppError('MEDIA_CLEANUP','仅无依赖的COPY视频可明确选择清理项目副本；REFERENCE原文件绝不删除。')
                    life=copy.deepcopy(row.lifecycle);history=list(life.get('history',[]));history.append({'action':'RESTORE' if restore else 'HIDE' if hide_only else 'REMOVE','at':utc_now(),'by':'local_operator','previous':{k:v for k,v in life.items() if k!='history'},'counts':preview['counts']})
                    if restore and life.get('copy_cleanup') in {'DELETED','QUARANTINED'}:raise AppError('MEDIA_COPY_REMOVED','项目副本已清理或隔离；请先恢复实际文件，不能标为可用。')
                    life.update(hidden=not restore,removed=not restore and not hide_only,history=history,revision=life.get('revision',0)+1)
                    if cleanup_copy:
                        original=safe_path(folder,row.path)
                        if not original.is_relative_to((folder/'media').resolve()) or original==Path(row.original_path).resolve() or not original.is_file() or file_hash(original)!=row.sha256:raise AppError('MEDIA_CLEANUP','副本路径或哈希不符，禁止清理。')
                        staged=original.with_name(original.name+'.removed-'+uuid4().hex);original.rename(staged);life.update(copy_cleanup='QUARANTINED',cleanup_path=staged.relative_to(folder).as_posix())
                    row.lifecycle=life
                committed=True
            finally:
                if not committed and staged and staged.exists():staged.rename(original)
            if staged:
                try:
                    staged.unlink()
                    with db.transaction() as s:
                        row=s.get(MediaAsset,media_id);life=copy.deepcopy(row.lifecycle);life['copy_cleanup']='DELETED';row.lifecycle=life
                except OSError:return dict(preview,cleanup_pending=True)
        self.logs.write('media','媒体已恢复列表。' if restore else '媒体隐藏/移除已记录；来源与历史引用保留。')
        return dict(preview,cleanup_pending=False)
