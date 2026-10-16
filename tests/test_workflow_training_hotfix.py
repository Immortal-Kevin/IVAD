import copy,json,os
from pathlib import Path
import pytest
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import Qt
from tests.test_dataset_lifecycle import draft_payload
from tests.test_dataset_management_hotfix import truth
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context
from tests.test_gui import make_window,close_window
from tests.test_p3_training import freeze_valid
from ivad_app.core.contracts import AppError,DeviceInfo

def mode_payload(truth,mode='engineering'):
    value=draft_payload(truth);value['settings']['validation_mode']=mode;value['settings']['preset']='small';value['settings']['ratios']=[80,20,0]
    return value

def test_risk_ack_bound_and_immutable_versions(services,truth):
    p,*_=truth;value=mode_payload(truth);r=services.datasets.save_draft(value);did=r['id']
    result=services.datasets.validate_draft(did);plan=result['plan'];assert plan['risk_confirmation_required'] and result['dataset']['details']['draft']['state']=='DRAFT'
    with pytest.raises(AppError):services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=1))
    signature=services.datasets.validation_signature(plan);services.datasets.acknowledge_draft_risk(did,signature,expected_revision=1)
    assert not services.datasets.validate_draft(did)['plan']['risk_confirmation_required']
    frozen=services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=1));folder,snap=services.datasets.snapshot(frozen['version_id']);before=(folder/'manifest.json').read_bytes()
    assert snap['admission']['risk_ack']==signature and snap['admission']['split_status']=='LIMITED'
    value.update(dataset_id=did,expected_revision=1);value['settings']['seed']=999;services.datasets.save_draft(value)
    assert services.datasets.validate_draft(did)['plan']['risk_confirmation_required']
    assert (folder/'manifest.json').read_bytes()==before

@pytest.mark.parametrize('mode',['engineering','strict'])
def test_integrity_never_relaxed(services,truth,mode):
    value=mode_payload(truth,mode);r=services.datasets.save_draft(value)
    row=services.media.frames()[0]
    # corrupt a referenced test image, never a user image
    from ivad_app.storage.models import ExtractedFrame
    from sqlalchemy import select
    with services.store.open() as (root,db,_),db.transaction() as s:
        frame=s.get(ExtractedFrame,value['frame_ids'][0]);path=Path(root)/frame.path
    path.write_bytes(b'INVALID TEST IMAGE')
    plan=services.datasets.validate_draft(r['id'])['plan'];assert plan['split_status']=='BLOCKED' and plan['issues']

def test_strict_rejects_limited_and_invalid_mode(services,truth):
    value=mode_payload(truth,'strict');r=services.datasets.save_draft(value);result=services.datasets.validate_draft(r['id'])
    assert result['plan']['split_status']=='BLOCKED' and not result['plan']['risk_confirmation_required']
    value.update(dataset_id=r['id'],expected_revision=1);value['settings']['validation_mode']='bypass';services.datasets.save_draft(value)
    with pytest.raises(AppError):services.datasets.validate_draft(r['id'])

def test_gui_check_saves_dirty_in_place(qtbot,services,truth,monkeypatch):
    r=services.datasets.save_draft(mode_payload(truth));w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:r['id'] in d.dataset_records and not w.p2.refreshing,timeout=10000);d.existing.setCurrentIndex(d.existing.findData(r['id']));d.tabs.setCurrentIndex(2)
        d.preset.setCurrentIndex(d.preset.findData('standard'));d.preset.setCurrentIndex(d.preset.findData('small'))
        assert d.split_button.isEnabled() and not d.allow_random.isVisible() and not d.allow_limited.isVisible()
        calls=[]
        def yes(*a,**k):calls.append(1);return QMessageBox.StandardButton.Yes
        monkeypatch.setattr(QMessageBox,'question',yes);w.p2.split_preview()
        qtbot.waitUntil(lambda:d.active_validated and d.isEnabled(),timeout=10000)
        assert d.tabs.currentIndex()==2 and d.active_dataset==r['id'] and len(services.datasets.list_datasets())==1 and len(calls)==1
        w.p2.split_preview();qtbot.waitUntil(lambda:d.isEnabled(),timeout=10000);assert len(calls)==1
        out=Path(os.environ.get('IVAD_WORKFLOW_EVIDENCE',str(services.data_dir/'workflow')));out.mkdir(parents=True,exist_ok=True);w.resize(1920,1080);qtbot.wait(50);w.grab().save(str(out/'dataset-validation-mode.png'))
    finally:d.draft_dirty=False;close_window(qtbot,w)

def test_gui_save_failure_no_check(qtbot,services,truth,monkeypatch):
    r=services.datasets.save_draft(mode_payload(truth));w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:r['id'] in d.dataset_records and not w.p2.refreshing,timeout=10000);d.existing.setCurrentIndex(d.existing.findData(r['id']));d.seed.setValue(100)
        monkeypatch.setattr(services.datasets,'save_draft',lambda *a:(_ for _ in ()).throw(ValueError('TEST save failure')))
        monkeypatch.setattr(services.datasets,'validate_draft',lambda *a:pytest.fail('must not check failed save'))
        w.p2.split_preview();qtbot.waitUntil(lambda:not d.draft_saving,timeout=10000)
        assert d.draft_dirty and '保存失败' in d.split_save_state.text()
    finally:d.draft_dirty=False;close_window(qtbot,w)

def test_training_controls_preflight_guards_and_layout(qtbot,services,media_project,monkeypatch):
    p,vid=freeze_valid(services,media_project);w=make_window(qtbot,services);w.update_project_summary();page=w.pages['training'];w.show_page('training')
    try:
        page.model.setCurrentText('yolo26n')
        qtbot.waitUntil(lambda:page.dataset.findData(vid)>=0 and not page.busy,timeout=10000);page.timer.stop();page.gpu.addItem('NVIDIA TEST DEVICE (not hardware evidence)','nvidia:fixture');page.gpu.setCurrentIndex(page.gpu.findData('nvidia:fixture'))
        assert all(not x.isEnabled() and x.toolTip() for x in page.inputs.values())
        page.mode.setCurrentIndex(1);assert all(x.isEnabled() for x in page.inputs.values());page.inputs['optimizer'].setCurrentText('AdamW');page.inputs['amp'].setChecked(True)
        report={'counts':{'train':2,'val':1},'parameters':page.configuration()['parameters']}
        captured=[]
        def inspect(payload):captured.append(copy.deepcopy(payload));return report
        monkeypatch.setattr(services.training,'configuration_preflight',inspect)
        page.start();assert not services.jobs.history() and '检查' in page.info.text()
        page.preflight();qtbot.waitUntil(lambda:not page.checking,timeout=10000);assert page.checked_configuration and captured[-1]['parameters']['amp'] and captured[-1]['parameters']['optimizer']=='AdamW'
        page.inputs['batch'].setValue(3);assert page.checked_configuration is None and not page.action_buttons[2].isEnabled()
        page.inputs['imgsz'].setValue(641);assert '32' in page.info.text();page.inputs['imgsz'].setValue(640)
        # Hold submission completion: repeated clicks cannot submit twice.
        page.preflight();qtbot.waitUntil(lambda:not page.checking,timeout=10000)
        queued=[];monkeypatch.setattr(services.jobs,'submit',lambda *a:queued.append(a) or 'TEST-JOB')
        page.start();page.start();qtbot.waitUntil(lambda:not page.submitting,timeout=10000);assert len(queued)==1 and not services.training.runs()
        qtbot.waitUntil(lambda:not page.busy,timeout=10000)
        if page.gpu.findData('nvidia:fixture')<0:page.gpu.addItem('TEST NVIDIA backend (not hardware evidence)','nvidia:fixture')
        page.gpu.setCurrentIndex(page.gpu.findData('nvidia:fixture'))
        out=Path(os.environ.get('IVAD_WORKFLOW_EVIDENCE',str(services.data_dir/'workflow')));out.mkdir(parents=True,exist_ok=True)
        for width,height in [(1920,1080),(920,720)]:
            w.resize(width,height);qtbot.wait(80);w.grab().save(str(out/f'training-{width}.png'))
            if page.width()>=1100:
                assert page.basic.y()==page.advanced.y() and page.basic.x()<page.advanced.x()
                assert len({b.y() for b in page.action_buttons})==1
            (out/f'geometry-{width}.json').write_text(json.dumps(dict(requested=[width,height],actual=[w.width(),w.height()],dpr=w.devicePixelRatioF(),page_width=page.width(),button_positions=[[b.x(),b.y(),b.width(),b.height()] for b in page.action_buttons])),encoding='utf8')
        page.mode.setCurrentIndex(0);assert not page.inputs['amp'].isChecked()
        from PySide6.QtCore import QEvent,QPoint
        from PySide6.QtGui import QHelpEvent
        from PySide6.QtWidgets import QApplication,QToolTip
        control=page.inputs['epochs'];help_event=QHelpEvent(QEvent.Type.ToolTip,QPoint(5,5),control.mapToGlobal(QPoint(5,5)))
        QApplication.sendEvent(control,help_event)
        qtbot.waitUntil(lambda:QToolTip.isVisible(),timeout=3000);assert '完整遍历' in QToolTip.text();QToolTip.hideText()
        from ivad_app.services.training_service import DEFAULTS
        page.rows=[dict(id='RESUME-FIXTURE',parameters=dict(DEFAULTS,epochs=77))];page.resume.addItem('TEST interrupted resume','RESUME-FIXTURE');page.resume.setCurrentIndex(page.resume.findData('RESUME-FIXTURE'))
        assert page.inputs['epochs'].value()==77 and not page.inputs['epochs'].isEnabled() and page.configuration()['parameters']['epochs']==77
        assert '沿用原任务参数' in page.inputs['epochs'].toolTip();page.resume.setCurrentIndex(0)
        cancelled=[];page.rows=[dict(id='EXACT-TEST-RUN',state='RUNNING',job_id='EXACT-TEST-JOB')];page.selected_run='EXACT-TEST-RUN'
        monkeypatch.setattr(services.jobs,'cancel',lambda jid:cancelled.append(jid))
        questions=[]
        def deny(*args,**kwargs):questions.append(args[2]);return QMessageBox.StandardButton.No
        monkeypatch.setattr(QMessageBox,'question',deny);page.cancel();assert not cancelled and 'EXACT-TEST-RUN' in questions[0]
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes);page.cancel();qtbot.waitUntil(lambda:bool(cancelled),timeout=10000);assert cancelled==['EXACT-TEST-JOB']
    finally:close_window(qtbot,w)

def test_configuration_preflight_weight_and_resume_checks(services,media_project,monkeypatch,tmp_path):
    p,vid=freeze_valid(services,media_project)
    monkeypatch.setattr(services.devices,'require_gpu',lambda *_:DeviceInfo('nvidia:TEST','TEST','CUDA',True,True,False,'TEST',{}))
    value=dict(root=p.root,version_id=vid,device_id='nvidia:TEST',model='yolo11n',parameters={'amp':True,'optimizer':'AdamW'})
    result=services.training.configuration_preflight(value);assert result['parameters']['amp'] and result['counts']['val']
    with pytest.raises(AppError):services.training.configuration_preflight(dict(value,resume_run_id='missing'))
    with pytest.raises(AppError):services.training.configuration_preflight(dict(value,operation='validate'))

def test_worker_receives_exact_supported_parameters(services,media_project,monkeypatch):
    p,vid=freeze_valid(services,media_project);captured=[]
    monkeypatch.setattr(services.devices,'require_gpu',lambda *_:DeviceInfo('nvidia:TEST','TEST','CUDA',True,True,False,'TEST',{'index':0}))
    class Child:
        returncode=1
        def __init__(self,args,**kwargs):captured.append(json.loads(Path(args[-1]).read_text(encoding='utf8')))
        def poll(self):return 1
    monkeypatch.setattr('ivad_app.services.training_service.subprocess.Popen',Child)
    from ivad_app.services.training_service import validate_parameters
    params=validate_parameters(dict(epochs=3,imgsz=160,batch=2,patience=1,seed=456,lr0=.002,weight_decay=.001,optimizer='AdamW',augment=False,amp=True))
    jid=services.jobs.submit('p3_train',p.id,dict(root=p.root,version_id=vid,device_id='nvidia:TEST',parameters=params))
    import time
    deadline=time.monotonic()+10
    while services.jobs.get(jid)['state'] not in {'FAILED','SUCCEEDED'} and time.monotonic()<deadline:time.sleep(.02)
    assert services.jobs.get(jid)['state']=='FAILED' and captured[0]['parameters']==params
    assert not services.models.versions() # no actual CUDA or fabricated success

def test_real_copy_existing_200_and_v1_preserved(qtbot,services,monkeypatch,tmp_path):
    location=os.environ.get('IVAD_WORKFLOW_REAL_COPY')
    if not location:pytest.skip('Requires independent copy of existing 8525test1')
    root=Path(location).resolve();assert 'workflow-training-gui-20261016' in str(root)
    services.projects.open(str(root));r=next(d for d in services.datasets.list_datasets() if d['name']=='8525test1');did=r['id'];assert len(r['details']['draft']['members'])==200
    old_version=next(v for v in services.datasets.versions() if v['dataset_id']==did and v['number']==1);folder,snap=services.datasets.snapshot(old_version['id']);before=(folder/'manifest.json').read_bytes()
    runs=copy.deepcopy(services.training.runs());models=copy.deepcopy(services.models.versions())
    w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:did in d.dataset_records and not w.p2.refreshing,timeout=20000);d.existing.setCurrentIndex(d.existing.findData(did));d.tabs.setCurrentIndex(2)
        d.preset.setCurrentIndex(d.preset.findData('standard'));d.preset.setCurrentIndex(d.preset.findData('small'))
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes);w.p2.split_preview();qtbot.waitUntil(lambda:d.active_validated and d.isEnabled(),timeout=20000)
        assert len(d.draft_frames())==200 and d.active_dataset==did
        plan=services.datasets.load_dataset(did)['details']['draft']['validation']['report'];assert plan['split_counts']=={'train':160,'val':40,'test':0}
        services.datasets.freeze(Context(),dict(root=str(root),dataset_id=did,draft_revision=d.draft_revision))
        assert len(services.datasets.versions())==2 and (folder/'manifest.json').read_bytes()==before
        assert services.training.runs()==runs and services.models.versions()==models
        out=Path(os.environ['IVAD_WORKFLOW_EVIDENCE']);out.mkdir(parents=True,exist_ok=True);w.resize(1920,1080);qtbot.wait(100);w.grab().save(str(out/'real-copy-200.png'))
        (out/'real-copy-results.json').write_text(json.dumps(dict(dataset_id=did,members=200,plan=plan,v1_unchanged=True,old_runs_unchanged=True,old_models_unchanged=True),ensure_ascii=False,indent=2),encoding='utf8')
    finally:d.draft_dirty=False;close_window(qtbot,w)
    from ivad_app.core.application import ApplicationServices
    reopened=ApplicationServices(services.root,tmp_path/'reopen',step_seconds=.01)
    try:
        reopened.projects.open(str(root));saved=reopened.datasets.load_dataset(did)
        assert len(saved['details']['draft']['members'])==200 and saved['details']['draft']['settings']['validation_mode']=='engineering'
        assert reopened.training.runs()==runs and reopened.models.versions()==models
    finally:reopened.close()
