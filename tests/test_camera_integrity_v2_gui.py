from pathlib import Path
from PySide6.QtWidgets import QMessageBox
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from ivad_app.core.application import ApplicationServices


def test_gui_create_from_selected_refresh_guard_and_restart(qtbot,services,tmp_path,monkeypatch):
    p=services.projects.create(str(tmp_path),'摄像头持久化测试');w=make_window(qtbot,services)
    w.show_page('projects');h=w.p2.hotfix;panel=h.cameras;h.tabs.setCurrentIndex(1)
    w.confirm_discard=lambda:True
    def settled():qtbot.waitUntil(lambda:not h.camera_busy and not w.p2.refreshing and panel.isEnabled(),timeout=10000)
    def save():
        click(qtbot,panel,'project_camera_save');qtbot.waitUntil(lambda:not panel.dirty and panel.isEnabled(),timeout=10000);settled()
    try:
        settled();panel.fields['code'].setText('8525');panel.fields['name'].setText('8525压滤机');save()
        a=panel.record.copy();assert panel.mode=='EDIT'
        click(qtbot,panel,'project_camera_new')
        assert panel.mode=='CREATE' and panel.record is None and not panel.table.selectedItems()
        panel.fields['code'].setText('12021204');panel.fields['name'].setText('1202-1204给煤机')
        h.refresh_cameras();settled()
        assert panel.record is None and panel.mode=='CREATE' and panel.fields['code'].text()=='12021204'
        save();b=panel.record.copy();assert a['id']!=b['id'] and len(panel.rows)==2
        assert next(r for r in services.cameras.list() if r['id']==a['id'])==a
        click(qtbot,panel,'project_camera_new');panel.fields['code'].setText('8525');panel.fields['name'].setText('禁止重复')
        click(qtbot,panel,'project_camera_save');qtbot.waitUntil(lambda:panel.isEnabled() and '已存在' in panel.info.text(),timeout=10000)
        assert panel.mode=='CREATE' and panel.dirty and len(services.cameras.list())==2
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Discard)
        row_a=next(i for i,r in enumerate(panel.rows) if r['id']==a['id']);panel.table.selectRow(row_a)
        assert panel.record['id']==a['id'];panel.fields['name'].setText('8525压滤机 · 编辑测试');save()
        assert panel.record['id']==a['id'] and len(panel.rows)==2
        panel.fields['location'].setText('尚未保存')
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel)
        click(qtbot,panel,'project_camera_new');assert panel.mode=='EDIT' and panel.fields['location'].text()=='尚未保存'
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Save)
        click(qtbot,panel,'project_camera_new');qtbot.waitUntil(lambda:panel.mode=='CREATE' and panel.isEnabled(),timeout=10000);settled()
        assert next(r for r in services.cameras.list() if r['id']==a['id'])['details']['location']=='尚未保存'
        panel.fields['code'].setText('重复输入');panel.fields['name'].setText('待放弃')
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Discard)
        panel.table.selectRow(next(i for i,r in enumerate(panel.rows) if r['id']==b['id']))
        assert panel.mode=='EDIT' and panel.record['id']==b['id']
        evidence=Path('artifacts/camera-integrity-v2-20261015');evidence.mkdir(exist_ok=True,parents=True)
        w.resize(1920,1080);qtbot.wait(100);assert w.grab().save(str(evidence/'two-cameras-edit.png'))
        click(qtbot,panel,'project_camera_new');qtbot.wait(50);assert w.grab().save(str(evidence/'create-mode.png'))
        ids={r['id'] for r in services.cameras.list()}
    finally:close_window(qtbot,w)
    restarted=ApplicationServices(services.root,services.data_dir,step_seconds=.01)
    restarted.projects.open(p.root);w2=make_window(qtbot,restarted)
    try:
        w2.show_page('projects');h2=w2.p2.hotfix;h2.tabs.setCurrentIndex(1)
        qtbot.waitUntil(lambda:not h2.camera_busy and len(h2.cameras.rows)==2,timeout=10000)
        assert {r['id'] for r in h2.cameras.rows}==ids
        assert next(r for r in h2.cameras.rows if r['id']==a['id'])['details']['location']=='尚未保存'
    finally:close_window(qtbot,w2)
