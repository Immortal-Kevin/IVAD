from PySide6.QtCore import Qt,QPointF
from PySide6.QtWidgets import QMessageBox,QInputDialog
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
import threading

def test_gui_quick_batch_camera_exclude_restore(qtbot,services,media_project,monkeypatch):
    project,media,ids=media_project
    w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('annotation');a=w.p2.annotation
    qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading,timeout=10000)
    first=a.frame_id;a.image_tag.setCurrentIndex(1)
    assert a.image_label.currentData() is None and not a.image_label.isEnabled()
    assert not a.tool.model().item(1).isEnabled()
    click(qtbot,a,'annotation_quick_save');qtbot.waitUntil(lambda:a.frame_id!=first and not a.loading,timeout=10000)
    assert services.annotations.load(first)['payload']['objects']==[]
    assert services.annotations.load(first)['status']=='DRAFT'
    second=a.frame_id;a.classes.setCurrentIndex(1);a.image_tag.setCurrentIndex(2);a.tool.setCurrentIndex(1)
    qtbot.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(20,20)))
    qtbot.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(90,90)))
    click(qtbot,a,'annotation_quick_save');qtbot.waitUntil(lambda:a.frame_id!=second and not a.loading,timeout=10000)
    assert services.annotations.load(second)['payload']['objects']
    a.navigate(-1);qtbot.waitUntil(lambda:a.frame_id==second and not a.loading,timeout=10000)
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:QMessageBox.StandardButton.No)
    a.image_tag.setCurrentIndex(1);assert a.image_tag.currentData()=='ABNORMAL' and a.canvas.shapes
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:QMessageBox.StandardButton.Yes)
    a.image_tag.setCurrentIndex(1);qtbot.waitUntil(lambda:not a.saving and not a.dirty,timeout=10000)
    assert services.annotations.load(second)['payload']['objects']==[]
    assert len(services.annotations.revisions(second))>=2
    monkeypatch.setattr(QInputDialog,'getItem',lambda *args,**kwargs:(args[3][-1],True))
    click(qtbot,a,'annotation_restore_history');qtbot.waitUntil(lambda:not a.loading and a.image_tag.currentData()=='ABNORMAL',timeout=10000)
    assert a.canvas.shapes
    a.auto_next.setChecked(False);click(qtbot,a,'annotation_quick_save')
    qtbot.waitUntil(lambda:not a.saving and not a.dirty,timeout=10000);assert a.frame_id==second
    a.navigate(1);qtbot.waitUntil(lambda:a.frame_id!=second and not a.loading,timeout=10000)
    third=a.frame_id;a.image_tag.setCurrentIndex(0);a.reason.setText('测试夹具待复核');a.mark_dirty()
    click(qtbot,a,'annotation_quick_save');qtbot.waitUntil(lambda:not a.saving and not a.dirty,timeout=10000)
    assert services.annotations.frames_status()[third]['processing_state']=='UNCERTAIN'
    a.select_checked(True);a.batch_action('normal')
    qtbot.waitUntil(lambda:not a.batch_busy,timeout=10000)
    assert services.annotations.load(second)['payload']['objects']
    assert services.annotations.load(third)['payload']['image_tag']=='UNKNOWN'
    w.show_page('projects');panel=w.p2.hotfix.cameras;w.p2.hotfix.tabs.setCurrentIndex(1);panel.new();panel.fields['name'].setText('1204-1202给煤机摄像头')
    click(qtbot,panel,'project_camera_save');qtbot.waitUntil(lambda:bool(services.cameras.list()),timeout=10000)
    camera=services.cameras.list()[0]['id'];mid=a.media_id;w.show_page('media');media=w.p2.media
    qtbot.waitUntil(lambda:media.camera_choice.findData(camera)>=0,timeout=10000)
    media.table.selectRow(next(i for i,r in enumerate(media.media_rows) if r['id']==mid))
    qtbot.waitUntil(lambda:bool(media.selected_media) and media.selected_media['id']==mid,timeout=10000)
    media.camera_choice.setCurrentIndex(media.camera_choice.findData(camera))
    qtbot.waitUntil(lambda:not a.loading and not w.p2.refreshing,timeout=10000)
    w.p2.refresh()
    qtbot.waitUntil(lambda:not w.p2.refreshing and not a.loading,timeout=10000);qtbot.wait(80)
    assert media.camera_choice.currentData()==camera
    click(qtbot,media,'media_camera_save')
    qtbot.waitUntil(lambda:a.camera_id==camera and not a.loading,timeout=10000)
    assert services.media.get(a.media_id)['camera_id']==camera
    w.show_page('annotation')
    # A normal DRAFT frame is soft-excluded; the saved document survives.
    a.navigate(1);qtbot.waitUntil(lambda:a.frame_id!=third and not a.loading,timeout=10000)
    fid=a.frame_id;before=services.annotations.load(fid)['payload']
    monkeypatch.setattr(QInputDialog,'getItem',lambda *args,**kwargs:('严重运动模糊',True))
    a.batch_action('exclude',True);qtbot.waitUntil(lambda:not a.batch_busy,timeout=10000)
    qtbot.waitUntil(lambda:services.annotations.frames_status()[fid]['processing_state']=='EXCLUDED',timeout=10000)
    a.state_filter.setCurrentIndex(a.state_filter.findData('EXCLUDED'))
    qtbot.waitUntil(lambda:a.frame_id==fid and not a.loading,timeout=10000)
    assert not a.quick_button.isEnabled()
    a.batch_action('restore',True);qtbot.waitUntil(lambda:not a.batch_busy,timeout=10000)
    assert services.annotations.load(fid)['payload']==before
    close_window(qtbot,w)

def test_refresh_coalesces_label_save_while_collection_running(qtbot,services,media_project,monkeypatch):
    project,_,_=media_project;w=make_window(qtbot,services);w.p2.set_project(project)
    qtbot.waitUntil(lambda:not w.p2.refreshing and bool(w.p2.annotation.frame_id) and not w.p2.annotation.loading,timeout=10000)
    original=services.annotations.labels;old_rows=original();entered=threading.Event();release=threading.Event();calls=[]
    def delayed(root=None,**kwargs):
        calls.append(root)
        if len(calls)==1:
            entered.set();assert release.wait(5);return old_rows
        return original(root,**kwargs)
    monkeypatch.setattr(services.annotations,'labels',delayed)
    w.p2.refresh();qtbot.waitUntil(entered.is_set,timeout=5000)
    new=services.annotations.save_label({'name':'刷新并发回归类别'})
    w.p2.refresh();assert w.p2.refresh_pending
    release.set();qtbot.waitUntil(lambda:w.p2.annotation.classes.findData(new['id'])>=0,timeout=10000)
    assert len(calls)>=2
    close_window(qtbot,w)


def test_single_exclude_next_default_and_restore(qtbot,services,media_project,monkeypatch):
    project,_,_=media_project;w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('annotation');a=w.p2.annotation
    qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and not w.p2.refreshing,timeout=10000)
    first=a.frame_id;following=a.frames.item(a.frames.currentRow()+1).data(Qt.ItemDataRole.UserRole)
    assert a.auto_next.isChecked()
    monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:QMessageBox.StandardButton.Yes)
    seen=[]
    def choose(*args,**kwargs):
        seen.extend(args[3]);assert args[5] is False;return ('严重模糊',True)
    monkeypatch.setattr(QInputDialog,'getItem',choose)
    click(qtbot,a,'frame_exclude')
    qtbot.waitUntil(lambda:not a.batch_busy and not a.loading and a.frame_id==following and not w.p2.refreshing,timeout=10000)
    assert len(seen)==6 and services.annotations.frames_status()[first]['processing_state']=='EXCLUDED'
    a.state_filter.setCurrentIndex(a.state_filter.findData('EXCLUDED'))
    qtbot.waitUntil(lambda:a.frame_id==first and not a.loading,timeout=10000)
    a.batch_action('restore',True);qtbot.waitUntil(lambda:not a.batch_busy,timeout=10000)
    assert services.annotations.frames_status()[first]['processing_state']=='UNPROCESSED'
    close_window(qtbot,w)
