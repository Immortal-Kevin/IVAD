import copy,json
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select
from ivad_app.core.contracts import AppError
from ivad_app.storage.models import ExtractedFrame,RegionOfInterest,ModelVersion
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context


def test_soft_exclusion_keeps_review_snapshot_and_restores(services,media_project):
    p,m,ids=media_project;s=services.annotations;label=s.labels()[0]['id']
    box={'id':str(uuid4()),'kind':'box','label_id':label,'geometry':[1,2,20,20]}
    s.save(ids[0],{'image_tag':'ABNORMAL','objects':[box]},'REVIEWED',0)
    frozen=services.datasets.freeze(Context(),{'root':p.root,'name':'protected fixture','frame_ids':[ids[0]]})
    folder,snapshot=services.datasets.snapshot(frozen['version_id']);manifest=(folder/'manifest.json').read_bytes()
    doc=s.load(ids[0]);history=s.revisions(ids[0]);preview=s.batch_preview(ids[:2],'exclude')
    assert preview['annotated']==1 and preview['referenced']==1 and len(preview['eligible'])==2
    result=s.batch_apply(preview,'测试夹具严重模糊');assert result['changed']==2 and result['failed']==0
    assert s.load(ids[0])['payload']==doc['payload'] and s.load(ids[0])['status']=='REVIEWED'
    assert s.revisions(ids[0])==history and (folder/'manifest.json').read_bytes()==manifest
    assert ids[0] not in {r['id'] for r in services.datasets.candidates()}
    assert not s.batch_preview(ids[:2],'exclude')['eligible']
    s.batch_apply(s.batch_preview(ids[:2],'restore'))
    assert s.load(ids[0])['completion_state']=='LABELED' and s.revisions(ids[0])==history
    assert (folder/'manifest.json').read_bytes()==manifest


def test_worklist_remove_is_independent_of_training_and_exclusion(services,media_project):
    p,m,ids=media_project;s=services.annotations;s.save(ids[0],{'image_tag':'NORMAL','objects':[]},'REVIEWED',0)
    before=s.load(ids[0]);s.batch_apply(s.batch_preview([ids[0]],'remove'))
    assert s.load(ids[0])['frame']['handling']['worklist_hidden']
    assert s.load(ids[0])['payload']==before['payload'] and ids[0] in {r['id'] for r in services.datasets.candidates()}
    s.batch_apply(s.batch_preview([ids[0]],'exclude'),'fixture');s.batch_apply(s.batch_preview([ids[0]],'return'))
    assert s.load(ids[0])['processing_state']=='EXCLUDED' and not s.load(ids[0])['frame']['handling']['worklist_hidden']
    s.batch_apply(s.batch_preview([ids[0]],'restore'));assert s.load(ids[0])['processing_state']=='NORMAL'


def test_camera_change_after_preview_rolls_back(services,media_project):
    p,m,ids=media_project;s=services.annotations;preview=s.batch_preview(ids[:2],'exclude')
    camera=services.cameras.save('A');services.cameras.associate(m[0],camera['id'],None)
    with pytest.raises(AppError):s.batch_apply(preview,'fixture')
    assert all(s.load(fid)['processing_state']!='EXCLUDED' for fid in ids[:2])

@pytest.mark.parametrize('kind,geometry',[('box',[1,2,20,20]),('polygon',[[1,2],[20,2],[20,20]])])
def test_valid_objects_auto_abnormal_completion_and_deleted_objects(services,media_project,kind,geometry):
    p,m,ids=media_project;s=services.annotations;label=s.labels()[0]['id'];obj={'id':str(uuid4()),'kind':kind,'geometry':geometry,'label_id':label}
    result=s.save(ids[0],{'image_tag':'UNKNOWN','objects':[obj]},None,0)
    assert result['completion_state']=='LABELED' and s.load(ids[0])['payload']['image_tag']=='ABNORMAL'
    assert s.load(ids[0])['status']=='DRAFT' and ids[0] not in {r['id'] for r in services.datasets.candidates()}
    s.save(ids[0],{'image_tag':'ABNORMAL','objects':[]},None,1)
    assert s.load(ids[0])['completion_state']=='UNLABELED'
    with pytest.raises(AppError):s.save(ids[1],{'image_tag':'UNKNOWN','objects':[dict(obj,geometry=[-1,-1,0,0])]},None,0)
    assert s.load(ids[1])['revision']==0


@pytest.mark.parametrize('mismatch',['aspect','rotation','coordinates'])
def test_roi_auto_priority_shared_reuse_and_geometry_guard(services,media_project,mismatch):
    p,m,ids=media_project;s=services.annotations;camera=services.cameras.save('same view')
    services.cameras.associate(m[0],camera['id'],None);services.cameras.associate(m[1],camera['id'],None)
    first=next(f for f in services.media.frames() if f['media_id']==m[0]);second=next(f for f in services.media.frames() if f['media_id']==m[1])
    roi=[{'id':str(uuid4()),'kind':'roi_box','geometry':[1,1,30,30]}]
    s.save(first['id'],{'image_tag':'NORMAL','objects':[]},None,0,roi,0,True)
    shared=s.load(second['id']);assert shared['camera_roi'] and shared['roi_objects']
    own=[dict(roi[0],id=str(uuid4()),geometry=[2,2,25,25])]
    s.save(second['id'],{'image_tag':'NORMAL','objects':[]},None,0,own,0,False)
    current=s.load(second['id']);assert not current['camera_roi'] and current['roi_objects'][0]['geometry']==own[0]['geometry']
    assert '配置不同' in current['notice'] and s.load(second['id'],camera_roi=True)['roi_objects']
    with services.store.open() as (_,db,_),db.transaction() as session:
        row=session.scalar(select(RegionOfInterest).where(RegionOfInterest.scope=='camera:'+camera['id']))
        payload=copy.deepcopy(row.payload)
        if mismatch=='aspect':payload['dimensions']=[100,1]
        elif mismatch=='rotation':payload['rotation']=90
        else:payload['objects'][0]['geometry']=[-1,0,2,2]
        row.payload=payload
    guarded=s.load(first['id']);assert not guarded['roi_objects'] and '不匹配' in guarded['notice']
    assert s.load(ids[-1])['camera_available'] is False


def test_camera_samples_and_many_to_many_model_configuration(services,media_project):
    p,m,ids=media_project;a=services.cameras.save('压滤机');b=services.cameras.save('给煤机')
    services.cameras.associate(m[0],a['id'],None);services.cameras.associate(m[1],b['id'],None)
    fa=next(f['id'] for f in services.media.frames() if f['media_id']==m[0]);fb=next(f['id'] for f in services.media.frames() if f['media_id']==m[1])
    label=services.annotations.labels()[0]['id'];services.annotations.save(fa,{'image_tag':'NORMAL','objects':[]},None,0)
    services.annotations.save(fb,{'image_tag':'UNKNOWN','objects':[{'id':str(uuid4()),'kind':'box','geometry':[1,1,20,20],'label_id':label}]},None,0)
    assert [r['id'] for r in services.datasets.camera_samples(a['id'],image_tag='NORMAL')]==[fa]
    assert [r['id'] for r in services.datasets.camera_samples(b['id'],image_tag='ABNORMAL',fault_id=label)]==[fb]
    assert not services.datasets.camera_samples(a['id'],fault_id=label)
    with services.store.open() as (_,db,_),db.transaction() as session:
        session.add(ModelVersion(id='model-shared',details={'state':'EXPERIMENTAL','fixture':True},revision=1));session.add(ModelVersion(id='model-dedicated',details={'state':'EXPERIMENTAL','fixture':True},revision=1))
    before=services.models.versions()
    extra_label=services.annotations.labels()[1]['id']
    for cid,mid in [(a['id'],'model-shared'),(b['id'],'model-shared'),(a['id'],'model-dedicated')]:
        assert not services.models.configure_camera(cid,mid,[label,extra_label])['enabled']
    assert len(services.models.camera_configurations(a['id']))==2 and len(services.models.camera_configurations())==3
    assert services.models.versions()==before
    with pytest.raises(AppError):services.annotations.delete_label(extra_label)
    services.cameras.save('C') # Registry integrity snapshot includes configuration metadata.
    assert len(services.models.camera_configurations())==3
    with pytest.raises(AppError):services.models.configure_camera('foreign','model-shared',[label])

@pytest.mark.parametrize('operation',['save','batch'])
def test_diagnostic_failure_after_commit_is_not_reported_as_rollback(services,media_project,monkeypatch,operation):
    _,_,ids=media_project
    def fail(*a,**k):raise OSError('TEST FIXTURE log unavailable')
    monkeypatch.setattr(services.logs,'write',fail)
    if operation=='save':
        result=services.annotations.save(ids[0],{'image_tag':'NORMAL','objects':[]},None,0)
        assert services.annotations.load(ids[0])['completion_state']=='LABELED'
    else:
        result=services.annotations.batch_apply(services.annotations.batch_preview([ids[0]],'exclude'),'fixture')
        assert services.annotations.load(ids[0])['processing_state']=='EXCLUDED'
    assert '已提交' in result['warning']
