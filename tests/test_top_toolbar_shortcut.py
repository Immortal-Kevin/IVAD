import os,threading,copy,json
from pathlib import Path
from PySide6.QtCore import Qt,QPoint,QRect
from PySide6.QtWidgets import QPushButton,QScrollArea,QMessageBox,QBoxLayout
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from ivad_app.core.contracts import AppError


def ready(qtbot,w):
    a=w.p2.annotation
    qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and not a.saving and not a.dirty and not a.shortcut_busy and not w.p2.refreshing,timeout=10000)


def test_toolbar_visible_responsive_and_not_duplicated(qtbot,services,media_project):
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation
    try:
        ready(qtbot,w);output=Path(os.environ.get('IVAD_TOP_EVIDENCE',str(services.data_dir/'top-evidence')));output.mkdir(parents=True,exist_ok=True)
        geometries=[]
        for width,height in [(1920,1080),(1280,800),(1040,720)]:
            w.resize(width,height);qtbot.wait(70)
            props=next(scroll for scroll in a.findChildren(QScrollArea) if scroll.widget().objectName()=='annotation_properties')
            props.verticalScrollBar().setValue(props.verticalScrollBar().maximum());qtbot.wait(30)
            for button in [a.normal_button,a.abnormal_button]:
                assert a.top_actions.isAncestorOf(button) and button.isVisible() and not props.isAncestorOf(button)
                assert button.width()>=button.fontMetrics().horizontalAdvance(button.text())
                assert a.rect().contains(QRect(button.mapTo(a,QPoint(0,0)),button.size()))
                assert len([b for b in a.findChildren(QPushButton) if b.text()==button.text()])==1
            assert a.normal_button.mapTo(a,QPoint(0,0)).y()==a.abnormal_button.mapTo(a,QPoint(0,0)).y()
            rects=[QRect(b.mapTo(a,QPoint(0,0)),b.size()) for b in a.top_toolbar.findChildren(QPushButton) if b.isVisible()]
            assert all(not rect.intersects(other) for i,rect in enumerate(rects) for other in rects[i+1:])
            geometries.append({'requested':[width,height],'actual':[w.width(),w.height()],'dpr':w.devicePixelRatioF(),'wrapped':a.top_layout.direction()==QBoxLayout.Direction.TopToBottom,'top_height':a.top_toolbar.height()})
            assert w.grab().save(str(output/f'top-toolbar-{width}.png'))
        if w.devicePixelRatioF()==1:assert geometries[0]['wrapped'] is False and geometries[-1]['wrapped'] is True
        (output/'geometry.json').write_text(json.dumps(geometries,indent=2),encoding='utf-8')
    finally:close_window(qtbot,w)


def test_normal_conflict_double_click_failure_and_last(qtbot,services,media_project,monkeypatch):
    p,m,ids=media_project;s=services.annotations;label=s.labels()[0]['id'];first=ids[0]
    box={'id':first,'kind':'box','geometry':[10,10,40,40],'label_id':label}
    s.save(first,{'image_tag':'ABNORMAL','objects':[box]},'REVIEWED',0)
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    try:
        ready(qtbot,w);a.request_load(first);ready(qtbot,w);a.image_tag.setCurrentIndex(2)
        before=copy.deepcopy(s.load(first));monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:QMessageBox.StandardButton.No)
        click(qtbot,a,'annotation_normal_next');qtbot.waitUntil(lambda:not a.shortcut_busy,timeout=3000)
        assert a.frame_id==first and s.load(first)['payload']==before['payload']
        monkeypatch.setattr(QMessageBox,'question',lambda *args,**kwargs:QMessageBox.StandardButton.Yes)
        original=s.save;entered=threading.Event();release=threading.Event()
        def slow(*args,**kwargs):entered.set();release.wait(5);return original(*args,**kwargs)
        monkeypatch.setattr(s,'save',slow)
        click(qtbot,a,'annotation_normal_next');qtbot.waitUntil(entered.is_set,timeout=5000)
        assert not a.normal_button.isEnabled() and not a.abnormal_button.isEnabled()
        qtbot.mouseDClick(a.normal_button,Qt.MouseButton.LeftButton);a.trigger_top_shortcut('normal')
        release.set();ready(qtbot,w)
        assert s.load(first)['payload']['image_tag']=='NORMAL' and not s.load(first)['payload']['objects'] and s.load(first)['revision']==2
        assert a.frame_id==ids[1] and len(s.revisions(first))==2
        # Simulate failure before commit; no next-frame action may run.
        current=a.frame_id
        def fail(*args,**kwargs):raise AppError('TEST_FIXTURE','模拟保存失败')
        monkeypatch.setattr(s,'save',fail);click(qtbot,a,'annotation_normal_next')
        qtbot.waitUntil(lambda:a.save_error and not a.saving and not a.shortcut_busy,timeout=5000)
        assert a.frame_id==current and s.load(current)['revision']==0
        monkeypatch.setattr(s,'save',original);a.dirty=False;a.save_error=False;a.pending=None;a.debounce.stop();a.request_load(current,force=True);ready(qtbot,w)
        last=a.frames.item(a.frames.count()-1).data(Qt.ItemDataRole.UserRole);a.request_load(last);ready(qtbot,w)
        click(qtbot,a,'annotation_normal_next');ready(qtbot,w)
        assert a.frame_id==last and '最后一张' in a.info.text() and s.load(last)['completion_state']=='LABELED'
    finally:
        a.dirty=False;a.save_error=False;a.pending=None;a.debounce.stop();close_window(qtbot,w)


def test_abnormal_overrides_mode_preserves_default_and_skips_excluded(qtbot,services,media_project):
    p,m,ids=media_project;s=services.annotations;label=s.labels()[0]['id']
    s.batch_apply(s.batch_preview([ids[1]],'exclude'),'测试夹具')
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation
    try:
        ready(qtbot,w);a.state_filter.setCurrentIndex(a.state_filter.findData('ALL'));ready(qtbot,w);a.request_load(ids[0]);ready(qtbot,w)
        a.classes.setCurrentIndex(a.classes.findData(label));a.canvas.add('box',[10,10,40,40]);a.debounce.stop()
        # Retain valid unsaved objects while forcing a different displayed mode.
        a.image_tag.blockSignals(True);a.image_tag.setCurrentIndex(a.image_tag.findData('NORMAL'));a.image_tag.blockSignals(False)
        click(qtbot,a,'annotation_abnormal_next');ready(qtbot,w)
        assert a.frame_id==ids[2] and a.classes.currentData()==label
        saved=s.load(ids[0]);assert saved['payload']['image_tag']=='ABNORMAL' and saved['payload']['objects'][0]['label_id']==label and saved['completion_state']=='LABELED'
        assert a.image_tag.currentData()=='UNKNOWN' and not a.canvas.shapes
    finally:close_window(qtbot,w)


def test_invalid_category_and_frame_classification_no_fake_boxes(qtbot,services,media_project):
    p,m,ids=media_project;s=services.annotations;label=s.labels()[0]['id']
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    try:
        ready(qtbot,w);first=a.frame_id;a.canvas.label_id='missing-category';a.canvas.add('box',[10,10,40,40]);a.debounce.stop()
        click(qtbot,a,'annotation_abnormal_next');qtbot.waitUntil(lambda:a.save_error and not a.saving and not a.shortcut_busy,timeout=5000)
        assert a.frame_id==first and s.load(first)['revision']==0
        a.dirty=False;a.save_error=False;a.pending=None;a.debounce.stop()
        s.save(first,{'image_tag':'ABNORMAL','objects':[],'image_label_id':label},None,0)
        a.request_load(first,force=True);ready(qtbot,w);click(qtbot,a,'annotation_abnormal_next');ready(qtbot,w)
        assert a.frame_id!=first and not s.load(first)['payload']['objects'] and s.load(first)['payload']['image_label_id']==label and s.load(first)['completion_state']=='LABELED'
    finally:
        a.dirty=False;a.save_error=False;a.pending=None;a.debounce.stop();close_window(qtbot,w)
