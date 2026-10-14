import copy,json,sqlite3,shutil
from uuid import uuid4
from pathlib import Path
import pytest
from sqlalchemy import select,text
from ivad_app.core.contracts import AppError
from ivad_app.storage.models import Annotation,ExtractedFrame,Camera,MediaAsset
from ivad_app.storage.database import Database
from tests.test_p2_services import media_project
from tests.test_p2_media import Context,sample_videos

def save(services,fid,tag='NORMAL',objects=None,status='DRAFT'):
    rev=services.annotations.load(fid)['revision']
    return services.annotations.save(fid,{'image_tag':tag,'objects':objects or [],'image_label_id':None},status,rev)

def test_processing_states_and_normal_conflict(services,media_project):
    p,m,ids=media_project;s=services.annotations
    assert s.frames_status()[ids[0]]['processing_state']=='UNPROCESSED'
    save(services,ids[0]);assert s.frames_status()[ids[0]]['processing_state']=='NORMAL'
    save(services,ids[1],'UNKNOWN');assert s.frames_status()[ids[1]]['processing_state']=='UNCERTAIN'
    label=s.labels()[0]['id'];objects=[{'id':str(uuid4()),'kind':'box','geometry':[1,1,20,20],'label_id':label}]
    save(services,ids[2],'ABNORMAL',objects,'REVIEWED')
    with pytest.raises(AppError,match='确认'):save(services,ids[2],'NORMAL')
    current=s.load(ids[2]);s.save(ids[2],{'image_tag':'NORMAL','objects':[],'normal_conversion_confirmed':True},'DRAFT',current['revision'])
    s.restore_revision(ids[2],1,2)
    assert s.load(ids[2])['payload']['objects']==[dict(objects[0],source='Human Generated')]
    assert len(s.revisions(ids[2]))==3

def test_batch_normal_skips_abnormal_uncertain_reviewed_and_transaction(services,media_project,monkeypatch):
    p,m,ids=media_project;s=services.annotations
    s.labels()
    save(services,ids[0],'ABNORMAL');save(services,ids[1],'UNKNOWN');save(services,ids[2],'NORMAL',status='REVIEWED')
    preview=s.batch_preview(ids[:5],'normal');assert len(preview['skipped'])==3
    result=s.batch_apply(preview);assert result['changed']==2
    assert s.load(ids[3])['payload']['objects']==[] and s.load(ids[3])['status']=='DRAFT'
    preview=s.batch_preview(ids[5:7],'normal')
    # Inject a late failure inside the transaction, after the first update.
    from sqlalchemy.orm import Session
    original=Session.add;calls=[]
    def injected(session,obj,*args,**kwargs):
        from ivad_app.storage.models import AnnotationRevision
        if isinstance(obj,AnnotationRevision):
            calls.append(obj)
            if len(calls)==2:raise RuntimeError('TEST FIXTURE transactional failure')
        return original(session,obj,*args,**kwargs)
    monkeypatch.setattr(Session,'add',injected)
    with pytest.raises(RuntimeError):s.batch_apply(preview)
    assert all(s.load(fid)['revision']==0 for fid in ids[5:7])

def test_exclusion_recovery_protection_and_new_snapshot(services,media_project,tmp_path):
    p,m,ids=media_project;s=services.annotations
    s.labels()
    save(services,ids[0],status='REVIEWED')
    old=services.datasets.freeze(Context(),{'root':p.root,'name':'旧冻结','frame_ids':[ids[0]]})
    folder,snapshot=services.datasets.snapshot(old['version_id']);before=(folder/'manifest.json').read_bytes()
    preview=s.batch_preview(ids[:3],'exclude');assert len(preview['skipped'])==1
    paths={fid:services.media.frame_image(fid)[0]['path'] for fid in ids[:3]}
    s.batch_apply(preview,'测试：严重模糊')
    assert s.frames_status()[ids[1]]['processing_state']=='EXCLUDED'
    assert all((Path(p.root)/value).is_file() for value in paths.values())
    with pytest.raises(AppError):save(services,ids[1])
    assert ids[1] not in [f['id'] for f in services.datasets.candidates()]
    with pytest.raises(AppError):services.datasets.freeze(Context(),{'root':p.root,'name':'禁止剔除','frame_ids':[ids[1]]})
    restored=s.batch_preview(ids[:3],'restore');s.batch_apply(restored)
    assert s.frames_status()[ids[1]]['processing_state']=='UNPROCESSED'
    assert s.load(ids[1])['frame']['handling']['history'][1]['action']=='restore'
    assert (folder/'manifest.json').read_bytes()==before
    services.datasets.export(Context(),{'root':p.root,'version_id':old['version_id'],'format':'yolo_detect','parent':str(tmp_path)})
    new=services.datasets.freeze(Context(),{'root':p.root,'name':'新冻结','frame_ids':[ids[0]]})
    assert new['images']==1

def test_camera_uuid_rename_clip_frame_roi_inheritance(services,media_project):
    p,media,ids=media_project;s=services.annotations
    camera=services.cameras.save('1204-1202给煤机摄像头')
    services.cameras.associate(media[0],camera['id'],None)
    label=s.labels()[0]['id'];roi=[{'id':str(uuid4()),'kind':'roi_box','geometry':[1,1,40,40]}]
    s.save(ids[0],{'objects':[],'image_tag':'NORMAL'},'DRAFT',0,roi,0,True)
    renamed=services.cameras.save('摄像头新名称',camera['id'],camera['revision'])
    assert renamed['id']==camera['id']
    assert s.load(ids[0],camera_roi=True)['scope']=='camera:'+camera['id']
    clip=services.media.save_video_clip(Context(),{'root':p.root,'media_id':media[0],'start_us':0,'end_us':400000})
    clipped=services.media.get(clip['media_id']);assert clipped['camera_id']==camera['id']
    frame=services.media.capture(clipped['id'],0)
    assert s.load(frame,camera_roi=True)['roi_objects'][0]['geometry']==roi[0]['geometry']
    assert s.load(frame)['payload']['objects']==[]

def test_0004_upgrade_preserves_annotations_and_creates_backup(tmp_path):
    dbpath=tmp_path/'old.sqlite';old=Database(dbpath,create=True,revision='0004')
    with old.engine.begin() as conn:
        conn.execute(text("INSERT INTO media_assets(id,project_id,name,original_path,path,mode,sha256,size,video,camera,equipment,site,state,error,job_id,imported_at,kind,clip_info) VALUES('m','p','录像','','','REFERENCE','hash',1,'{}','旧编号','','','READY','','','now','ORIGINAL','{}')"))
        conn.execute(text("INSERT INTO rois(id,scope,media_id,camera,payload,revision,updated_at) VALUES('r','camera:旧编号','m','旧编号','{\"objects\":[],\"history\":[]}',3,'now')"))
    old.close();new=Database(dbpath)
    with new.engine.connect() as conn:
        cid=conn.execute(text('SELECT camera_id FROM media_assets')).scalar()
        assert conn.execute(text('SELECT name FROM cameras WHERE id=:id'),{'id':cid}).scalar()=='旧编号'
        assert conn.execute(text('SELECT scope,revision FROM rois')).one()==('camera:'+cid,3)
    new.close();backup=next(tmp_path.glob('*.backup'))
    with sqlite3.connect(backup) as raw:assert raw.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0004'

def test_preview_detects_concurrent_annotation_change(services,media_project):
    p,m,ids=media_project;preview=services.annotations.batch_preview(ids[:2],'normal')
    save(services,ids[1],'ABNORMAL')
    with pytest.raises(AppError):services.annotations.batch_apply(preview)
    assert services.annotations.load(ids[0])['revision']==0
