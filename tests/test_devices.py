from pathlib import Path
import os
from dataclasses import asdict
import json, time
import pytest
from ivad_app.core.contracts import AppError
from ivad_app.services.device_service import NvidiaWorker

@pytest.mark.hardware
def test_real_nvidia_worker_and_intel_not_validated(services):
    devices = services.devices.probe()
    nvidia = [d for d in devices if d.id.startswith('nvidia:') and d.status != 'Error']
    assert nvidia and nvidia[0].name == 'NVIDIA GeForce RTX 5070 Ti'
    assert nvidia[0].backend_available and nvidia[0].backend_validated
    assert nvidia[0].details['ort_available'] and nvidia[0].details['ort_validated']
    intel = next(d for d in devices if d.id.startswith('intel:'))
    assert not intel.backend_validated and intel.status == 'Not Tested'
    assert services.devices.require_gpu(nvidia[0].id).id == nvidia[0].id
    services.settings.save_preferences({'language': 'zh_CN', 'worker_python': '', 'preferred_gpu': nvidia[0].id})
    assert services.devices.require_gpu('').id == nvidia[0].id
    services.settings.save_preferences({'language': 'zh_CN', 'worker_python': '', 'preferred_gpu': 'nvidia:absent'})
    with pytest.raises(AppError): services.devices.require_gpu('')
    evidence = services.root / os.environ.get('IVAD_TEST_EVIDENCE_DIR','artifacts/p2/regression') / 'device-live.json'
    evidence.parent.mkdir(parents=True,exist_ok=True)
    evidence.write_text(json.dumps([asdict(d) for d in devices], ensure_ascii=False, indent=2), encoding='utf-8')

def test_missing_worker_gpu_rejection_and_no_cpu(services):
    services.settings.save_preferences({'language': 'zh_CN', 'worker_python': str(services.root / 'missing-worker.exe'), 'preferred_gpu': ''})
    devices = services.devices.probe()
    assert devices[0].status == 'Error' and not devices[0].backend_available
    for device_id in ['cpu', devices[0].id, 'unknown']:
        with pytest.raises(AppError): services.devices.require_gpu(device_id)

def test_evidence_absent_never_validated(tmp_path):
    worker = NvidiaWorker(tmp_path, tmp_path / 'python.exe')
    assert worker._validated({'torch': 'same'}, {'name': 'NVIDIA GeForce RTX 5070 Ti'}) is False

def test_registry_rejects_cpu_and_unregistered_intel():
    from ivad_app.compute.registry import WorkerRegistry
    registry = WorkerRegistry()
    with pytest.raises(AppError): registry.register('cpu', lambda: None)
    with pytest.raises(AppError): registry.create('intel_xpu')
