import json,os,copy
from pathlib import Path
from fractions import Fraction
from uuid import uuid4
import av,pytest
from PySide6.QtCore import Qt,QRect,QPoint
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from tests.test_p2_media import sample_videos,Context
from tests.test_p2_services import media_project
from tests.test_dataset_management_hotfix import truth
from ivad_app.video.reader import FileVideoSource
from ivad_app.video.timestamps import frame_times,relative_time_us

@pytest.mark.parametrize('name',['sample.mp4','vfr.mp4'])
def test_regular_and_variable_real_pts(sample_videos,name):
    source=FileVideoSource(sample_videos/name);frames=list(source.iter_frames())
    values=[frame_times({'pts_us':f.pts_us,'time_us':f.time_us},{'id':'original','video':source.metadata}) for f in frames]
    assert values[0]['media_relative_us']==0 and all(v['media_relative_us']==f.time_us for v,f in zip(values,frames))
    assert all(not v['timestamp_issues'] for v in values)
    if name=='vfr.mp4':assert len({b['media_relative_us']-a['media_relative_us'] for a,b in zip(values,values[1:])})>1

def test_nonzero_origin_real_decode_extract_and_clip(services,tmp_path,sample_videos):
    target=tmp_path/'nonzero.ts'
    with av.open(str(sample_videos/'sample.mp4')) as src,av.open(str(target),'w',format='mpegts') as dst:
        stream=dst.add_stream_from_template(src.streams.video[0])
        for packet in src.demux(video=0):
            if packet.dts is None:continue
            offset=int(Fraction(500,1)/packet.time_base);packet.pts+=offset;packet.dts+=offset;packet.stream=stream;dst.mux(packet)
    source=FileVideoSource(target);assert source.metadata['origin_us']>100000000
    p=services.projects.create(str(tmp_path),'Nonzero PTS fixture');mid=services.media.import_batch(Context(),dict(root=p.root,paths=[str(target)],mode='COPY'))['imported'][0]
    result=services.media.extract(Context(),dict(root=p.root,media_id=mid,options=dict(mode='fixed',start_us=200000,end_us=1000000,interval_us=200000,maximum=10,format='PNG')))
    rows=[r for r in services.media.frames() if r['id'] in result['frames']]
    assert len(rows)==4 and [r['media_relative_us'] for r in rows]==[200000,400000,600000,800000]
    assert all(r['pts_us']>100000000 and r['time_us']==r['media_relative_us'] for r in rows)
    for r in rows:assert source.at(r['media_relative_us']).pts_us==r['pts_us']
    clip=services.media.save_video_clip(Context(),dict(root=p.root,media_id=mid,start_us=200000,end_us=1000000,name='clip'))
    clipid=clip['media_id'];out=services.media.extract(Context(),dict(root=p.root,media_id=clipid,options=dict(mode='fixed',start_us=0,end_us=600000,interval_us=200000,maximum=10,format='PNG')))
    cliprows=[r for r in services.media.frames() if r['id'] in out['frames']]
    assert cliprows[0]['media_relative_us']==0 and cliprows[0]['source_relative_us']==200000
    assert all(r['source_relative_us']==r['media_relative_us']+200000 for r in cliprows)
    raw_before=[(r['id'],r['pts_us'],r['time_us']) for r in services.media.frames()]
    services.datasets.screening();assert raw_before==[(r['id'],r['pts_us'],r['time_us']) for r in services.media.frames()]

def test_nested_clip_unknown_and_mismatch_are_not_rewritten():
    root={'id':'root','video':{'origin_us':500000000,'duration_us':70000000}};clip={'id':'clip','parent_id':'root','video':{'origin_us':0,'duration_us':3000000},'clip_info':{'first_source_time_us':12000000}};nested={'id':'nested','parent_id':'clip','video':{'origin_us':0,'duration_us':1000000},'clip_info':{'first_source_time_us':400000}};frame={'pts_us':200000,'time_us':200000};before=copy.deepcopy(frame)
    result=frame_times(frame,nested,{m['id']:m for m in [root,clip,nested]});assert result['source_relative_us']==12600000 and frame==before and result['capture_datetime'] is None
    result=frame_times(dict(pts_us=500200000,time_us=900),root);assert result['media_relative_us']==200000 and result['timestamp_issues']
    del clip['clip_info']['first_source_time_us'];assert frame_times(frame,clip,{'root':root,'clip':clip})['source_relative_us'] is None

def test_compact_selection_feedback_tabs_and_protection(qtbot,services,truth,tmp_path):
    p,mids,ids,cams,label=truth;services.annotations.batch_apply(services.annotations.batch_preview([ids[1]],'exclude'),'TEST FIXTURE')
    w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:bool(d.all_rows) and not w.p2.refreshing,timeout=10000)
        assert '请打开项目' not in d.summary.text();d.camera.setCurrentIndex(0)
        click(qtbot,d,'dataset_select_all');assert len(d.selected_frames())==5
        click(qtbot,d,'dataset_select_normal');assert len(d.selected_frames())==2 and '正常已勾选2张' in d.selection_info.text()
        click(qtbot,d,'dataset_select_abnormal');assert len(d.selected_frames())==3 and '异常已勾选3张' in d.selection_info.text()
        selected=set(d.selected_frames());d.tabs.setCurrentIndex(1);assert set(d.selected_frames())==selected and '当前待添加3张' in d.counts.text()
        d.add_selected();assert not d.draft_frames() and 'BLOCKED' in d.action_info.text()
        d.allow_multi.setChecked(True);click(qtbot,d,'dataset_add_selected');assert len(d.draft_frames())==3 and '成功3' in d.action_info.text()
        click(qtbot,d,'dataset_add_selected');assert len(d.draft_frames())==3 and '重复跳过3' in d.action_info.text()
        click(qtbot,d,'dataset_clear_selection');assert not d.selected_frames() and len(d.draft_frames())==3
        d.tabs.setCurrentIndex(0);d.select_all();w.p2.refresh();qtbot.waitUntil(lambda:not w.p2.refreshing,timeout=10000);assert len(d.selected_frames())==5
        d.camera.setCurrentIndex(d.camera.findData(cams[1]));assert not d.selected_frames() and len(d.draft_frames())==3
        d.fault.addItem('无匹配类别','missing');d.fault.setCurrentIndex(d.fault.findData('missing'));assert '当前筛选条件下没有可用图片' in d.summary.text();d.fault.setCurrentIndex(0)
        d.data_error('测试夹具：图片数据读取失败');assert '数据读取失败' in d.summary.text();d.data_error('')
        output=Path(os.environ.get('IVAD_DATASET_V2_EVIDENCE',str(tmp_path/'v2-gui')));output.mkdir(parents=True,exist_ok=True);geometry=[]
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(100)
            assert d.filters_widget.height()<100
            controls=[d.camera,d.fault,d.tag,d.source,d.completion,d.exclusion]
            rects=[QRect(c.mapTo(d.filters_widget,QPoint(0,0)),c.size()) for c in controls]
            assert all(not r.intersects(b) for i,r in enumerate(rects) for b in rects[i+1:])
            assert all(d.filters_widget.rect().contains(r) for r in rects)
            geometry.append(dict(requested=[width,height],actual=[w.width(),w.height()],dpr=w.devicePixelRatioF(),filter_height=d.filters_widget.height(),table_height=d.candidates.height()))
            assert w.grab().save(str(output/f'compact-{width}.png'))
        (output/'geometry.json').write_text(json.dumps(geometry,indent=2),encoding='utf-8')
        d.set_project(None);assert d.summary.text()=='请先前往项目管理打开或创建项目。'
    finally:close_window(qtbot,w)
