import json, shutil, sqlite3, time
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import text
from tests.test_p2_services import media_project
from tests.test_p2_media import Context, sample_videos
from ivad_app.core.contracts import AppError
from ivad_app.storage.database import Database
from ivad_app.storage.project_store import file_hash

def reviewed(services,ids,tag='ABNORMAL'):
    label=services.annotations.labels()[0]
    for frame in ids:
        services.annotations.save(frame,{'objects':[{'id':str(uuid4()),'kind':'polygon','label_id':label['id'],'geometry':[[5,5],[80,5],[80,60]]}],'image_tag':tag},'REVIEWED',0)

def test_p1_schema_upgrade_preserves_jobs_and_preferences(tmp_path):
    path=tmp_path/'legacy.sqlite';old=Database(path,create=True,revision='0002')
    with old.engine.begin() as conn:
        conn.execute(text("INSERT INTO projects (id,name,description,site,created_at,updated_at,revision) VALUES ('old','旧中文项目','','','now','now',3)"))
        conn.execute(text("INSERT INTO jobs (id,kind,project_id,state,progress,created_at,updated_at,error) VALUES ('job','diagnostic','old','SUCCEEDED',100,'now','now','')"))
    old.close();new=Database(path)
    with new.engine.connect() as conn:
        assert conn.execute(text('SELECT name,revision FROM projects')).one()==('旧中文项目',3)
        assert conn.execute(text('SELECT state,progress FROM jobs')).one()==('SUCCEEDED',100)
    assert new.integrity_check()=='ok';new.close()
    backup=next(tmp_path.glob('*.backup'))
    with sqlite3.connect(backup) as conn:assert conn.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0002'

def test_import_disk_failure_source_preserved(services,tmp_path,sample_videos,monkeypatch):
    p=services.projects.create(str(tmp_path),'磁盘不足');source=sample_videos/'sample.mp4';before=file_hash(source)
    monkeypatch.setattr('ivad_app.services.media_service.shutil.disk_usage',lambda _:shutil._ntuple_diskusage(100,100,0))
    with pytest.raises(AppError):services.media.import_batch(Context(),{'root':p.root,'paths':[str(source)],'mode':'COPY'})
    assert file_hash(source)==before and not list(Path(p.root).rglob('*.partial'))

def test_real_job_cancellation_keeps_committed_frames(services,media_project,monkeypatch):
    p,media_ids,ids=media_project;original=services.media._save_frame
    def slow(*a,**k):
        result=original(*a,**k);time.sleep(.035);return result
    monkeypatch.setattr(services.media,'_save_frame',slow)
    job=services.jobs.submit('p2_extract',p.id,{'root':p.root,'media_id':media_ids[0],'options':{'mode':'fixed','end_us':1100000,'interval_us':1000,'maximum':5000,'format':'PNG'}})
    deadline=time.monotonic()+5
    while services.jobs.get(job)['progress']==0 and time.monotonic()<deadline:time.sleep(.01)
    services.jobs.cancel(job)
    while services.jobs.get(job)['state'] not in {'CANCELLED','FAILED','SUCCEEDED'} and time.monotonic()<deadline:time.sleep(.01)
    assert services.jobs.get(job)['state']=='CANCELLED'
    assert services.media.check()['status']=='PASS'

def test_snapshot_new_version_and_tamper_block(services,media_project,tmp_path):
    p,_,ids=media_project;reviewed(services,ids[:2]);payload={'root':p.root,'name':'版本','frame_ids':ids[:2]}
    first=services.datasets.freeze(Context(),payload);folder,snap=services.datasets.snapshot(first['version_id']);old=(folder/'manifest.json').read_bytes()
    doc=services.annotations.load(ids[0]);services.annotations.save(ids[0],doc['payload'],'APPROVED',doc['revision'])
    second=services.datasets.freeze(Context(),dict(payload,dataset_id=first['dataset_id']))
    assert second['number']==2 and (folder/'manifest.json').read_bytes()==old
    (folder/snap['samples'][0]['image']).write_bytes(b'controlled damaged snapshot image')
    with pytest.raises(AppError):services.datasets.export(Context(),{'root':p.root,'version_id':first['version_id'],'format':'coco','parent':str(tmp_path)})
    assert services.media.check()['status']=='WARNING'

def test_split_grouping_and_random_consent(services,media_project):
    p,_,ids=media_project;reviewed(services,ids)
    payload={'root':p.root,'name':'分组','frame_ids':ids}
    result=services.datasets.freeze(Context(),payload);_,snap=services.datasets.snapshot(result['version_id'])
    assert all(len({s['split'] for s in snap['samples'] if s['media_id']==mid})==1 for mid in {s['media_id'] for s in snap['samples']})
    assert len({s['sha256'] for s in snap['samples']})==len(snap['samples'])
    with pytest.raises(AppError):services.datasets.freeze(Context(),dict(payload,strategy='random'))
    random=services.datasets.freeze(Context(),dict(payload,strategy='random',allow_leakage=True))
    assert any('随机' in w for w in random['warnings'])

@pytest.mark.parametrize('tag',['UNKNOWN','ABNORMAL'])
def test_unlabeled_not_silent_yolo_negative(services,media_project,tmp_path,tag):
    p,_,ids=media_project;reviewed(services,[ids[0]])
    services.annotations.save(ids[1],{'objects':[],'image_tag':tag},'REVIEWED',0)
    result=services.datasets.freeze(Context(),{'root':p.root,'name':'标签','frame_ids':ids[:2]})
    with pytest.raises(AppError):services.datasets.export(Context(),{'root':p.root,'version_id':result['version_id'],'format':'yolo_detect','parent':str(tmp_path)})

def test_clip_revisions_delete_and_label_dependency(services,media_project):
    _,media_ids,_=media_project;label=services.annotations.labels()[0]
    value={'media_id':media_ids[0],'start_us':0,'end_us':100000,'tag':'ABNORMAL','status':'REVIEWED','label_id':label['id']}
    clip=services.annotations.save_clip(value);updated=services.annotations.save_clip(dict(value,id=clip['id'],revision=1,end_us=200000))
    assert updated['revision']==2 and len(updated['history'])==2
    services.annotations.delete_clip(clip['id'],2);assert services.annotations.clips(media_ids[0])==[]
    with pytest.raises(AppError):services.annotations.delete_label(label['id'])

def test_disabled_label_and_invalid_polygon_rejected(services,media_project):
    _,_,ids=media_project;label=services.annotations.labels()[0];label['enabled']=False;services.annotations.save_label(label)
    value={'objects':[{'id':str(uuid4()),'kind':'box','label_id':label['id'],'geometry':[1,1,10,10]}],'image_tag':'ABNORMAL'}
    with pytest.raises(AppError):services.annotations.save(ids[0],value,'REVIEWED',0)
    label=services.annotations.labels()[1];value['objects'][0].update(kind='polygon',label_id=label['id'],geometry=[[0,0],[100,100],[0,100],[100,0]])
    with pytest.raises(AppError):services.annotations.save(ids[0],value,'REVIEWED',0)

@pytest.mark.parametrize('operation',['freeze','export'])
def test_database_commit_failure_restores_partial_directory(services,media_project,tmp_path,monkeypatch,operation):
    from contextlib import contextmanager
    from ivad_app.storage.models import DatasetSample,ExportRecord
    p,_,ids=media_project;reviewed(services,[ids[0]])
    payload={'root':p.root,'name':'事务失败','frame_ids':[ids[0]]}
    if operation=='export':version=services.datasets.freeze(Context(),payload)
    original=Database.transaction
    @contextmanager
    def fail_commit(db):
        with original(db) as session:
            yield session
            target=DatasetSample if operation=='freeze' else ExportRecord
            if any(isinstance(row,target) for row in session.new):raise RuntimeError('controlled commit failure')
    monkeypatch.setattr(Database,'transaction',fail_commit)
    with pytest.raises(RuntimeError):
        if operation=='freeze':services.datasets.freeze(Context(),payload)
        else:services.datasets.export(Context(),{'root':p.root,'version_id':version['version_id'],'format':'coco','parent':str(tmp_path)})
    if operation=='freeze':assert not list((Path(p.root)/'datasets').glob('*/v*')) and list((Path(p.root)/'datasets').glob('*/*.partial'))
    else:assert not list(tmp_path.glob('IVAD-*/export_manifest.json')) and list(tmp_path.glob('.ivad-export-*.partial'))

def test_exact_duplicate_and_normal_negative(services,media_project,tmp_path):
    p,mids,ids=media_project;reviewed(services,[ids[0]])
    duplicate=services.media.capture(mids[0],0);services.annotations.save(duplicate,{'objects':[],'image_tag':'NORMAL'},'REVIEWED',0)
    preview=services.datasets.preview([ids[0],duplicate]);assert preview['count']==1 and any('SHA256' in w for w in preview['warnings'])
    services.annotations.save(ids[1],{'objects':[],'image_tag':'NORMAL'},'REVIEWED',0)
    version=services.datasets.freeze(Context(),{'root':p.root,'name':'正常负样本','frame_ids':ids[:2]})
    out=services.datasets.export(Context(),{'root':p.root,'version_id':version['version_id'],'format':'yolo_detect','parent':str(tmp_path)})
    assert any(p.read_text()=='' for p in (Path(out['path'])/'labels').rglob('*.txt'))

def test_camera_roi_normalized_across_media(services,tmp_path,sample_videos):
    p=services.projects.create(str(tmp_path),'共享摄像头ROI')
    imported=services.media.import_batch(Context(),{'root':p.root,'paths':[str(sample_videos/'sample.mp4'),str(sample_videos/'sample.mov')],'mode':'REFERENCE','camera':'CAM-01'})
    frames=[services.media.capture(mid,0) for mid in imported['imported']]
    roi=[{'id':str(uuid4()),'kind':'roi_polygon','geometry':[[0,0],[160,0],[160,90]]}]
    services.annotations.save(frames[0],{'objects':[],'image_tag':'NORMAL'},'DRAFT',0,roi,0,True)
    loaded=services.annotations.load(frames[1],camera_roi=True)
    assert loaded['scope']=='camera:CAM-01' and loaded['roi_objects'][0]['geometry']==roi[0]['geometry']
    assert services.annotations.load(frames[1],camera_roi=False)['roi_objects']==[]

def test_restart_marks_p2_task_interrupted_retains_payload(services,tmp_path):
    from ivad_app.storage.models import JobRecord
    from ivad_app.core.application import ApplicationServices
    job_id=str(uuid4());payload={'root':str(tmp_path),'media_id':'controlled-lost-worker','options':{'maximum':12}}
    with services.db.transaction() as session:
        session.add(JobRecord(id=job_id,kind='p2_extract',project_id=None,state='RUNNING',progress=24,error='',created_at='now',updated_at='now',payload=payload,result={}))
    directory=services.db.path.parent;services.close()
    reopened=ApplicationServices(services.root,directory)
    try:
        row=reopened.jobs.get(job_id);assert row['state']=='INTERRUPTED' and row['payload']==payload and row['progress']==24
    finally:reopened.close()
