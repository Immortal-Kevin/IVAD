import json
from pathlib import Path
from PySide6.QtCore import Qt, QPointF
from PySide6.QtWidgets import QFileDialog, QMessageBox, QPushButton, QScrollArea
from tests.test_gui import make_window, close_window
from tests.test_p2_media import sample_videos
from ivad_app.gui.label_dialog import LabelDialog

def click(qtbot,parent,name):
    widget=parent.findChild(QPushButton,name);assert widget is not None
    ancestor=widget.parentWidget()
    while ancestor:
        if isinstance(ancestor,QScrollArea):ancestor.ensureWidgetVisible(widget);qtbot.wait(20);break
        ancestor=ancestor.parentWidget()
    qtbot.mouseClick(widget,Qt.MouseButton.LeftButton)

def test_gui_import_play_extract_annotate_freeze_export_reopen(qtbot,services,tmp_path,sample_videos,monkeypatch):
    window=make_window(qtbot,services)
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    window.create_project(str(tmp_path),'GUI P2全流程','','')
    qtbot.waitUntil(lambda:not window.project_busy and not window.p2.refreshing,timeout=10000)
    root=services.projects.current.root
    window.show_page('media');media=window.p2.media
    paths=[str(sample_videos/name) for name in ['sample.mp4','sample.mov','sample.mkv']]
    monkeypatch.setattr(QFileDialog,'getOpenFileNames',lambda *a,**k:(paths,''))
    click(qtbot,media,'import_media')
    qtbot.waitUntil(lambda:len(media.media_rows)==3,timeout=20000)
    assert all(row['state']=='READY' and row['mode']=='COPY' for row in media.media_rows)
    for index in range(3):
        media.table.selectRow(index)
        qtbot.waitUntil(lambda:media.player.last_image is not None,timeout=10000)
        if index==0:
            player=media.player
            click(qtbot,player,'video_next');qtbot.waitUntil(lambda:player.position_us>0,timeout=5000)
            click(qtbot,player,'video_previous');qtbot.waitUntil(lambda:player.position_us==0,timeout=5000)
            player.goto.setValue(.5);qtbot.mouseClick(player.goto_button,Qt.MouseButton.LeftButton)
            qtbot.waitUntil(lambda:player.position_us>=500000,timeout=5000)
            player.speed.setCurrentIndex(3);click(qtbot,player,'video_play')
            qtbot.waitUntil(lambda:player.position_us>700000,timeout=5000)
            click(qtbot,player,'video_play');assert not player.playing
            click(qtbot,player,'capture_frame')
            qtbot.waitUntil(lambda:len(services.media.frames(root))>=1,timeout=5000)
        media.tabs.setCurrentIndex(1);media.maximum.setValue(1);media.start.setValue(0);media.end.setValue(.2)
        before=len(services.media.frames(root));click(qtbot,media,'extract_frames')
        qtbot.waitUntil(lambda:len(services.media.frames(root))>before,timeout=15000)
        qtbot.waitUntil(lambda:not window.p2.tracked and not window.p2.refreshing,timeout=15000)
    window.show_page('annotation');ann=window.p2.annotation
    qtbot.waitUntil(lambda:ann.frame_id is not None and not ann.loading,timeout=5000)
    # Real dialog and mouse edits; no generated detector output enters truth.
    dialog=LabelDialog(services.annotations,window.runner,root,window.p2.refresh,window)
    qtbot.addWidget(dialog);dialog.show();qtbot.waitUntil(lambda:len(dialog.records)>=5,timeout=5000)
    dialog.name.setText('GUI人工多边形类别');dialog.kind.setCurrentIndex(1);click(qtbot,dialog,'save_label')
    qtbot.waitUntil(lambda:any(r['name']=='GUI人工多边形类别' for r in dialog.records),timeout=5000)
    label_id=next(r['id'] for r in dialog.records if r['name']=='GUI人工多边形类别');dialog.accept()
    qtbot.waitUntil(lambda:ann.classes.findData(label_id)>=0,timeout=5000)
    selected=[]
    for media_row in media.media_rows:
        frame=next(f for f in services.media.frames(root) if f['media_id']==media_row['id'] and f['time_us']==0)
        row=next(i for i in range(ann.frames.count()) if ann.frames.item(i).data(Qt.ItemDataRole.UserRole)==frame['id'])
        ann.frames.setCurrentRow(row)
        qtbot.waitUntil(lambda:ann.frame_id==frame['id'] and not ann.loading,timeout=5000)
        ann.classes.setCurrentIndex(ann.classes.findData(label_id));ann.tool.setCurrentIndex(2)
        for x,y in [(20,20),(100,20),(90,90),(20,80)]:
            qtbot.mouseClick(ann.canvas.viewport(),Qt.MouseButton.LeftButton,pos=ann.canvas.mapFromScene(QPointF(x,y)))
        qtbot.keyClick(ann.canvas,Qt.Key.Key_Return)
        assert len(ann.canvas.shapes)==1
        ann.review.setCurrentText('APPROVED');ann.image_tag.setCurrentIndex(2)
        qtbot.waitUntil(lambda:ann.revision>0 and not ann.dirty and not ann.saving,timeout=10000)
        assert services.annotations.load(frame['id'],root)['payload']['objects'][0]['source']=='Human Generated'
        selected.append(frame['id'])
    evidence=services.root/'artifacts/p2/gui';evidence.mkdir(parents=True,exist_ok=True)
    window.grab().save(str(evidence/'annotation.png'))
    window.show_page('dataset');dataset=window.p2.dataset
    qtbot.waitUntil(lambda:dataset.candidates.rowCount()==3,timeout=10000)
    cell=dataset.candidates.visualItemRect(dataset.candidates.item(0,0))
    from PySide6.QtCore import QPoint
    qtbot.mouseClick(dataset.candidates.viewport(),Qt.MouseButton.LeftButton,pos=QPoint(cell.left()+10,cell.center().y()))
    assert dataset.candidates.item(0,0).checkState()==Qt.CheckState.Checked
    dataset.select_all();dataset.name.setText('GUI完整分割数据集');click(qtbot,dataset,'freeze_dataset')
    qtbot.waitUntil(lambda:dataset.versions.rowCount()==1,timeout=20000)
    assert all(v>0 for v in dataset.version_rows[0]['summary']['splits'].values())
    dataset.versions.selectRow(0);dataset.format.setCurrentIndex(1)
    monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
    click(qtbot,dataset,'export_dataset')
    qtbot.waitUntil(lambda:bool(list(tmp_path.glob('IVAD-*/export_manifest.json'))),timeout=15000)
    qtbot.waitUntil(lambda:not window.p2.tracked,timeout=15000)
    exported=next(tmp_path.glob('IVAD-*/ivad_native.json'))
    assert len(json.loads(exported.read_text(encoding='utf-8'))['samples'])==3
    window.grab().save(str(evidence/'dataset.png'))
    close_window(qtbot,window)
    # New services and new main window read committed project state.
    from ivad_app.core.application import ApplicationServices
    reopened=ApplicationServices(services.root,tmp_path/'reopen-application',step_seconds=.01)
    reopened.projects.open(root);second=make_window(qtbot,reopened);second.p2.set_project(reopened.projects.current)
    qtbot.waitUntil(lambda:len(second.p2.dataset.version_rows)==1,timeout=10000)
    assert len(reopened.datasets.candidates(root))==3
    close_window(qtbot,second);reopened.close()
