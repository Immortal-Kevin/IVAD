import json, shutil, threading
from pathlib import Path
from uuid import uuid4
import pytest, yaml
from tests.test_p2_media import Context, sample_videos
from ivad_app.core.contracts import AppError

@pytest.fixture
def media_project(services,tmp_path,sample_videos):
    project=services.projects.create(str(tmp_path),'P2中文测试项目')
    report=services.media.import_batch(Context(),{'root':project.root,'paths':[str(sample_videos/n) for n in ['sample.mp4','sample.mov','sample.mkv']],'mode':'COPY','camera':''})
    ids=[]
    for media_id in report['imported']:
        media=services.media.get(media_id)
        r=services.media.extract(Context(),{'root':project.root,'media_id':media_id,'options':{'mode':'fixed','start_us':0,'end_us':media['video']['duration_us'],'interval_us':300000,'maximum':10,'format':'PNG'}})
        ids.extend(r['frames'])
    return project,report['imported'],ids

def test_copy_reference_dedup_missing_relocate(services,tmp_path,sample_videos):
    p=services.projects.create(str(tmp_path),'视频项目')
    src=tmp_path/'external.mp4';shutil.copyfile(sample_videos/'sample.mp4',src)
    report=services.media.import_batch(Context(),{'root':p.root,'paths':[str(src)],'mode':'REFERENCE'})
    media_id=report['imported'][0]
    duplicate=services.media.import_batch(Context(),{'root':p.root,'paths':[str(src)],'mode':'COPY'})
    assert duplicate['duplicates'][0]['id']==media_id
    moved=tmp_path/'moved.mp4';src.rename(moved)
    assert services.media.list()[0]['state']=='MISSING'
    services.media.relocate(media_id,str(moved));assert services.media.get(media_id)['accessible_path']==str(moved)
    assert moved.is_file()

def test_fixed_smart_range_and_retry(services,media_project):
    p,media_ids,ids=media_project
    media=services.media.get(media_ids[0]);source=__import__('ivad_app.video.reader',fromlist=['FileVideoSource']).FileVideoSource(Path(media['accessible_path']))
    actual={f.pts_us for f in source.iter_frames()}
    assert all(f['pts_us'] in actual for f in services.media.frames())
    opts={'mode':'smart','start_us':200000,'end_us':1000000,'interval_us':400000,'maximum':4,'format':'JPEG','quality':85,'max_width':160,'sensitivity':1,'baseline':True}
    result=services.media.extract(Context(),{'root':p.root,'media_id':media_ids[0],'options':opts})
    again=services.media.extract(Context(),{'root':p.root,'media_id':media_ids[0],'options':opts})
    assert result['frames']==again['frames'] and 1<=result['count']<=4
    selected=[f for f in services.media.frames() if f['id'] in result['frames']]
    assert all(200000<=f['time_us']<=1000000 and f['width']==160 for f in selected)
    assert services.media.check()['status']=='PASS'

def test_manual_annotation_roi_revision_labels(services,media_project):
    p,_,ids=media_project;frame=ids[0];label=services.annotations.labels()[0]
    payload={'objects':[{'id':str(uuid4()),'kind':'box','label_id':label['id'],'geometry':[10,20,60,40]}],'image_tag':'ABNORMAL','image_label_id':label['id']}
    roi=[{'id':str(uuid4()),'kind':'roi_polygon','geometry':[[0,0],[100,0],[100,100]]}]
    saved=services.annotations.save(frame,payload,'REVIEWED',0,roi,0)
    loaded=services.annotations.load(frame)
    assert loaded['payload']['objects'][0]['geometry']==[10,20,60,40]
    assert loaded['roi_objects'][0]['geometry']==roi[0]['geometry']
    with pytest.raises(AppError):services.annotations.save(frame,payload,'REVIEWED',0,roi,0)
    label['name']='中文重命名';updated=services.annotations.save_label(label)
    assert updated['id']==label['id']
    with pytest.raises(AppError):services.annotations.delete_label(label['id'])

@pytest.mark.parametrize('kind',['box','polygon'])
def test_dataset_freeze_and_all_compatible_exports(services,media_project,tmp_path,kind):
    p,media_ids,ids=media_project;label=services.annotations.labels()[0]
    chosen=[]
    for media_id in media_ids:
        selected=next(f for f in services.media.frames() if f['media_id']==media_id)
        geometry=[10,20,60,40] if kind=='box' else [[10,20],[70,20],[70,60],[10,60]]
        payload={'objects':[{'id':str(uuid4()),'kind':kind,'label_id':label['id'],'geometry':geometry}],'image_tag':'ABNORMAL','image_label_id':None}
        services.annotations.save(selected['id'],payload,'APPROVED',0);chosen.append(selected['id'])
    result=services.datasets.freeze(Context(),{'root':p.root,'name':'冻结中文数据集','frame_ids':chosen,'ratios':[70,20,10]})
    assert all(result['splits'][k]>0 for k in ['train','val','test'])
    folder,snapshot=services.datasets.snapshot(result['version_id'])
    original=(folder/'manifest.json').read_bytes()
    for format in ['yolo_detect','coco','ivad_native']+(['yolo_segment'] if kind=='polygon' else []):
        out=services.datasets.export(Context(),{'root':p.root,'version_id':result['version_id'],'format':format,'parent':str(tmp_path)})
        native=json.loads((Path(out['path'])/'ivad_native.json').read_text(encoding='utf-8'))
        assert len(native['samples'])==3 and all((Path(out['path'])/s['image']).is_file() for s in native['samples'])
        if format.startswith('yolo'):
            config=yaml.safe_load((Path(out['path'])/'data.yaml').read_text(encoding='utf-8'));assert config['names'][0]==label['name']
            text=next((Path(out['path'])/'labels').rglob('*.txt')).read_text().strip().split();assert text[0]=='0'
            if format=='yolo_detect':assert list(map(float,text[1:]))==pytest.approx([40/320,40/180,60/320,40/180],abs=1e-8)
    assert (folder/'manifest.json').read_bytes()==original
    if kind=='box':
        with pytest.raises(AppError,match='不能伪装'):services.datasets.export(Context(),{'root':p.root,'version_id':result['version_id'],'format':'yolo_segment','parent':str(tmp_path)})
