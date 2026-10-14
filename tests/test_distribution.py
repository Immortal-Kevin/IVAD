import json,zipfile,sys
import pytest
from ivad_app.core.application import ApplicationServices
from ivad_app.core.contracts import AppError,DeviceInfo
from ivad_app.services.device_service import NvidiaWorker
from ivad_app.services.diagnostic_export import export_diagnostics

def test_lite_does_not_start_worker_and_never_allows_ai(tmp_path,monkeypatch):
    services=ApplicationServices(tmp_path,tmp_path/'app',lite=True)
    monkeypatch.setattr(NvidiaWorker,'probe',lambda _:pytest.fail('Lite must not execute CUDA worker'))
    monkeypatch.setattr(services.devices,'_hardware_only',lambda _:[])
    services.devices.probe()
    for selected in ['cpu','nvidia:dummy','']:
        with pytest.raises(AppError,match='禁止'):services.devices.require_gpu(selected)
    assert 'torch' not in sys.modules and 'onnxruntime' not in sys.modules
    services.close()

def test_diagnostic_zip_only_allowlists_metadata(tmp_path):
    services=ApplicationServices(tmp_path,tmp_path/'app',lite=True)
    services.logs.write('media','password="hidden" token=hidden Bearer hidden path C:\\Users\\private\\video.mp4',level='ERROR')
    services.devices.devices=[DeviceInfo('nvidia:private','GPU example','CUDA',True,False,False,'Worker Not Installed',{'driver':'617.42','uuid':'private'})]
    result=export_diagnostics(services,tmp_path/'diagnostic.zip')
    with zipfile.ZipFile(result['path']) as z:
        assert set(z.namelist())=={'environment.json','hardware.json','errors.json','manifest.json'}
        all_text=''.join(z.read(n).decode() for n in z.namelist())
        assert 'hidden' not in all_text and 'private' not in all_text
        for n in z.namelist():json.loads(z.read(n))
        assert json.loads(z.read('hardware.json'))[0]['backend_validated'] is False
    services.close()
