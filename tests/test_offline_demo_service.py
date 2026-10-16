import json
import pytest
from ivad_app.core.contracts import AppError
from ivad_app.services.offline_demo_service import OfflineDemoService

@pytest.mark.parametrize('boxes',[[[-1,0,5,5,.5,0]],[[0,0,100,5,.5,0]],[[0,0,5,5,1.1,0]],[[0,0,5,5,.5,1]],[[0,0,0,5,.5,0]],[[0,0,5,5,float('nan'),0]],[[0,0,5]]])
def test_invalid_output_rejected(boxes):
    with pytest.raises(AppError):OfflineDemoService.validate_boxes(boxes,20,20,1)

def test_valid_original_coordinates_and_empty():
    OfflineDemoService.validate_boxes([],1280,720,1);OfflineDemoService.validate_boxes([[600,100,1000,600,.75,0]],1280,720,1)

def test_incomplete_cache_never_accepted(services,tmp_path):
    (tmp_path/'manifest.json').write_text(json.dumps(dict(state='CANCELLED')),encoding='utf8')
    with pytest.raises(AppError):services.offline.load(tmp_path)

def test_offline_job_registered_without_production_model_change(services,tmp_path):
    p=services.projects.create(str(tmp_path),'P35 isolated fixture')
    assert 'p35_offline' in services.jobs.handlers and not services.models.camera_configurations()
    assert not services.training.runs() and not services.models.versions()

def test_invalid_confidence_rejected_before_gpu(services):
    with pytest.raises(AppError,match='置信度'):services.offline.run(None,dict(root='unused',media_id='unused',model_id='unused',confidence=0))

def test_cpu_demo_rejected(services,monkeypatch):
    from types import SimpleNamespace
    monkeypatch.setattr(services.devices,'require_gpu',lambda *_:SimpleNamespace(id='cpu'))
    with pytest.raises(AppError,match='NVIDIA'):services.offline.run(None,dict(root='unused',media_id='unused',model_id='unused',device_id='cpu'))
