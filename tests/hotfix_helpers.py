from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from tests.test_p2_gui import click

def review_fixture(qtbot,w,frame_id,status,monkeypatch):
    """Legacy review-policy fixture. The duplicate review GUI was intentionally removed."""
    a=w.p2.annotation;current=a.frame_id
    qtbot.waitUntil(lambda:not a.dirty and not a.saving and not a.loading,timeout=10000)
    revision=w.s.annotations.load(frame_id)['revision']
    w.s.annotations.review_frames({frame_id:revision},status)
    w.p2.refresh();qtbot.waitUntil(lambda:not w.p2.refreshing,timeout=10000)
    w.show_page('annotation');a.request_load(current,force=True);qtbot.waitUntil(lambda:not a.loading,timeout=10000)
