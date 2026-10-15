import copy,json,sqlite3
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select
from ivad_app.core.contracts import AppError
from ivad_app.storage.models import Annotation,MediaAsset,ExtractedFrame,TrainingRun,ModelVersion
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click

def test_completion_and_review_are_independent(services,media_project):
    p,_,ids=media_project;s=services.annotations
    assert s.load(ids[0])['completion_state']=='UNLABELED'
    s.save(ids[0],{'image_tag':'NORMAL','objects':[]},None,0,completion_state='LABELED')
    assert s.load(ids[0])['status']=='DRAFT' and s.load(ids[0])['completion_state']=='LABELED'
    assert not services.datasets.candidates()
    s.review_frames({ids[0]:1},'REVIEWED');assert len(services.datasets.candidates())==1
    loaded=s.load(ids[0]);s.save(ids[0],dict(loaded['payload'],image_tag='ABNORMAL',image_label_id=s.labels()[0]['id']),None,loaded['revision'])
    assert s.load(ids[0])['status']=='REVIEWED' and s.frames_status()[ids[0]]['review_stale']
    assert not services.datasets.candidates()
    s.review_frames({ids[0]:3},'REVIEWED');assert len(services.datasets.candidates())==1
    for i,status in enumerate(['DRAFT','REVIEWED','APPROVED','REJECTED'],1):
        s.save(ids[i],{'image_tag':'UNKNOWN','objects':[]},status,0)
        assert s.load(ids[i])['completion_state']=='UNLABELED'
    with pytest.raises(AppError):s.review_frames({ids[1]:1},'APPROVED')
    assert len(s.revisions(ids[0]))==4

def test_camera_uuid_project_details_and_explicit_clip_protection(services,media_project):
    p,mids,_=media_project;s=services.cameras
    a=s.save('1204-1202给煤机摄像头',root=p.root,details={'code':'1204-1202','location':'测试位置','equipment':'TEST FIXTURE','enabled':True});b=s.save('另一个机位',root=p.root)
    s.associate(mids[0],a['id'],None,p.root)
    clip=services.media.save_video_clip(Context(),{'root':p.root,'media_id':mids[0],'start_us':0,'end_us':500000})['media_id']
    assert services.media.get(clip)['camera_id']==a['id']
    s.associate(clip,b['id'],a['id'],p.root);result=s.associate(mids[0],b['id'],a['id'],p.root)
    assert result['preserved_explicit_clips']==[clip]
    s.associate(mids[0],a['id'],b['id'],p.root);assert services.media.get(clip)['camera_id']==b['id']
    renamed=s.save('显示名称更新',a['id'],a['revision'],p.root,details=dict(a['details'],enabled=False));assert renamed['id']==a['id']
    assert a['id'] not in {r['id'] for r in s.list(p.root,available_only=True)}
    assert services.media.get(mids[0])['camera_id']==a['id']
    with pytest.raises(AppError):s.associate(mids[1],a['id'],None,p.root)

@pytest.mark.parametrize('mode,cleanup',[('COPY',False),('COPY',True),('REFERENCE',False)])
def test_safe_remove_without_dependencies(services,tmp_path,sample_videos,mode,cleanup):
    p=services.projects.create(str(tmp_path),'安全移除');source=sample_videos/'sample.mp4';before=source.read_bytes()
    mid=services.media.import_batch(Context(),{'root':p.root,'paths':[str(source)],'mode':mode})['imported'][0];row=services.media.get(mid);copy_path=Path(row['accessible_path'])
    preview=services.media.dependencies(mid);assert not preview['has_dependencies']
    services.media.remove(mid,cleanup_copy=cleanup,expected_signature=preview['signature'])
    assert services.media.list()==[] and services.media.list(include_inactive=True)[0]['state']=='REMOVED'
    assert source.read_bytes()==before
    if cleanup:
        assert not copy_path.exists()
        with pytest.raises(AppError):services.media.remove(mid,restore=True)
        assert len(services.media.import_batch(Context(),{'root':p.root,'paths':[str(source)],'mode':mode})['imported'])==1
    else:
        assert copy_path.exists();services.media.remove(mid,restore=True);assert services.media.get(mid)['sha256']==row['sha256']

def test_dependency_guard_keeps_frozen_training_models(services,media_project,tmp_path):
    from tests.test_p3_training import freeze_valid
    p,vid=freeze_valid(services,media_project);mid=media_project[1][0]
    with services.store.open(p.root) as (_,db,_),db.transaction() as s:
        s.add(TrainingRun(id='software-fixture-run',details={'version_id':vid,'state':'SUCCEEDED'},revision=1));s.add(ModelVersion(id='software-fixture-model',details={'dataset_version':vid,'state':'EXPERIMENTAL'},revision=1))
    folder,snap=services.datasets.snapshot(vid);before=(folder/'manifest.json').read_bytes();preview=services.media.dependencies(mid)
    assert preview['counts']['frames'] and preview['counts']['dataset_versions']==1 and preview['counts']['training_runs']==1 and preview['counts']['model_versions']==1
    with pytest.raises(AppError):services.media.remove(mid,cleanup_copy=True)
    services.media.remove(mid,hide_only=True,expected_signature=preview['signature']);assert mid not in {r['id'] for r in services.media.list()}
    assert (folder/'manifest.json').read_bytes()==before;services.training.preflight(vid,p.root)
    services.media.remove(mid,restore=True);assert services.media.get(mid)['state']=='READY'

def test_reference_cannot_delete_external_and_stale_preview_rejected(services,tmp_path,sample_videos):
    p=services.projects.create(str(tmp_path),'REFERENCE');mid=services.media.import_batch(Context(),{'root':p.root,'paths':[str(sample_videos/'sample.mp4')],'mode':'REFERENCE'})['imported'][0]
    before=services.media.dependencies(mid)
    with pytest.raises(AppError):services.media.remove(mid,cleanup_copy=True)
    services.media.extract(Context(),{'root':p.root,'media_id':mid,'options':{'mode':'fixed','start_us':0,'end_us':500000,'interval_us':200000,'maximum':2,'format':'PNG'}})
    with pytest.raises(AppError):services.media.remove(mid,hide_only=True,expected_signature=before['signature'])

def test_schema0006_camera_details_preserve_old_uuid_history(tmp_path):
    from ivad_app.storage.database import Database
    path=tmp_path/'legacy.sqlite';db=Database(path,create=True,revision='0006');db.close();cid=str(uuid4());history='[{"action":"CREATE","source":"TEST FIXTURE"}]'
    with sqlite3.connect(path) as db:
        db.execute('INSERT INTO cameras(id,name,legacy_key,revision,history) VALUES(?,?,?,?,?)',(cid,'旧摄像头','旧编号',3,history));before=db.execute('select * from cameras').fetchone()
    db=Database(path);assert db.integrity_check()=='ok';db.close()
    with sqlite3.connect(path) as db:
        after=db.execute('select * from cameras').fetchone();assert after[:len(before)]==before and after[-1]=='{}'
    backup=next(tmp_path.glob('*.backup'))
    with sqlite3.connect(backup) as db:assert db.execute('select * from cameras').fetchone()==before
