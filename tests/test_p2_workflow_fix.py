import copy
from uuid import uuid4
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtWidgets import QMessageBox
from ivad_app.core.contracts import AppError
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from tests.test_gui import make_window, close_window
from tests.test_p2_media import Context
from ivad_app.video.reader import FileVideoSource

def wait_saved(qtbot,ann):
    qtbot.waitUntil(lambda:not ann.saving and not ann.dirty and ann.revision>0,timeout=10000)

def test_optional_camera_load_and_normal_save(services,media_project):
    project,media,frames=media_project
    data=services.annotations.load(frames[0],camera_roi=True)
    assert data['camera_roi'] is False and data['camera_available'] is False
    assert '不影响基础标注' in data['notice']
    services.annotations.save(frames[0],{'objects':[],'image_tag':'NORMAL'},'REVIEWED',0,camera_roi=True)
    loaded=services.annotations.load(frames[0],camera_roi=True)
    assert loaded['payload']['objects']==[] and loaded['payload']['image_tag']=='NORMAL'
    assert loaded['status']=='REVIEWED' and loaded['roi_revision']==0

def test_extraction_half_open_boundary(services,media_project):
    p,media,frames=media_project
    result=services.media.extract(Context(),{'root':p.root,'media_id':media[0],'options':{'mode':'fixed','start_us':0,'end_us':600000,'interval_us':200000,'maximum':10,'format':'PNG'}})
    selected=[f for f in services.media.frames() if f['id'] in result['frames']]
    assert len(selected)==3 and max(f['time_us'] for f in selected)<600000

def test_coarse_seek_retries_using_actual_pts(sample_videos,monkeypatch):
    import ivad_app.video.reader as reader
    import av
    real_open=av.open;meta=FileVideoSource.probe(sample_videos/'sample.mp4')
    class CoarseContainer:
        def __init__(self,*args,**kwargs):self.actual=real_open(*args,**kwargs);self.calls=0
        def __enter__(self):return self
        def __exit__(self,*args):self.actual.close()
        def __getattr__(self,name):return getattr(self.actual,name)
        def seek(self,target,**kwargs):
            self.calls+=1
            if self.calls==1:target=int(.9/kwargs['stream'].time_base)
            return self.actual.seek(target,**kwargs)
        def decode(self,stream):
            for frame in self.actual.decode(stream):
                if self.calls==1 and float(frame.time)<.9:continue
                yield frame
    monkeypatch.setattr(reader.av,'open',CoarseContainer)
    selected=list(FileVideoSource(sample_videos/'sample.mp4',meta).iter_frames(200000,600000))
    assert selected and selected[0].time_us==200000

def test_mpeg_never_uses_unreliable_seek(sample_videos,monkeypatch):
    import ivad_app.video.reader as reader
    import av
    from types import SimpleNamespace
    real_open=av.open;meta=FileVideoSource.probe(sample_videos/'sample.mp4')
    class MpegContainer:
        format=SimpleNamespace(name='mpeg')
        def __init__(self,*args,**kwargs):self.actual=real_open(*args,**kwargs)
        def __enter__(self):return self
        def __exit__(self,*args):self.actual.close()
        def __getattr__(self,name):return getattr(self.actual,name)
        def seek(self,*args,**kwargs):raise AssertionError('MPEG must decode sequentially')
    monkeypatch.setattr(reader.av,'open',MpegContainer)
    selected=list(FileVideoSource(sample_videos/'sample.mp4',meta).iter_frames(200000,600000))
    assert selected and selected[0].time_us==200000

def test_normal_navigation_roi_independence_and_reopen(qtbot,services,media_project,tmp_path,monkeypatch):
    project,media,frames=media_project
    w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('annotation');a=w.p2.annotation
    qtbot.waitUntil(lambda:a.frame_id is not None and not a.loading,timeout=10000)
    # Reproduce stale camera scope, including forced programmatic selection.
    a.roi_scope.setCurrentIndex(1)
    qtbot.waitUntil(lambda:not a.loading and a.roi_scope.currentIndex()==0,timeout=10000)
    first=a.frame_id;a.image_tag.setCurrentIndex(1)
    a.navigate(1)
    qtbot.waitUntil(lambda:a.frame_id!=first and not a.loading,timeout=10000)
    assert services.annotations.load(first)['payload']['objects']==[]
    assert services.annotations.load(first)['payload']['image_tag']=='NORMAL'
    from tests.hotfix_helpers import review_fixture
    review_fixture(qtbot,w,first,'REVIEWED',monkeypatch)
    second=a.frame_id;a.classes.setCurrentIndex(1);a.tool.setCurrentIndex(1)
    qtbot.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(20,20)))
    qtbot.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(90,90)))
    assert len(a.canvas.shapes)==1
    a.canvas.undo();assert a.canvas.shapes==[]
    a.canvas.redo();assert len(a.canvas.shapes)==1
    a.image_tag.setCurrentIndex(2);wait_saved(qtbot,a)
    target=copy.deepcopy(services.annotations.load(second)['payload']['objects'])
    a.canvas.add('roi_box',[0,0,100,100]);wait_saved(qtbot,a)
    loaded=services.annotations.load(second)
    assert loaded['payload']['objects']==target and len(loaded['roi_objects'])==1
    review_fixture(qtbot,w,second,'REVIEWED',monkeypatch)
    a.navigate(-1);qtbot.waitUntil(lambda:a.frame_id==first and not a.loading,timeout=10000)
    assert a.image_tag.currentData()=='NORMAL'
    assert not [o for o in a.canvas.shapes if not o['kind'].startswith('roi_')]
    close_window(qtbot,w)
    from ivad_app.core.application import ApplicationServices
    reopened=ApplicationServices(services.root,tmp_path/'reopen-fix')
    reopened.projects.open(project.root)
    assert reopened.annotations.load(first)['payload']['objects']==[]
    assert reopened.annotations.load(first)['status']=='REVIEWED'
    assert reopened.annotations.load(second)['payload']['objects']==target
    reopened.close()

def test_failed_save_navigation_cancel_discard_retry(qtbot,services,media_project,monkeypatch):
    project,media,frames=media_project
    w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('annotation');a=w.p2.annotation
    qtbot.waitUntil(lambda:a.frame_id is not None and not a.loading,timeout=10000)
    first=a.frame_id;original=services.annotations.save
    def fail(*args,**kwargs):raise AppError('TEST_FAILURE','测试夹具：模拟写入失败')
    monkeypatch.setattr(services.annotations,'save',fail)
    a.image_tag.setCurrentIndex(1);a.navigate(1)
    qtbot.waitUntil(lambda:a.save_error,timeout=10000)
    assert a.frame_id==first and a.frames.currentRow()==0
    def choose(text):
        def click():
            dialog=w.window().findChildren(QMessageBox)[-1]
            next(b for b in dialog.buttons() if b.text()==text).click()
        QTimer.singleShot(50,click)
    choose('取消');a.navigate(1);assert a.frame_id==first and a.dirty
    monkeypatch.setattr(services.annotations,'save',original)
    choose('保存后继续');a.navigate(1)
    qtbot.waitUntil(lambda:a.frame_id!=first and not a.loading,timeout=10000)
    assert services.annotations.load(first)['payload']['image_tag']=='NORMAL'
    second=a.frame_id;monkeypatch.setattr(services.annotations,'save',fail)
    a.image_tag.setCurrentIndex(2);a.save_now();qtbot.waitUntil(lambda:a.save_error,timeout=10000)
    choose('不保存继续');a.navigate(1)
    qtbot.waitUntil(lambda:a.frame_id!=second and not a.loading,timeout=10000)
    assert services.annotations.load(second)['revision']==0
    monkeypatch.setattr(services.annotations,'save',original);close_window(qtbot,w)
