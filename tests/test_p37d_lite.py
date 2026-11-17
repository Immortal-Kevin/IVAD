"""Lite capability boundary; software tests do not replace frozen EXE tests."""
from pathlib import Path
import sys
import pytest
from ivad_app.core.application import ApplicationServices
from ivad_app.core.contracts import AppError


def test_lite_denies_backend_bypass_without_creating_jobs(tmp_path, monkeypatch):
    monkeypatch.setenv('IVAD_P37D_LITE', '1')
    services = ApplicationServices(Path(__file__).resolve().parents[1], tmp_path/'app', lite=False)
    try:
        assert services.demo_lite and services.lite
        project = services.projects.create(str(tmp_path), 'Synthetic blank')
        assert services.cameras.list()==[] and services.media.list()==[]
        assert services.annotations.labels()==[] and services.datasets.versions()==[]
        calls = [lambda:services.jobs.submit('p3_train',project.id,{'model':'rfdetr-nano'}),
                 lambda:services.jobs.submit('p3_validate',project.id,{}),
                 lambda:services.jobs.submit('p35_offline',project.id,{}),
                 lambda:services.jobs.submit('p2_clip',project.id,{}),
                 lambda:services.jobs.register('p3_train',lambda *_:None),
                 lambda:services.jobs.register('p2_clip',lambda *_:None),
                 lambda:services.media.save_video_clip(None,{}),
                 lambda:services.training.configuration_preflight({}),
                 lambda:services.offline.load('ignored'),
                 lambda:services.models.register('ignored',{})]
        for call in calls:
            with pytest.raises(AppError) as caught:call()
            assert caught.value.code=='DEMO_FEATURE_DISABLED'
        assert services.jobs.history()==[]
        assert set(services.jobs.handlers)=={'p2_import','p2_extract','p2_freeze','p2_export'}
    finally:services.close()


def test_frozen_profile_cannot_be_disabled_by_environment(tmp_path,monkeypatch):
    from ivad_app.core.demo_policy import enabled,require
    monkeypatch.setattr(sys,'frozen',True,raising=False)
    monkeypatch.setattr(sys,'_MEIPASS',str(tmp_path),raising=False)
    (tmp_path/'p37d-lite-profile.json').write_text('{}',encoding='utf8')
    monkeypatch.setenv('IVAD_P37D_LITE','0')
    assert enabled()
    with pytest.raises(AppError):require('ai')


def test_source_training_entry_cannot_launch_worker_under_lite(monkeypatch):
    monkeypatch.setenv('IVAD_P37D_LITE','1')
    from ivad_app.services.rfdetr_training_service import RFDETRTrainingService
    from ivad_app.services.training_service import TrainingService
    rf=RFDETRTrainingService(*([None]*5),Path.cwd(),None)
    with pytest.raises(AppError) as caught:rf.python()
    assert caught.value.code=='DEMO_FEATURE_DISABLED'
    old=TrainingService(*([None]*5),Path.cwd(),None)
    with pytest.raises(AppError) as caught:old.configuration_preflight({})
    assert caught.value.code=='DEMO_FEATURE_DISABLED'
