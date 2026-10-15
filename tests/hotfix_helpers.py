from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from tests.test_p2_gui import click

def review_gui(qtbot,w,frame_id,status,monkeypatch):
    a=w.p2.annotation;current=a.frame_id
    qtbot.waitUntil(lambda:not a.dirty and not a.saving and not a.loading,timeout=10000)
    h=w.p2.hotfix;w.p2.refresh();w.show_page('dataset')
    qtbot.waitUntil(lambda:not w.p2.refreshing and any(f['id']==frame_id for f in h.review_rows),timeout=10000)
    for i,row in enumerate(h.review_rows):h.review_table.item(i,0).setCheckState(Qt.CheckState.Checked if row['id']==frame_id else Qt.CheckState.Unchecked)
    h.review_status.setCurrentIndex(h.review_status.findData(status));monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    click(qtbot,w.p2.dataset,'dataset_review_submit')
    qtbot.waitUntil(lambda:w.s.annotations.load(frame_id)['status']==status and not w.s.annotations.frames_status()[frame_id]['review_stale'],timeout=10000)
    w.show_page('annotation');a.request_load(current,force=True);qtbot.waitUntil(lambda:not a.loading,timeout=10000)
