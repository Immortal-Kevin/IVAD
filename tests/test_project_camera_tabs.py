import os
import json
from pathlib import Path
from PySide6.QtCore import Qt, QPoint
from PySide6.QtWidgets import QPushButton, QFileDialog
from tests.test_gui import make_window, close_window
from tests.test_p2_gui import click


def test_project_camera_tabs_context_and_geometry(qtbot, services, tmp_path, monkeypatch):
    w=make_window(qtbot,services);w.resize(1920,1080);w.show_page('projects')
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    w.confirm_discard=lambda:True
    try:
        _verify(qtbot,services,tmp_path,w)
    finally:
        close_window(qtbot,w)

def _verify(qtbot,services,tmp_path,w):
    page=w.pages['projects'];h=w.p2.hotfix;panel=h.cameras
    assert [page.tabs.tabText(i) for i in range(2)]==['项目管理','摄像头管理']
    assert page.tabs.currentIndex()==0
    assert page.tabs.widget(0).isAncestorOf(page.name)
    assert page.tabs.widget(1).isAncestorOf(panel)
    page.tabs.setCurrentIndex(1);qtbot.wait(40)
    assert not page.name.isVisible() and panel.isVisible()
    assert '请先打开项目' in panel.project.text()
    assert not panel.findChild(QPushButton,'project_camera_save').isEnabled()
    assert not panel.findChild(QPushButton,'project_camera_new').isEnabled()
    page.tabs.setCurrentIndex(0);page.name.setText('布局验证项目')
    click(qtbot,page,'create_project');qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    p=services.projects.current;page.tabs.setCurrentIndex(1)
    qtbot.waitUntil(lambda:not h.camera_busy,timeout=10000)
    panel.fields['name'].setText('回归测试摄像头');panel.fields['code'].setText('TEST-01')
    click(qtbot,panel,'project_camera_save')
    qtbot.waitUntil(lambda:len(services.cameras.list())==1 and not h.camera_busy and panel.isEnabled(),timeout=10000)
    cid=services.cameras.list()[0]['id']
    qtbot.waitUntil(lambda:not w.p2.refreshing and not h.camera_busy,timeout=10000)
    qtbot.mouseClick(panel.enabled,Qt.MouseButton.LeftButton,pos=QPoint(10,panel.enabled.height()//2));assert not panel.enabled.isChecked()
    click(qtbot,panel,'project_camera_save')
    qtbot.waitUntil(lambda:not panel.dirty and panel.isEnabled() and not h.camera_busy,timeout=10000)
    assert not services.cameras.list()[0]['details']['enabled']
    w.open_project(p.root);qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    qtbot.waitUntil(lambda:not h.camera_busy,timeout=10000)
    assert panel.rows[0]['id']==cid
    page.tabs.setCurrentIndex(0);page.name.setText('未保存项目名称');page.site.setText('未保存厂区');page.description.setPlainText('未保存描述')
    for _ in range(3):
        page.tabs.setCurrentIndex(1);assert not page.name.isVisible()
        page.tabs.setCurrentIndex(0);assert not panel.isVisible()
    assert page.name.text()=='未保存项目名称' and page.site.text()=='未保存厂区' and page.description.toPlainText()=='未保存描述'
    evidence=Path(os.environ.get('IVAD_TAB_EVIDENCE','artifacts/p2-project-camera-tabs-20261015'))
    evidence.mkdir(parents=True,exist_ok=True);qtbot.wait(100)
    suffix=os.environ.get('QT_SCALE_FACTOR','native')
    assert w.devicePixelRatioF()==float(suffix)
    assert w.grab().save(str(evidence/f'project-tab-{suffix}.png'))
    click(qtbot,page,'save_project');qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    click(qtbot,page,'project_camera_details');qtbot.wait(100)
    assert page.tabs.currentIndex()==1
    page.camera_scroll.verticalScrollBar().setValue(0);qtbot.wait(40)
    assert w.grab().save(str(evidence/f'camera-tab-{suffix}.png'))
    w.workspace.showPopup();qtbot.wait(50)
    assert w.workspace.view().palette().base().color().lightness()>180
    assert w.workspace.view().grab().save(str(evidence/f'combo-popup-{suffix}.png'))
    w.workspace.hidePopup()
    (evidence/f'geometry-{suffix}.json').write_text(json.dumps({'logical_window':[w.width(),w.height()], 'device_pixel_ratio':w.devicePixelRatioF(), 'capture_pixels':[w.grab().width(),w.grab().height()], 'camera_scroll_max':page.camera_scroll.verticalScrollBar().maximum(), 'camera_id':cid},ensure_ascii=False,indent=2),encoding='utf-8')
    assert panel.fields['name'].palette().color(panel.fields['name'].backgroundRole()).lightness()>180
    w.create_project(str(tmp_path),'另一验证项目','','');qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    assert panel.rows==[] and panel.table.rowCount()==0
    qtbot.waitUntil(lambda:not h.camera_busy,timeout=10000)
    assert panel.rows==[] and panel.table.rowCount()==0
    w.open_project(p.root);qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    qtbot.waitUntil(lambda:not h.camera_busy,timeout=10000);assert panel.rows[0]['id']==cid
    w.close_project();qtbot.waitUntil(lambda:not w.project_busy,timeout=10000)
    assert panel.rows==[] and panel.table.rowCount()==0
