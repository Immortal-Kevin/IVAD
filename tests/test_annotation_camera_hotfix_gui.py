from pathlib import Path
import os
from PySide6.QtCore import Qt,QPointF
from PySide6.QtWidgets import QMessageBox,QInputDialog,QScrollArea
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from ivad_app.core.contracts import AppError


def test_gui_filter_batch_status_and_feedback(qtbot,services,media_project,monkeypatch):
    project,m,ids=media_project;c1=services.cameras.save('测试压滤机',details={'code':'8525'});c2=services.cameras.save('测试给煤机',details={'code':'12021204'})
    services.cameras.associate(m[0],c1['id'],None);services.cameras.associate(m[1],c2['id'],None)
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    notices=[];monkeypatch.setattr(QMessageBox,'information',lambda *args,**k:notices.append(args[2]))
    monkeypatch.setattr(QInputDialog,'getItem',lambda *a,**k:('严重模糊',True))
    w.confirm_discard=lambda:True
    def wait():qtbot.waitUntil(lambda:not a.loading and not a.saving and not a.dirty and not a.batch_busy and not w.p2.refreshing,timeout=10000)
    def refresh():w.p2.refresh();wait();qtbot.wait(50)
    evidence=Path(os.environ.get('IVAD_ANNOTATION_EVIDENCE',str(Path(services.data_dir)/'test-evidence')))
    evidence.mkdir(parents=True,exist_ok=True)
    def capture(name):
        w.resize(1920,1080)
        for scroll in a.findChildren(QScrollArea):scroll.verticalScrollBar().setValue(0)
        qtbot.wait(60);assert w.grab().save(str(evidence/(name+('-dpi2' if os.environ.get('QT_SCALE_FACTOR')=='2' else '')+'.png')))
    try:
        wait();qtbot.waitUntil(lambda:a.camera_filter.findData(c1['id'])>=0,timeout=10000)
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c1['id']));wait()
        assert all(next(r for r in a.frame_rows if r['id']==a.frames.item(i).data(Qt.ItemDataRole.UserRole))['camera_id']==c1['id'] for i in range(a.frames.count()))
        assert not a.roi_scope.isVisible() and a.camera_id==c1['id']
        a.auto_next.setChecked(False);fid=a.frame_id;a.image_tag.setCurrentIndex(1);a.debounce.stop()
        assert a.review.currentData()=='UNLABELED' and services.annotations.load(fid)['revision']==0
        click(qtbot,a,'annotation_quick_save');wait();assert a.review.currentData()=='LABELED'
        assert services.annotations.load(fid)['payload']['objects']==[] and services.annotations.load(fid)['status']=='DRAFT'
        capture('normal-saved-status')
        a.navigate(1);wait();boxfid=a.frame_id;a.classes.setCurrentIndex(1);a.tool.setCurrentIndex(1)
        qtbot.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(10,10)));qtbot.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(50,50)))
        a.debounce.stop();assert a.image_tag.currentData()=='ABNORMAL' and a.review.currentData()=='UNLABELED'
        click(qtbot,a,'save_annotation');wait();assert a.review.currentData()=='LABELED'
        capture('box-saved-status')
        a.navigate(1);wait();polyfid=a.frame_id;a.tool.setCurrentIndex(2)
        for point in [(10,10),(50,10),(50,50)]:qtbot.mouseClick(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(*point)))
        qtbot.mouseClick(a.canvas.viewport(),Qt.MouseButton.RightButton,pos=a.canvas.mapFromScene(QPointF(50,50)));a.debounce.stop()
        click(qtbot,a,'save_annotation');wait();assert a.review.currentData()=='LABELED' and services.annotations.load(polyfid)['payload']['objects'][0]['kind']=='polygon'
        refresh();a.clear_checked()
        for target in [fid,boxfid]:
            next(a.frames.item(i) for i in range(a.frames.count()) if a.frames.item(i).data(Qt.ItemDataRole.UserRole)==target).setCheckState(Qt.CheckState.Checked)
        click(qtbot,a,'frames_batch_exclude');wait();assert '成功2张' in a.batch_result.text()
        assert all(services.annotations.load(f)['processing_state']=='EXCLUDED' for f in [fid,boxfid])
        a.state_filter.setCurrentIndex(a.state_filter.findData('EXCLUDED'));wait();a.select_checked()
        click(qtbot,a,'frames_batch_restore');wait();assert '成功2张' in a.batch_result.text()
        a.state_filter.setCurrentIndex(a.state_filter.findData('ALL'));wait();a.select_checked()
        click(qtbot,a,'frames_batch_remove');wait();assert a.frames.count()==0 and '成功' in a.batch_result.text()
        a.worklist_filter.setCurrentIndex(a.worklist_filter.findData('REMOVED'));wait();assert a.frames.count()>0
        a.select_checked();click(qtbot,a,'frames_batch_return');wait();assert a.frames.count()==0
        a.worklist_filter.setCurrentIndex(0);wait();a.select_checked();assert a.chosen_frames()
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c2['id']));wait();assert not a.chosen_frames() and not a.checked_ids
        a.camera_filter.setCurrentIndex(0);wait();a.select_checked();before=services.annotations.frames_status()
        click(qtbot,a,'frames_batch_exclude');assert '多个摄像头' in a.batch_result.text() and services.annotations.frames_status()==before
        confirmations=[]
        monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:(confirmations.append(args[1]) or QMessageBox.StandardButton.Yes))
        a.cross_camera.setChecked(True);click(qtbot,a,'frames_batch_exclude');wait()
        assert '跨摄像头二次确认' in confirmations and '确认帧操作' in confirmations
        a.select_checked();click(qtbot,a,'frames_batch_restore');wait();a.cross_camera.setChecked(False)
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c1['id']));wait();a.select_checked();click(qtbot,a,'frames_batch_restore');wait()
        assert notices and '成功0张' in a.batch_result.text() and '尚未剔除' in a.batch_result.text()
        # Feedback is separate from frame load/refresh notices.
        text=a.batch_result.text();refresh();assert a.batch_result.text()==text
        output=evidence;w.resize(1920,1080);qtbot.wait(80);assert w.grab().save(str(output/('annotation-camera-filter'+('-dpi2' if os.environ.get('QT_SCALE_FACTOR')=='2' else '')+'.png')))
        assert services.annotations.load(boxfid)['payload']['objects']
    finally:
        a.dirty=False;a.save_error=False;a.debounce.stop();close_window(qtbot,w)


def test_gui_failed_save_does_not_complete(qtbot,services,media_project,monkeypatch):
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    try:
        qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading,timeout=10000);fid=a.frame_id
        def fail(*args,**kwargs):raise AppError('TEST_FIXTURE','模拟保存失败')
        monkeypatch.setattr(services.annotations,'save',fail);a.image_tag.setCurrentIndex(1);a.debounce.stop();a.save_now()
        qtbot.waitUntil(lambda:a.save_error and not a.saving,timeout=10000)
        assert a.review.currentData()=='UNLABELED' and services.annotations.load(fid)['revision']==0
    finally:
        a.dirty=False;a.save_error=False;a.debounce.stop();close_window(qtbot,w)
