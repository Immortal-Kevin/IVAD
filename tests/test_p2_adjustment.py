import json, threading, sqlite3
import time
import os
from pathlib import Path
from fractions import Fraction
from uuid import uuid4
import av, pytest
from PIL import Image
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QPushButton, QScrollArea
from tests.test_p2_media import Context, sample_videos
from tests.test_p2_services import media_project
from tests.test_gui import make_window, close_window
from ivad_app.core.contracts import AppError
from ivad_app.video.reader import FileVideoSource
from ivad_app.storage.project_store import file_hash
from ivad_app.storage.database import Database

@pytest.fixture
def long_reference(services,tmp_path):
    source=tmp_path/'长录像_设备故障场景_用于人工截取测试_20秒.mp4'
    with av.open(str(source),'w') as output:
        stream=output.add_stream('libx264',rate=25);stream.width=160;stream.height=90;stream.pix_fmt='yuv420p'
        for i in range(500):
            frame=av.VideoFrame.from_image(Image.new('RGB',(160,90),(i%256,30,90)));frame.pts=i;frame.time_base=Fraction(1,25)
            for packet in stream.encode(frame):output.mux(packet)
        for packet in stream.encode():output.mux(packet)
    project=services.projects.create(str(tmp_path),'补充测试')
    result=services.media.import_batch(Context(),{'root':project.root,'paths':[str(source)],'mode':'REFERENCE'})
    return project,result['imported'][0],source

def test_long_reference_clip_extract_annotation_dataset(services,long_reference,tmp_path):
    project,mid,source=long_reference;checksum=file_hash(source)
    result=services.media.save_video_clip(Context(),{'root':project.root,'media_id':mid,'start_us':5000000,'end_us':7000000,'note':'人工故障片段'})
    clip=services.media.get(result['media_id']);assert clip['kind']=='CLIP' and clip['mode']=='COPY' and clip['parent_id']==mid
    assert clip['clip_info']['frames']==50 and clip['clip_info']['first_source_time_us']==5000000
    frames=list(FileVideoSource(Path(clip['accessible_path'])).iter_frames());assert len(frames)==50 and frames[0].time_us==0
    assert file_hash(source)==checksum and services.media.get(mid)['mode']=='REFERENCE'
    out=services.media.extract(Context(),{'root':project.root,'media_id':clip['id'],'options':{'mode':'fixed','start_us':0,'end_us':1500000,'interval_us':500000,'maximum':3,'format':'PNG'}})
    label=services.annotations.labels()[0]
    for fid in out['frames']:services.annotations.save(fid,{'objects':[{'id':str(uuid4()),'kind':'box','geometry':[1,1,20,20],'label_id':label['id']}],'image_tag':'ABNORMAL'},'REVIEWED',0)
    original_frame=services.media.capture(mid,0);services.annotations.save(original_frame,{'objects':[],'image_tag':'NORMAL'},'REVIEWED',0);out['frames'].append(original_frame)
    version=services.datasets.freeze(Context(),{'root':project.root,'name':'片段数据集','frame_ids':out['frames']})
    _,snapshot=services.datasets.snapshot(version['version_id']);assert all(s['source_group_id']==mid for s in snapshot['samples'])
    services.datasets.export(Context(),{'root':project.root,'version_id':version['version_id'],'format':'yolo_detect','parent':str(tmp_path)})
    assert services.media.check()['status']=='PASS'

@pytest.mark.parametrize('start,end',[(700000,100000),(0,50000),(0,50000000),(-1,200000)])
def test_invalid_clip_range_no_resource(services,long_reference,start,end):
    p,mid,source=long_reference;before=file_hash(source)
    with pytest.raises(AppError):services.media.save_video_clip(Context(),{'root':p.root,'media_id':mid,'start_us':start,'end_us':end})
    assert len(services.media.list())==1 and file_hash(source)==before

def test_cancel_clip_removes_owned_staging_no_record(services,long_reference):
    p,mid,source=long_reference;before=file_hash(source)
    class Cancel(Context):
        def progress(self,value):
            if value>=10:self.cancel.set()
            self.check()
    with pytest.raises(AppError):services.media.save_video_clip(Cancel(),{'root':p.root,'media_id':mid,'start_us':0,'end_us':10000000})
    assert len(services.media.list())==1 and not list(Path(p.root).rglob('*.partial')) and file_hash(source)==before

def test_encoder_failure_no_false_ready(services,long_reference,monkeypatch):
    p,mid,source=long_reference;original=av.open;before=file_hash(source)
    def fail(path,mode='r',**kwargs):
        if mode=='w':raise RuntimeError('controlled encoder failure')
        return original(path,mode,**kwargs)
    monkeypatch.setattr(av,'open',fail)
    with pytest.raises(RuntimeError):services.media.save_video_clip(Context(),{'root':p.root,'media_id':mid,'start_us':0,'end_us':1000000})
    assert len(services.media.list())==1 and file_hash(source)==before

def test_schema_0003_upgrade_preserves_all_existing_columns(tmp_path):
    dbpath=tmp_path/'old.sqlite';db=Database(dbpath,create=True,revision='0003');db.close()
    with sqlite3.connect(dbpath) as raw:
        raw.execute("INSERT INTO media_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",('m','p','原录像','source','media/m.mp4','COPY','hash',12,'{}','','','','READY','','j','now'))
        before=raw.execute('SELECT * FROM media_assets').fetchone()
    upgraded=Database(dbpath);upgraded.close()
    with sqlite3.connect(dbpath) as raw:
        after=raw.execute('SELECT * FROM media_assets').fetchone();assert after[:len(before)]==before
        columns=[r[1] for r in raw.execute('pragma table_info(media_assets)')]
        values=dict(zip(columns,after));assert values['kind']=='ORIGINAL' and values['parent_id'] is None and values['clip_info']=='{}' and values['camera_id'] is None and values['lifecycle']=='{}'
    backup=next(tmp_path.glob('*.backup'))
    with sqlite3.connect(backup) as raw:assert raw.execute('SELECT version_num FROM alembic_version').fetchone()[0]=='0003'

def test_gui_clip_save_and_layout(qtbot,services,long_reference):
    p,mid,_=long_reference;window=make_window(qtbot,services);window.resize(1440,760);window.show_page('media');media=window.p2.media
    qtbot.waitUntil(lambda:len(media.media_rows)==1,timeout=5000);media.table.selectRow(0)
    qtbot.waitUntil(lambda:media.selected_media is not None and media.player.last_image is not None,timeout=5000)
    assert media.table.height()>220 and media.table.maximumHeight()>160
    assert media.splitter.widget(0).geometry().left()<media.splitter.widget(1).geometry().left()
    assert all(w.toolTip() for w in [media.start,media.end,media.sampling,media.interval,media.maximum,media.format,media.quality,media.max_width,media.sensitivity,media.baseline,media.extract_button,media.cancel_button])
    assert not media.quality.isEnabled();media.format.setCurrentText('JPEG');assert media.quality.isEnabled()
    media.tabs.setCurrentIndex(3);bar=media.tabs.tabBar();window.raise_();window.activateWindow();qtbot.wait(100)
    def tab_color(index):
        img=bar.grab().toImage();point=bar.tabRect(index).topLeft()+QPoint(4,4);ratio=img.devicePixelRatio();return img.pixelColor(round(point.x()*ratio),round(point.y()*ratio))
    qtbot.mouseMove(window,QPoint(10,10));qtbot.wait(40);inactive=tab_color(0);assert inactive.blue()>inactive.red() and inactive.red()<80
    active=tab_color(3);assert active.red()>200 and active.green()>200
    qtbot.mouseMove(bar,bar.tabRect(0).center())
    from PySide6.QtGui import QMouseEvent,QEnterEvent
    from PySide6.QtCore import QEvent,QPointF
    from PySide6.QtWidgets import QApplication
    pos=QPointF(bar.tabRect(0).center());global_pos=QPointF(bar.mapToGlobal(pos.toPoint()))
    QApplication.sendEvent(bar,QEnterEvent(pos,pos,global_pos))
    QApplication.sendEvent(bar,QMouseEvent(QEvent.Type.MouseMove,pos,global_pos,Qt.MouseButton.NoButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier))
    qtbot.wait(80);hover=tab_color(0);assert hover.red()>200 and hover.green()>200
    media.tabs.setCurrentIndex(1);media.operations_scroll.ensureWidgetVisible(media.parameter_help[1]);qtbot.wait(30)
    assert len(media.parameter_help)==8 and media.parameter_help[1].isVisible() and '1.000' in media.parameter_help[1].text()
    media.start.setValue(5);media.end.setValue(6);media.tabs.setCurrentIndex(3)
    media.operations_scroll.ensureWidgetVisible(media.save_video_button);qtbot.wait(30)
    qtbot.mouseClick(media.save_video_button,Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda:len(media.media_rows)==2,timeout=15000)
    clip_index=next(i for i,r in enumerate(media.media_rows) if r['kind']=='CLIP');assert media.table.item(clip_index,0).text().startswith('CLIP')
    media.table.selectRow(clip_index)
    qtbot.waitUntil(lambda:media.selected_media and media.selected_media['kind']=='CLIP' and media.player.last_image is not None,timeout=5000)
    evidence=services.root/os.environ.get('IVAD_P2_ADJUSTMENT_EVIDENCE_DIR',f'artifacts/test-runs/{time.time_ns()}/adjustment');evidence.mkdir(parents=True,exist_ok=True);window.grab().save(str(evidence/'gui-clip-save.png'))
    media.table.selectRow(next(i for i,r in enumerate(media.media_rows) if r['id']==mid))
    qtbot.waitUntil(lambda:media.selected_media['id']==mid,timeout=5000)
    assert media.end.value()==pytest.approx(20,abs=.001)
    close_window(qtbot,window)

def test_real_clip_job_cancel_and_history(services,long_reference,monkeypatch):
    from ivad_app.jobs.manager import JobContext
    p,mid,source=long_reference;before=file_hash(source);original=JobContext.progress
    def slow(context,value):time.sleep(.01);return original(context,value)
    monkeypatch.setattr(JobContext,'progress',slow)
    job=services.jobs.submit('p2_clip',p.id,{'root':p.root,'media_id':mid,'start_us':0,'end_us':10000000})
    deadline=time.monotonic()+10
    while services.jobs.get(job)['progress']==0 and time.monotonic()<deadline:time.sleep(.01)
    services.jobs.cancel(job)
    while services.jobs.get(job)['state'] not in {'CANCELLED','FAILED','SUCCEEDED'} and time.monotonic()<deadline:time.sleep(.01)
    assert services.jobs.get(job)['state']=='CANCELLED' and len(services.media.list())==1
    assert not list(Path(p.root).rglob('*.partial')) and file_hash(source)==before

@pytest.mark.parametrize('name',['vfr.mp4','noninteger.mp4','rotation.mp4'])
def test_clip_vfr_noninteger_rotation_actual_pts(services,tmp_path,sample_videos,name):
    p=services.projects.create(str(tmp_path),'时间戳片段')
    imported=services.media.import_batch(Context(),{'root':p.root,'paths':[str(sample_videos/name)],'mode':'COPY'})
    mid=imported['imported'][0];parent=services.media.get(mid);original=[f for f in FileVideoSource(Path(parent['accessible_path'])).iter_frames(200000,900000) if f.time_us<900000]
    result=services.media.save_video_clip(Context(),{'root':p.root,'media_id':mid,'start_us':200000,'end_us':900000})
    clip=services.media.get(result['media_id']);frames=list(FileVideoSource(Path(clip['accessible_path'])).iter_frames())
    assert [f.time_us for f in frames]==[f.time_us-original[0].time_us for f in original]
    assert frames[0].image.size==original[0].image.size and clip['video']['rotation']==0
    with pytest.raises(AppError):services.media.save_video_clip(Context(),{'root':p.root,'media_id':clip['id'],'start_us':0,'end_us':200000})
