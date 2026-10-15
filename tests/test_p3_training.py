import copy,sqlite3
from pathlib import Path
import pytest
from ivad_app.core.contracts import AppError
from ivad_app.services.training_service import validate_parameters
from ivad_app.storage.database import Database
from tests.test_p2_services import media_project
from tests.test_p2_media import Context,sample_videos
from tests.test_gui import make_window,close_window

@pytest.mark.parametrize('values',[{'epochs':0},{'batch':-1},{'imgsz':641},{'lr0':float('nan')},{'optimizer':'untrusted'},{'amp':'true'},{'unknown':1}])
def test_parameter_reject(values):
    with pytest.raises(AppError):validate_parameters(values)

def freeze_valid(services,media_project):
    p,media,ids=media_project;label=services.annotations.labels()[0]['id'];chosen=[]
    for mid in media:
        frames=[f for f in services.media.frames() if f['media_id']==mid]
        for index,f in enumerate([frames[0],frames[-1]]):
            payload={'image_tag':'ABNORMAL' if index==0 else 'NORMAL','image_label_id':None,'objects':[{'id':f['id'],'kind':'box','geometry':[10,20,60,40],'label_id':label}] if index==0 else []}
            services.annotations.save(f['id'],payload,'REVIEWED',0);chosen.append(f['id'])
    r=services.datasets.freeze(Context(),{'root':p.root,'name':'P3 TEST FIXTURE, not industrial truth','frame_ids':chosen,'ratios':[70,20,10]})
    return p,r['version_id']

def test_preflight_snapshot_and_leakage(services,media_project,monkeypatch):
    p,vid=freeze_valid(services,media_project);folder,snap,counts=services.training.preflight(vid,p.root)
    assert counts['train'] and counts['val'];before=(folder/'manifest.json').read_bytes()
    bad=copy.deepcopy(snap);bad['samples'][1]['sha256']=bad['samples'][0]['sha256'];bad['samples'][1]['image']=bad['samples'][0]['image']
    monkeypatch.setattr(services.datasets,'snapshot',lambda *args:(folder,bad))
    with pytest.raises(AppError):services.training.preflight(vid,p.root)
    assert (folder/'manifest.json').read_bytes()==before

@pytest.mark.parametrize('mutation',['unknown','unreviewed','roi','bad_class','bad_coordinates','group_leak'])
def test_training_rejects_invalid_truth(services,media_project,monkeypatch,mutation):
    p,vid=freeze_valid(services,media_project);folder,snap=services.datasets.snapshot(vid,p.root);snap=copy.deepcopy(snap)
    sample=next(s for s in snap['samples'] if s['annotation']['objects'])
    if mutation=='unknown':sample['annotation']['image_tag']='UNKNOWN'
    elif mutation=='unreviewed':sample['annotation_status']='DRAFT'
    elif mutation=='roi':sample['annotation']['objects'][0]['kind']='roi_box'
    elif mutation=='bad_class':sample['annotation']['objects'][0]['label_id']='missing'
    elif mutation=='bad_coordinates':sample['annotation']['objects'][0]['geometry']=[-1,0,9999,5]
    else:
        for item in snap['samples']:item['camera_id']='same-camera-test-fixture'
    monkeypatch.setattr(services.datasets,'snapshot',lambda *args:(folder,snap))
    with pytest.raises(AppError):services.training.preflight(vid,p.root)

def test_registry_gates_hash_and_atomic_rollback(services,tmp_path):
    p=services.projects.create(str(tmp_path),'P3 registry fixture');f=tmp_path/'owned.pt';f.write_bytes(b'owned test fixture, never deserialized')
    with pytest.raises(AppError):services.models.register(f,{},p.root)
    mid=services.models.register(f,{'model':'yolo26n'},p.root,trusted=True)
    with pytest.raises(AppError):services.models.transition(mid,'CANDIDATE',1,p.root)
    good={'model':'yolo26n','metrics':{'precision':0.,'recall':0.,'map50':0.,'map50_95':0.},'validation_passed':True,'gpu_evidence':{'weight_changed':True},'source':'TEST FIXTURE NOT TRAINING EVIDENCE'}
    a=services.models.register(f,good,p.root,trusted=True);b=services.models.register(f,good,p.root,trusted=True)
    with pytest.raises(AppError):services.models.transition(a,'CANDIDATE',1,p.root)
    for k in [a,b]:services.models.transition(k,'CANDIDATE',1,p.root,thresholds={key:0 for key in good['metrics']})
    with pytest.raises(AppError):services.models.transition(a,'PRODUCTION',2,p.root)
    services.models.transition(a,'PRODUCTION',2,p.root,approved=True);services.models.transition(b,'PRODUCTION',2,p.root,approved=True)
    rows={r['id']:r for r in services.models.versions(p.root)};assert rows[a]['state']=='CANDIDATE' and rows[b]['state']=='PRODUCTION'
    services.models.transition(a,'PRODUCTION',rows[a]['revision'],p.root,approved=True,rollback=True)
    rows={r['id']:r for r in services.models.versions(p.root)};assert rows[a]['state']=='PRODUCTION' and rows[b]['state']=='CANDIDATE'
    output=Path(services.models.export(a,tmp_path,p.root));assert (output/'model.pt').read_bytes()==f.read_bytes()
    assert (output/'model_manifest.json').exists()
    path,_=services.models.verify(a,p.root);path.write_bytes(b'controlled corruption')
    with pytest.raises(AppError):services.models.verify(a,p.root)

def test_schema0005_to0006_append_only(tmp_path):
    path=tmp_path/'old.sqlite';db=Database(path,create=True,revision='0005');db.close()
    with sqlite3.connect(path) as raw:before=raw.execute("select name,sql from sqlite_master where type='table' and name!='alembic_version' order by name").fetchall()
    db=Database(path);assert db.integrity_check()=='ok';db.close()
    with sqlite3.connect(path) as raw:
        after=dict(raw.execute("select name,sql from sqlite_master where type='table'").fetchall());assert all(after[n]==sql for n,sql in before)
    assert list(tmp_path.glob('*.backup'))

def test_training_gui_config_and_cpu_rejection(qtbot,services,media_project):
    p,vid=freeze_valid(services,media_project);w=make_window(qtbot,services);w.update_project_summary();page=w.pages['training'];w.show_page('training')
    qtbot.waitUntil(lambda:page.dataset.findData(vid)>=0,timeout=10000)
    assert page.mode.currentIndex()==0 and not page.advanced.isEnabled()
    page.mode.setCurrentIndex(1);assert page.advanced.isEnabled();page.inputs['imgsz'].setValue(641)
    page.gpu.addItem('invalid CPU','cpu');page.gpu.setCurrentIndex(page.gpu.findData('cpu'));page.start();assert '32' in page.info.text()
    page.inputs['imgsz'].setValue(160);page.start();qtbot.waitUntil(lambda:'CPU' in page.info.text(),timeout=10000)
    assert not services.jobs.history();close_window(qtbot,w)

def test_registry_gui_serializes_mutation_and_light_background(qtbot,services,tmp_path,monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    from tests.test_p2_gui import click
    project=services.projects.create(str(tmp_path),'registry GUI fixture');f=tmp_path/'test.pt';f.write_bytes(b'TEST FIXTURE, never loaded')
    data={'model':'yolo26n','metrics':dict(precision=1.,recall=1.,map50=1.,map50_95=1.),'validation_passed':True,'gpu_evidence':{'weight_changed':True},'source':'TEST FIXTURE, synthetic metadata, no hardware claim'}
    mid=services.models.register(f,data,project.root,trusted=True)
    w=make_window(qtbot,services);w.update_project_summary();w.show_page('models');page=w.pages['models']
    qtbot.waitUntil(lambda:not page.busy and len(page.rows)==1,timeout=10000)
    page.table.selectRow(0);click(qtbot,page,'model_candidate');assert page.busy and not page.isEnabled()
    qtbot.waitUntil(lambda:not page.busy,timeout=10000);assert page.rows[0]['state']=='CANDIDATE'
    page.table.selectRow(0);monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
    click(qtbot,page,'model_production');assert page.busy;qtbot.waitUntil(lambda:not page.busy,timeout=10000)
    assert page.rows[0]['state']=='PRODUCTION'
    image=page.grab().toImage();assert image.pixelColor(2,2).lightness()>200
    close_window(qtbot,w)

@pytest.mark.parametrize('failure',['oom','crash'])
def test_worker_failure_keeps_queue_and_does_not_register(services,media_project,monkeypatch,failure):
    import json,time
    from ivad_app.core.contracts import DeviceInfo
    p,vid=freeze_valid(services,media_project)
    monkeypatch.setattr(services.devices,'require_gpu',lambda *_:DeviceInfo('nvidia:MOCK','MOCK software failure injection','CUDA',True,True,False,'TEST FIXTURE',{'index':0}))
    class Child:
        returncode=1
        def __init__(self,args,**kwargs):
            req=json.loads(Path(args[-1]).read_text(encoding='utf8'))
            if failure=='oom':(Path(req['work'])/'result.json').write_text(json.dumps({'status':'FAIL','oom':True,'error':'MOCK OutOfMemoryError; not hardware measurement'}),encoding='utf8')
        def poll(self):return self.returncode
    monkeypatch.setattr('ivad_app.services.training_service.subprocess.Popen',Child)
    jid=services.jobs.submit('p3_train',p.id,{'root':p.root,'version_id':vid,'device_id':'nvidia:MOCK'})
    deadline=time.monotonic()+10
    while services.jobs.get(jid)['state'] not in {'FAILED','SUCCEEDED'} and time.monotonic()<deadline:time.sleep(.02)
    job=services.jobs.get(jid);assert job['state']=='FAILED'
    assert ('显存不足' if failure=='oom' else 'Worker异常退出') in job['error']
    assert not services.models.versions(p.root) and services.training.runs(p.root)[0]['state']=='FAILED'
    next_job=services.jobs.submit('diagnostic');deadline=time.monotonic()+10
    while services.jobs.get(next_job)['state']!='SUCCEEDED' and time.monotonic()<deadline:time.sleep(.02)
    assert services.jobs.get(next_job)['state']=='SUCCEEDED'
