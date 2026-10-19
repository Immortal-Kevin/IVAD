"""Retirement policy tests. Synthetic rows are not CUDA or user-data evidence."""
import json,threading,os
from pathlib import Path
import pytest
from sqlalchemy import select
from ivad_app.core.contracts import AppError
from ivad_app.services.backend_policy import classification
from ivad_app.storage.models import TrainingRun,ModelVersion,JobRecord

@pytest.mark.parametrize('details,expected',[
    ({'model':'yolo11n'},'LEGACY_READ_ONLY'),({'model':'yolo26n'},'LEGACY_READ_ONLY'),
    ({'model':'rfdetr-nano','backend':'rfdetr'},'ACTIVE_RFDETR'),
    ({'model':'rfdetr-nano'},'UNKNOWN'),({'model':'yolo11n','backend':'rfdetr'},'UNKNOWN'),
    ({'backend':'ultralytics'},'UNKNOWN'),({},'UNKNOWN')])
def test_trustworthy_classification(details,expected):
    assert classification(details)==expected

def seed(services,tmp_path):
    p=services.projects.create(str(tmp_path),'mixed history fixture')
    records=[dict(model='yolo11n'),dict(model='yolo26n'),dict(model='opaque')]
    records += [dict(backend='rfdetr',model='rfdetr-nano',state=state) for state in ['QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED']]
    source=Path(p.root)/'models/history.pt';source.write_bytes(b'historical bytes never loaded')
    from ivad_app.storage.project_store import file_hash
    with services.store.open(p.root) as (_,db,_),db.transaction() as s:
        for i,d in enumerate(records):
            d=dict(state='SUCCEEDED',path='models/history.pt',sha256=file_hash(source),**{k:v for k,v in d.items() if k!='state'})|{'state':d.get('state','SUCCEEDED')}
            s.add(TrainingRun(id='run-'+str(i),details=d,revision=1));s.add(ModelVersion(id='model-'+str(i),details=d,revision=1))
    return p

def test_history_filter_archive_integrity_restart_and_project_scope(services,tmp_path):
    p=seed(services,tmp_path)
    before=services.training.runs(p.root,include_archived=True)
    assert len(before)==8 and len(services.models.versions(p.root,include_archived=True))==8
    assert {r['state'] for r in services.training.runs(p.root)}=={'QUEUED','RUNNING','SUCCEEDED','FAILED','CANCELLED'}
    assert len(services.models.versions(p.root))==5
    services.projects.close();services.projects.open(p.root)
    assert services.training.runs(p.root,include_archived=True)==before
    p2=services.projects.create(str(tmp_path),'other project')
    assert services.training.runs(p2.root)==[] and services.models.versions(p2.root)==[]
    assert services.models.verify('model-0',p.root)[0].read_bytes()==b'historical bytes never loaded'
    for state in ['CANDIDATE','PRODUCTION']:
        with pytest.raises(AppError,match='只读'):services.models.transition('model-0',state,1,p.root,approved=True)
    assert services.training.runs(p.root,include_archived=True)==before

@pytest.mark.parametrize('model',['yolo11n','yolo26n','unverified',None])
def test_old_jobs_rejected_at_both_boundaries(services,model):
    payload=dict(model=model)
    for fn in [services.training.configuration_preflight,lambda p:services.training.train(None,p),lambda p:services.jobs.submit('p3_train',None,p)]:
        with pytest.raises(AppError) as error:fn(payload)
        assert error.value.code=='LEGACY_READ_ONLY'
    assert services.jobs.history()==[]

def test_offline_blocked_before_gpu_or_cache_change(services,monkeypatch):
    monkeypatch.setattr(services.devices,'require_gpu',lambda *_:pytest.fail('must not load GPU'))
    for fn in [lambda:services.offline.run(None,{}),lambda:services.jobs.submit('p35_offline',None,{})]:
        with pytest.raises(AppError,match='MIGRATION PENDING'):fn()

def test_queued_rf_visible_cancel_and_live_legacy_kept(services,tmp_path):
    p=services.projects.create(str(tmp_path),'queued fixture');hold=threading.Event();entered=threading.Event()
    def blocker(context,payload):
        entered.set()
        while not hold.wait(.01):context.check()
    services.jobs.register('p2_blocker',blocker)
    services.jobs.submit('p2_blocker',p.id,{})
    assert entered.wait(3)
    try:
        jid=services.jobs.submit('p3_train',p.id,dict(root=p.root,model='rfdetr-nano'))
        rows=services.training.runs(p.root);assert len(rows)==1 and rows[0]['state']=='QUEUED' and rows[0]['job_id']==jid
        services.jobs.cancel(jid)
        assert services.training.runs(p.root)[0]['state']=='CANCELLED'
        with services.jobs.db.transaction() as s:
            s.add(JobRecord(id='old-live',kind='p3_train',project_id='other',state='RUNNING',progress=20,created_at='2026-10-19',updated_at='2026-10-19',error='',payload={'model':'yolo11n'},result={}))
            s.add(JobRecord(id='old-done',kind='p3_train',project_id=p.id,state='SUCCEEDED',progress=100,created_at='2026-10-19',updated_at='2026-10-19',error='',payload={'model':'yolo26n'},result={}))
            s.add(JobRecord(id='unknown-live',kind='p3_train',project_id=p.id,state='RUNNING',progress=0,created_at='2026-10-19',updated_at='2026-10-19',error='',payload={'model':'rfdetr-nano','root':p.root},result={}))
        visible=services.jobs.operator_history(p.id)
        assert any(r['id']=='old-live' and r['archive_classification']=='LEGACY_READ_ONLY' for r in visible)
        assert all(r['id']!='old-done' for r in visible)
        assert any(r['id']=='unknown-live' and r['archive_classification']=='UNKNOWN' for r in visible)
        assert all(r['job_id']!='unknown-live' for r in services.training.runs(p.root))
    finally:hold.set()

def test_native_operator_controls_and_popup_lifetime(qtbot,services,tmp_path,monkeypatch):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication,QMenu
    from tests.test_gui import make_window,close_window
    print('Qt platform:',QApplication.platformName())
    assert QApplication.platformName()=='windows'
    p=seed(services,tmp_path);monkeypatch.setattr(services.training.rf,'devices_snapshot',lambda:[])
    for cycle in range(2):
        if cycle:
            # MainWindow close shuts down its service container. A real restart
            # must create a fresh container against the persisted fixture.
            from ivad_app.core.application import ApplicationServices
            services=ApplicationServices(services.root,services.data_dir)
            services.projects.open(p.root)
            monkeypatch.setattr(services.training.rf,'devices_snapshot',lambda:[])
        w=make_window(qtbot,services)
        try:
            w.show_page('training');page=w.pages['training']
            qtbot.waitUntil(lambda:not page.busy and len(page.rows)==5,timeout=10000)
            assert [page.model.itemText(i) for i in range(page.model.count())]==['rfdetr-nano']
            export=w.p2.dataset.format
            assert [export.itemData(i) for i in range(export.count())]==['ivad_native','coco'] and export.currentData()=='ivad_native'
            for i in range(4):
                page.mode.showPopup();qtbot.wait(30);page.refresh();qtbot.waitUntil(lambda:not page.busy,timeout=5000);page.mode.hidePopup()
                menu=QMenu(page);menu.addAction('read-only popup stress');menu.popup(page.mapToGlobal(page.rect().center()));qtbot.wait(20);menu.close();menu.deleteLater();qtbot.wait(10)
            w.show_page('models');models=w.pages['models'];qtbot.waitUntil(lambda:not models.busy and len(models.rows)==5,timeout=5000)
            models.import_model();assert '手工导入尚未开放' in models.info.text()
            w.show_page('offline');offline=w.pages['offline'];qtbot.waitUntil(lambda:not offline.busy,timeout=5000);offline.watch()
            assert not offline.start_button.isEnabled() and 'MIGRATION PENDING' in offline.model_info.text()
            if cycle==0 and os.environ.get('IVAD_RETIREMENT_EVIDENCE'):
                output=Path(os.environ['IVAD_RETIREMENT_EVIDENCE']);output.mkdir(parents=True,exist_ok=True)
                for key in ['training','dataset','models','offline']:
                    w.show_page(key);qtbot.wait(80);assert w.grab().save(str(output/(key+'.png')))
        finally:close_window(qtbot,w)
