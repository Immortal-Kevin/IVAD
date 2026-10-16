"""P37-A contracts and failure isolation; fixtures are not hardware evidence."""
import copy,json,sys,subprocess,threading,time
from pathlib import Path
import pytest
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos
from ivad_app.compute.rfdetr_contract import parameters,signature,PROTOCOL
from ivad_app.compute.gpu_lock import gpu_lease,ComputationCancelled
from ivad_app.core.contracts import AppError
ROOT=Path(__file__).resolve().parents[1]

def test_checkpoint_layout_cannot_be_changed_by_extension():
    from ivad_app.compute.rfdetr_weights import require_native_weights
    with pytest.raises(ValueError):require_native_weights(dict(state_dict={'x':'fixture'},optimizer_states=[]))
    require_native_weights(dict(model={'x':'fixture'},args={},optimizer_states=[]))

@pytest.mark.parametrize('value',[{'imgsz':384},{'optimizer':'SGD'},{'epochs':0},{'batch_size':False},{'resolution':385},{'lr':float('nan')},{'lr_encoder':0},{'amp_dtype':'cpu'},{'use_ema':'yes'}])
def test_rf_parameters_reject_yolo_invalid(value):
    with pytest.raises(AppError):parameters(value)

def test_gui_composition_does_not_import_old_training_engine(tmp_path):
    code="from pathlib import Path;import sys;from ivad_app.core.application import ApplicationServices;s=ApplicationServices(Path.cwd(),Path(sys.argv[1]));assert 'ivad_app.services.training_service' not in sys.modules;assert not any(n.startswith('ultralytics') for n in sys.modules);s.close()"
    subprocess.run([sys.executable,'-c',code,str(tmp_path/'runtime')],cwd=ROOT,check=True)

@pytest.mark.parametrize('ids',[(0,1),(1,5),(3,17)])
def test_coco_mapping_negative_and_provenance(tmp_path,ids):
    from PIL import Image
    from ivad_app.storage.project_store import file_hash
    from ivad_app.datasets.rfdetr import export
    Image.new('RGB',(32,24)).save(tmp_path/'sample.png');digest=file_hash(tmp_path/'sample.png')
    m=dict(version_id='fixture',classes=[dict(uuid='a',class_id=ids[0],name='A'),dict(uuid='b',class_id=ids[1],name='B')],samples=[])
    for i,split in enumerate(['train','val']):
        objects=[dict(id='a',kind='box',source='Human Generated',label_id='b',geometry=[2,3,12,11])] if i==0 else []
        m['samples'].append(dict(split=split,annotation_source='Human Generated',width=32,height=24,image='sample.png',sha256=digest,frame_id=str(i),source_group_id=str(i),time_us=i*200000,annotation=dict(image_tag='ABNORMAL' if objects else 'NORMAL',objects=objects)))
    path=tmp_path/'manifest.json';path.write_text(json.dumps(m),encoding='utf8');result=export(path,tmp_path/'coco')
    assert result['counts']['valid']['normal']==1
    train=json.loads((tmp_path/'coco/train/_annotations.coco.json').read_text());assert train['annotations'][0]['category_id']==ids[1] and train['annotations'][0]['bbox']==[2,3,12,11]
    assert result['minimum_cross_split_same_source_seconds'] is None

def test_cross_process_gpu_lock_and_wait_cancel(tmp_path):
    uuid='GPU-c942e790-0e56-4262-a96d-16122a858702'
    code="from pathlib import Path;import sys;from ivad_app.compute.gpu_lock import gpu_lease;\nwith gpu_lease(Path(sys.argv[1]),sys.argv[2],lambda:False):print('ACQUIRED',flush=True)"
    with gpu_lease(tmp_path,uuid,lambda:False):
        child=subprocess.Popen([sys.executable,'-c',code,str(tmp_path),uuid],cwd=ROOT,stdout=subprocess.PIPE,text=True)
        time.sleep(.3);assert child.poll() is None
        with pytest.raises(ComputationCancelled):
            with gpu_lease(tmp_path,uuid,lambda:True):pass
    assert child.communicate(timeout=5)[0].strip()=='ACQUIRED'

def test_rf_registry_rejects_unvalidated_pth_ckpt(services,tmp_path):
    p=services.projects.create(str(tmp_path),'RF registry fixture');source=tmp_path/'x.pth';source.write_bytes(b'fixture NOT weights')
    with pytest.raises(AppError):services.models.register(source,dict(backend='rfdetr',model='rfdetr-nano'),p.root,trusted=True)
    assert services.models.versions(p.root)==[]

def test_rf_registry_atomic_run_gate(services,tmp_path):
    p=services.projects.create(str(tmp_path),'atomic fixture');source=tmp_path/'x.pth';source.write_bytes(b'fixture never loaded')
    details=dict(backend='rfdetr',model='rfdetr-nano',artifact_format='rf-detr-weights-pth',parity=dict(status='PASS'),evaluation_protocol_sha256=signature(PROTOCOL))
    with pytest.raises(AppError):services.models.register(source,details,p.root,trusted=True,training_completion=('missing',{}))
    assert services.models.versions(p.root)==[]

def test_force_stop_owned_windows_process_tree(tmp_path):
    import ctypes
    from ivad_app.services.rfdetr_training_service import RFDETRTrainingService
    pidfile=tmp_path/'owned-grandchild.pid'
    code="import subprocess,sys,time;from pathlib import Path;p=subprocess.Popen([sys.executable,'-c','import time;time.sleep(120)']);Path(sys.argv[1]).write_text(str(p.pid));time.sleep(120)"
    child=subprocess.Popen([sys.executable,'-c',code,str(pidfile)],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        deadline=time.monotonic()+5
        while not pidfile.exists() and time.monotonic()<deadline:time.sleep(.05)
        assert pidfile.exists();pid=int(pidfile.read_text());RFDETRTrainingService.stop_child(child)
        handle=ctypes.windll.kernel32.OpenProcess(0x100000,False,pid)
        if handle:
            try:assert ctypes.windll.kernel32.WaitForSingleObject(handle,1000)==0
            finally:ctypes.windll.kernel32.CloseHandle(handle)
        assert child.poll() is not None
    finally:
        if child.poll() is None:RFDETRTrainingService.stop_child(child)
        child.communicate(timeout=5)

def test_rf_environment_isolation_and_checkpoint_rejection(services,tmp_path):
    rf=services.training.rf
    assert rf.python().parent.parent.name=='.venv-rfdetr'
    services.settings.save_preferences(dict(services.settings.preferences(),rfdetr_worker_python=str(ROOT/'.venv-nvidia/Scripts/python.exe')))
    with pytest.raises(AppError):rf.python()

@pytest.mark.parametrize('mutation',['empty_classes','polygon','coordinates','normal_conflict','abnormal_no_box','machine_truth'])
def test_rf_preflight_rejects_invalid_truth(services,media_project,monkeypatch,mutation):
    from tests.test_p3_training import freeze_valid
    p,vid=freeze_valid(services,media_project);folder,snap=services.datasets.snapshot(vid,p.root);snap=copy.deepcopy(snap)
    sample=next(s for s in snap['samples'] if s['annotation']['objects']);annotation=sample['annotation']
    if mutation=='empty_classes':snap['classes']=[]
    elif mutation=='polygon':annotation['objects'][0]['kind']='polygon'
    elif mutation=='coordinates':annotation['objects'][0]['geometry']=[-1,0,10,10]
    elif mutation=='normal_conflict':annotation['image_tag']='NORMAL'
    elif mutation=='abnormal_no_box':annotation['objects']=[]
    else:annotation['objects'][0]['source']='Machine Generated'
    monkeypatch.setattr(services.datasets,'snapshot',lambda *a:(folder,snap))
    with pytest.raises(AppError):services.training.rf.snapshot(vid,p.root)

def test_rf_gui_parameters_layout_and_refresh(qtbot,services,media_project,monkeypatch):
    from tests.test_p3_training import freeze_valid
    from tests.test_gui import make_window,close_window
    from ivad_app.core.contracts import DeviceInfo
    from PySide6.QtWidgets import QComboBox
    p,vid=freeze_valid(services,media_project)
    gpu=DeviceInfo('nvidia:fixture','SOFTWARE FIXTURE, not GPU evidence','RF-DETR CUDA',True,True,False,'TEST',dict(bf16_supported=True))
    monkeypatch.setattr(services.training.rf,'devices_snapshot',lambda:[gpu])
    w=make_window(qtbot,services);w.show_page('training');page=w.pages['training']
    try:
        qtbot.waitUntil(lambda:page.dataset.findData(vid)>=0 and not page.busy,timeout=10000)
        assert page.model.currentText()=='rfdetr-nano';assert not page.advanced.isVisible()
        assert all(not x.isEnabled() and x.toolTip() for x in page.rf_inputs.values())
        page.mode.setCurrentIndex(1);assert all(x.isEnabled() for x in page.rf_inputs.values())
        page.rf_inputs['resolution'].setValue(385);assert '32' in page.info.text();page.rf_inputs['resolution'].setValue(384)
        payload=page.configuration();assert 'imgsz' not in payload['parameters'] and 'optimizer' not in payload['parameters']
        # Timer refresh must not reset an open combo's model or pending selection.
        changes=[];page.initial.model().modelReset.connect(lambda:changes.append(True));page.refresh()
        qtbot.waitUntil(lambda:not page.busy,timeout=10000);assert not changes
        assert page.rf_inputs['amp_dtype'].model().item(1).isEnabled()
        for size in [(1920,1080),(1100,720)]:
            w.resize(*size);qtbot.wait(100)
            if page.width()>=1100:assert page.basic.geometry().right()<page.rf_advanced.geometry().left()
            else:assert page.basic.geometry().bottom()<page.rf_advanced.geometry().top()
            assert all(b.width()>=b.fontMetrics().horizontalAdvance(b.text()) for b in page.action_buttons)
    finally:close_window(qtbot,w)
