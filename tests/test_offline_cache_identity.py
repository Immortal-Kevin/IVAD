import copy
from pathlib import Path
from tests.test_p3_training import freeze_valid
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from tests.test_p2_media import Context
from tests.test_gui import make_window,close_window

def test_cache_rejects_source_model_threshold_range_backend_and_version_changes(services,media_project,tmp_path,monkeypatch):
    p,vid=freeze_valid(services,media_project);_,snap=services.datasets.snapshot(vid);weight=tmp_path/'fixture.pt';weight.write_bytes(b'cache identity fixture; never deserialized')
    details=dict(model='yolo11n',task='detect',dataset_version=vid,class_map=snap['classes']);mid=services.models.register(weight,details,trusted=True);other=services.models.register(weight,details,trusted=True)
    payload=dict(root=p.root,media_id=snap['samples'][0]['media_id'],model_id=mid,device_id='nvidia:fixture',confidence=.25,start=0,end=.4,camera_id='camera-context')
    expected=services.offline.cache_identity(payload)
    for key,value in [('confidence',.35),('start',.04),('end',.44),('device_id','nvidia:other'),('camera_id','other'),('model_id',other)]:assert services.offline.cache_identity(dict(payload,**{key:value}))!=expected,key
    from ivad_app.services import offline_cache
    real_hash=offline_cache.file_hash;source=Path(services.media.get(payload['media_id'])['accessible_path'])
    for target in [source,services.root/'ivad_app/compute/offline_worker.py',services.root/'ivad_app/video/timestamps.py']:
        monkeypatch.setattr(offline_cache,'file_hash',lambda path,t=target:'0'*64 if Path(path)==t else real_hash(path));assert services.offline.cache_identity(payload)!=expected
    monkeypatch.setattr(offline_cache,'file_hash',real_hash)
    assert services.offline.matching_cache(payload) is None and not services.models.camera_configurations()

def test_unlinked_camera_confirmation_never_changes_media_owner(qtbot,services,media_project,tmp_path,sample_videos,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    p,vid=freeze_valid(services,media_project);_,snap=services.datasets.snapshot(vid);weight=tmp_path/'fixture.pt';weight.write_bytes(b'GUI-only fixture never loaded');services.models.register(weight,dict(model='yolo11n',task='detect',dataset_version=vid,class_map=snap['classes']),trusted=True)
    cam=services.cameras.save('演示摄像头',mode='CREATE');mid=services.media.import_batch(Context(),dict(root=p.root,paths=[str(sample_videos/'rotation.mp4')],mode='COPY'))['imported'][0]
    w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');page=w.pages['offline']
    try:
        qtbot.waitUntil(lambda:not page.busy and page.media.findData(mid)>=0,timeout=10000);page.media.setCurrentIndex(page.media.findData(mid));qtbot.waitUntil(lambda:page.preview.last_image is not None,timeout=10000)
        page.camera.setCurrentIndex(page.camera.findData(cam['id']));page.other_models.setChecked(True);page.gpu.addItem('TEST backend, not hardware measurement','nvidia:fixture')
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.No);assert page.inference_payload() is None
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes);value=page.inference_payload();assert value['camera_id']==cam['id'] and services.media.get(mid)['camera_id'] is None
        assert not services.jobs.history() and not services.models.camera_configurations()
    finally:close_window(qtbot,w)
