from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox,QDialog,QFileDialog
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos

def test_project_camera_media_source_completion_and_independent_review(qtbot,services,media_project,monkeypatch):
    from tests.hotfix_helpers import review_gui
    project,mids,ids=media_project;w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('projects');h=w.p2.hotfix;panel=h.cameras
    qtbot.waitUntil(lambda:not h.camera_busy,timeout=10000);h.tabs.setCurrentIndex(1);panel.new();panel.fields['name'].setText('1204-1202给煤机摄像头');panel.fields['code'].setText('1204-1202');panel.fields['location'].setText('TEST FIXTURE')
    click(qtbot,panel,'project_camera_save');qtbot.waitUntil(lambda:len(services.cameras.list())==1 and not h.camera_busy and panel.isEnabled(),timeout=10000);cam=services.cameras.list()[0]
    assert panel.uuid.text()==cam['id']
    w.show_page('media');media=w.p2.media;qtbot.waitUntil(lambda:media.camera_choice.findData(cam['id'])>=0,timeout=10000);media.table.selectRow(0)
    qtbot.waitUntil(lambda:bool(media.selected_media),timeout=10000);mid=media.media_id
    media.camera_choice.setCurrentIndex(media.camera_choice.findData(cam['id']));monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes);click(qtbot,media,'media_camera_save')
    qtbot.waitUntil(lambda:services.media.get(mid)['camera_id']==cam['id'],timeout=10000);w.show_page('annotation');a=w.p2.annotation
    fid=next(f['id'] for f in services.media.frames() if f['media_id']==mid);a.request_load(fid,force=True);qtbot.waitUntil(lambda:not a.loading and a.frame_id==fid and not w.p2.refreshing,timeout=10000)
    w.p2.refresh();qtbot.waitUntil(lambda:not w.p2.refreshing,timeout=10000)
    item=next(a.frames.item(i) for i in range(a.frames.count()) if a.frames.item(i).data(Qt.ItemDataRole.UserRole)==fid)
    assert '1204-1202' in item.text() and services.media.get(mid)['name'] in item.toolTip()
    assert [a.review.itemText(i) for i in range(a.review.count())]==['未标注','已标注']
    a.image_tag.setCurrentIndex(1);a.auto_next.setChecked(False);click(qtbot,a,'annotation_quick_save');qtbot.waitUntil(lambda:not a.dirty and not a.saving,timeout=10000)
    assert services.annotations.load(fid)['completion_state']=='LABELED' and services.annotations.load(fid)['status']=='DRAFT'
    review_gui(qtbot,w,fid,'REVIEWED',monkeypatch);assert services.annotations.load(fid)['status']=='REVIEWED'
    # Already-reviewed content changes preserve the raw review result but require renewed review for new freezes.
    a.image_tag.setCurrentIndex(2);click(qtbot,a,'annotation_quick_save');qtbot.waitUntil(lambda:not a.saving and not a.dirty,timeout=10000)
    assert services.annotations.load(fid)['status']=='REVIEWED' and fid not in {f['id'] for f in services.datasets.candidates()}
    click(qtbot,a,'camera_go_media');assert w.stack.currentWidget() is media
    close_window(qtbot,w)

def test_gui_dependency_removal_hide_restore_and_doubleclick(qtbot,services,media_project,monkeypatch):
    project,_,_=media_project;w=make_window(qtbot,services);w.p2.set_project(project);w.show_page('media');media=w.p2.media;qtbot.waitUntil(lambda:media.table.rowCount()>0,timeout=10000)
    media.table.selectRow(0);qtbot.waitUntil(lambda:bool(media.selected_media),timeout=10000);mid=media.media_id;source=services.media.get(mid)['accessible_path']
    monkeypatch.setattr(QDialog,'exec',lambda *_:QDialog.DialogCode.Accepted);click(qtbot,media,'media_remove')
    qtbot.waitUntil(lambda:mid not in {r['id'] for r in media.media_rows},timeout=10000)
    from pathlib import Path
    assert Path(source).exists() and services.media.dependencies(mid)['has_dependencies']
    media.show_inactive.setChecked(True);qtbot.waitUntil(lambda:mid in {r['id'] for r in media.media_rows},timeout=10000)
    media.table.selectRow(next(i for i,r in enumerate(media.media_rows) if r['id']==mid));qtbot.waitUntil(lambda:media.media_id==mid,timeout=10000);click(qtbot,media,'media_restore')
    qtbot.waitUntil(lambda:not next(r for r in services.media.list(include_inactive=True) if r['id']==mid)['lifecycle'].get('hidden'),timeout=10000)
    w.show_page('projects');projects=w.pages['projects'];w.refresh();qtbot.waitUntil(lambda:projects.recent.rowCount()>0 and not w.refresh_busy,timeout=10000)
    projects.recent.cellDoubleClicked.emit(0,0);qtbot.waitUntil(lambda:not w.project_busy and w.p2.hotfix.tabs.currentIndex()==1,timeout=10000)
    assert w.p2.hotfix.cameras.project.text().find(project.id)>=0
    close_window(qtbot,w)

def test_gui_import_selects_only_current_available_camera(qtbot,services,tmp_path,sample_videos,monkeypatch):
    from PySide6.QtWidgets import QPushButton
    project=services.projects.create(str(tmp_path),'导入关联项目');cam=services.cameras.save('1204-1202给煤机摄像头',details={'code':'1204-1202','enabled':True});disabled=services.cameras.save('停用',details={'enabled':False})
    other=services.projects.create(str(tmp_path),'另一项目');foreign=services.cameras.save('其他项目摄像头');services.projects.open(project.root)
    w=make_window(qtbot,services);w.show_page('media');media=w.p2.media
    qtbot.waitUntil(lambda:media.camera.findData(cam['id'])>=0,timeout=10000)
    assert media.camera.findData(disabled['id'])<0 and media.camera.findData(foreign['id'])<0
    qtbot.mouseClick(next(b for b in media.findChildren(QPushButton) if b.text().startswith('导入信息')),Qt.MouseButton.LeftButton)
    media.camera.setCurrentIndex(media.camera.findData(cam['id']));monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *a,**k:([str(sample_videos/'sample.mp4')],''));click(qtbot,media,'import_media')
    qtbot.waitUntil(lambda:len(services.media.list())==1 and services.media.list()[0]['state']=='READY',timeout=10000)
    assert services.media.list()[0]['camera_id']==cam['id'];qtbot.waitUntil(lambda:not w.p2.tracked,timeout=10000)
    # Explicit COPY cleanup through the actual removal dialog; source is an owned synthetic fixture.
    from PySide6.QtWidgets import QCheckBox
    before=(sample_videos/'sample.mp4').read_bytes();mid=services.media.list()[0]['id'];copied=services.media.get(mid)['accessible_path']
    qtbot.waitUntil(lambda:media.table.rowCount()==1 and not w.p2.refreshing,timeout=10000);media.table.selectRow(0)
    qtbot.waitUntil(lambda:media.selected_media is not None,timeout=10000)
    def accept_cleanup(dialog):
        cleanup=next(c for c in dialog.findChildren(QCheckBox) if c.text().startswith('明确清理'));assert cleanup.isEnabled();cleanup.setChecked(True);return QDialog.DialogCode.Accepted
    monkeypatch.setattr(QDialog,'exec',accept_cleanup);click(qtbot,media,'media_remove');qtbot.waitUntil(lambda:not services.media.list(),timeout=10000)
    qtbot.waitUntil(lambda:not media.media_rows and not w.p2.refreshing,timeout=10000)
    from pathlib import Path
    assert not Path(copied).exists() and (sample_videos/'sample.mp4').read_bytes()==before
    close_window(qtbot,w)
