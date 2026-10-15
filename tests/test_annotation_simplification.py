import copy,json,os
from pathlib import Path
from uuid import uuid4
from PySide6.QtCore import Qt,QPointF
from PySide6.QtWidgets import QMessageBox,QInputDialog,QScrollArea
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context


def test_continuous_defaults_normal_camera_switch_multiclass_and_exclude(qtbot,services,media_project,monkeypatch):
    p,m,ids=media_project
    c1=services.cameras.save('8525压滤机',details={'code':'8525'});c2=services.cameras.save('1202-1204给煤机',details={'code':'12021204'})
    services.cameras.associate(m[0],c1['id'],None);services.cameras.associate(m[1],c2['id'],None)
    services.annotations.labels()
    l1=services.annotations.save_label({'name':'压滤板破裂'})['id'];l2=next(r['id'] for r in services.annotations.labels() if r['name']=='落料口堵煤')
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes);monkeypatch.setattr(QInputDialog,'getItem',lambda *a,**k:('严重模糊',True))
    def wait():qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and not a.saving and not a.dirty and not w.p2.refreshing and not a.batch_busy,timeout=10000)
    def rect(start,end):
        a.tool.setCurrentIndex(1);qtbot.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(*start)));qtbot.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(*end)));a.debounce.stop()
    def advance(name,old):click(qtbot,a,name);qtbot.waitUntil(lambda:a.frame_id!=old and not a.loading and not a.saving,timeout=10000);wait()
    try:
        wait();qtbot.waitUntil(lambda:a.camera_filter.findData(c1['id'])>=0,timeout=10000)
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c1['id']));wait();assert a.classes.currentData() is None
        assert not a.review.isVisible() and not a.image_label.isVisible()
        a.classes.setCurrentIndex(a.classes.findData(l1));first=a.frame_id;rect((10,10),(40,40));assert a.canvas.shapes[0]['label_id']==l1
        assert services.annotations.load(first)['revision']==0
        advance('annotation_abnormal_next',first);second=a.frame_id
        assert a.classes.currentData()==l1 and not a.canvas.shapes
        assert services.annotations.load(second)['revision']==0 and a.image_tag.currentData()=='UNKNOWN'
        rect((60,40),(110,80));advance('annotation_abnormal_next',second);normal=a.frame_id
        assert services.annotations.load(first)['payload']['objects'][0]['geometry']!=services.annotations.load(second)['payload']['objects'][0]['geometry']
        advance('annotation_normal_next',normal);multi=a.frame_id
        assert services.annotations.load(normal)['payload']['image_tag']=='NORMAL' and not services.annotations.load(normal)['payload']['objects'] and services.annotations.load(normal)['payload'].get('image_label_id') is None
        assert a.classes.currentData()==l1 and services.annotations.load(multi)['revision']==0
        rect((10,10),(40,40));a.classes.setCurrentIndex(a.classes.findData(l2));assert a.canvas.shapes[0]['label_id']==l1
        a.tool.setCurrentIndex(2)
        for point in [(100,40),(140,40),(140,80)]:qtbot.mouseClick(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=a.canvas.mapFromScene(QPointF(*point)))
        qtbot.mouseClick(a.canvas.viewport(),Qt.MouseButton.RightButton,pos=a.canvas.mapFromScene(QPointF(140,80)));a.debounce.stop()
        assert {o['label_id'] for o in a.canvas.shapes}=={l1,l2};advance('annotation_abnormal_next',multi)
        assert {o['label_id'] for o in services.annotations.load(multi)['payload']['objects']}=={l1,l2}
        a.classes.setCurrentIndex(a.classes.findData(l1));unprocessed=a.frame_id
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c2['id']));wait();assert a.classes.currentData() is None
        a.classes.setCurrentIndex(a.classes.findData(l2));other=a.frame_id;rect((10,10),(40,40));advance('annotation_abnormal_next',other);assert a.classes.currentData()==l2
        a.camera_filter.setCurrentIndex(a.camera_filter.findData(c1['id']));wait();a.request_load(unprocessed);wait()
        assert a.classes.currentData()==l1 and not a.canvas.shapes and a.image_tag.currentData()=='UNKNOWN'
        a.request_load(second);wait();before=copy.deepcopy(services.annotations.load(second)['payload']);advance('frame_exclude',second)
        assert services.annotations.load(second)['processing_state']=='EXCLUDED' and services.annotations.load(second)['payload']==before
        output=Path(os.environ.get('IVAD_SIMPLIFY_EVIDENCE',str(services.data_dir/'simplification-evidence')));output.mkdir(parents=True,exist_ok=True)
        w.resize(1920,1080)
        for scroll in a.findChildren(QScrollArea):scroll.verticalScrollBar().setValue(0)
        qtbot.wait(70);assert w.grab().save(str(output/'simplified-workbench.png'))
        a.request_load(multi);wait();assert {o['label_id'] for o in a.canvas.shapes}=={l1,l2}
        assert not a.review.isVisible() and not a.image_label.isVisible()
        for scroll in a.findChildren(QScrollArea):scroll.verticalScrollBar().setValue(0)
        qtbot.wait(50);assert w.grab().save(str(output/'multiclass-workbench.png'))
    finally:
        a.dirty=False;a.save_error=False;a.debounce.stop();close_window(qtbot,w)


def test_historical_objects_and_frame_details_do_not_follow_default(qtbot,services,media_project,monkeypatch):
    p,m,ids=media_project;s=services.annotations;labels=s.labels();l1,l2=labels[0]['id'],labels[1]['id']
    first=ids[0];second=ids[1];obj={'id':str(uuid4()),'kind':'box','label_id':l1,'geometry':[10,10,40,40]}
    s.save(first,{'image_tag':'ABNORMAL','objects':[obj],'image_label_id':l2},'REVIEWED',0)
    s.save(second,{'image_tag':'ABNORMAL','objects':[],'image_label_id':l2},'REVIEWED',0)
    frozen=services.datasets.freeze(Context(),{'root':p.root,'name':'historical native fixture','frame_ids':[first,second]});folder,_=services.datasets.snapshot(frozen['version_id']);before_manifest=(folder/'manifest.json').read_bytes()
    before=s.load(first);w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    def wait():qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and not a.saving and not a.dirty and not w.p2.refreshing,timeout=10000)
    try:
        wait();a.request_load(first);wait();assert a.classes.currentData() is None and a.image_label.currentData()==l2
        assert a.canvas.label_names[l1] in a.objects.item(0).text() and a.canvas.shapes[0]['label_id']==l1
        a.select_object(0);a.classes.setCurrentIndex(a.classes.findData(l2));assert not a.dirty and a.canvas.shapes[0]['label_id']==l1
        a.save_now();a.request_load(second);wait();assert s.load(first)['payload']==before['payload'] and s.load(first)['revision']==before['revision']
        assert a.image_label.currentData()==l2 and not a.canvas.shapes and a.review.currentData()=='LABELED'
        monkeypatch.setattr(QInputDialog,'getItem',lambda *args,**kwargs:(next(text for text in args[3] if l1 in text),True))
        click(qtbot,a,'annotation_frame_details');a.debounce.stop();assert s.load(second)['payload']['image_label_id']==l2
        click(qtbot,a,'save_annotation');wait();assert s.load(second)['payload']['image_label_id']==l1 and not s.load(second)['payload']['objects']
        assert s.load(second)['status']=='REVIEWED' and s.load(second)['frame']['handling']['review_stale']
        assert (folder/'manifest.json').read_bytes()==before_manifest
    finally:
        a.dirty=False;a.save_error=False;a.debounce.stop();close_window(qtbot,w)


def test_multiclass_yolo_negatives_and_classification_separation(services,media_project,tmp_path):
    p,m,ids=media_project;labels=services.annotations.labels();l1,l2=labels[0]['id'],labels[1]['id']
    objects=[{'id':str(uuid4()),'kind':'box','label_id':l1,'geometry':[10,10,40,40]},{'id':str(uuid4()),'kind':'polygon','label_id':l2,'geometry':[[100,40],[140,40],[140,80]]}]
    services.annotations.save(ids[0],{'image_tag':'ABNORMAL','objects':objects},'REVIEWED',0)
    services.annotations.save(ids[1],{'image_tag':'NORMAL','objects':[]},'REVIEWED',0)
    frozen=services.datasets.freeze(Context(),{'root':p.root,'name':'multiclass detection fixture','frame_ids':ids[:2]});folder,snapshot=services.datasets.snapshot(frozen['version_id']);before=(folder/'manifest.json').read_bytes()
    exported=services.datasets.export(Context(),{'root':p.root,'version_id':frozen['version_id'],'format':'yolo_detect','parent':str(tmp_path)});destination=Path(exported['path'])
    positive=next(destination.glob('labels/*/'+ids[0]+'.txt')).read_text();negative=next(destination.glob('labels/*/'+ids[1]+'.txt')).read_text()
    assert len(positive.splitlines())==2 and len({line.split()[0] for line in positive.splitlines()})==2 and negative==''
    services.annotations.save(ids[2],{'image_tag':'ABNORMAL','objects':[],'image_label_id':l1},'REVIEWED',0)
    classified=services.datasets.freeze(Context(),{'root':p.root,'name':'classification only fixture','frame_ids':[ids[0],ids[2]]})
    from ivad_app.core.contracts import AppError
    import pytest
    with pytest.raises(AppError):services.datasets.export(Context(),{'root':p.root,'version_id':classified['version_id'],'format':'yolo_detect','parent':str(tmp_path)})
    with pytest.raises(AppError):services.training.preflight(classified['version_id'],p.root)
    assert (folder/'manifest.json').read_bytes()==before


def test_unlinked_video_defaults_are_independent(qtbot,services,media_project):
    p,m,ids=media_project;labels=services.annotations.labels();l1,l2=labels[0]['id'],labels[1]['id']
    w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation;w.confirm_discard=lambda:True
    def wait():qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and not w.p2.refreshing,timeout=10000)
    try:
        wait();a.media_filter.setCurrentIndex(a.media_filter.findData(m[0]));wait();a.classes.setCurrentIndex(a.classes.findData(l1));first=a.frame_id
        a.media_filter.setCurrentIndex(a.media_filter.findData(m[1]));wait();assert a.classes.currentData() is None
        a.classes.setCurrentIndex(a.classes.findData(l2));second=a.frame_id
        a.media_filter.setCurrentIndex(a.media_filter.findData(m[0]));wait();assert a.classes.currentData()==l1
        assert not a.dirty and not a.canvas.shapes
        assert services.annotations.load(first)['revision']==services.annotations.load(second)['revision']==0
    finally:close_window(qtbot,w)
