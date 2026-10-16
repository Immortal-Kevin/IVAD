import copy,json,sqlite3,os
from pathlib import Path
import pytest
from sqlalchemy import select
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox
from ivad_app.core.contracts import AppError
from ivad_app.core.application import ApplicationServices
from ivad_app.storage.database import Database,SCHEMA_HEAD
from ivad_app.storage.models import Annotation
from tests.test_dataset_management_hotfix import truth
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click

def draft_payload(truth,**extra):
    p,mids,ids,cams,label=truth
    return dict(name='生命周期实验',project_id=p.id,frame_ids=ids,camera_ids=cams,fault_ids=[label],allow_multi_camera=True,settings={'preset':'standard','strategy':'source','ratios':[70,20,10],'seed':123,'allow_limited':True,'allow_leakage':False},**extra)

def test_migration_0008_preserves_dataset_and_version(tmp_path):
    path=tmp_path/'legacy.sqlite';db=Database(path,create=True,revision='0008');db.close()
    with sqlite3.connect(path) as s:
        s.execute("insert into datasets(id,name,created_at) values('old','旧数据集','before')");s.execute("insert into dataset_versions(id,dataset_id,number,path,sha256,summary,created_at) values('v','old',1,'old.json','hash','{}','before')")
    db=Database(path);db.close()
    with sqlite3.connect(path) as s:
        assert s.execute('select id,name,created_at,details,revision from datasets').fetchone()==('old','旧数据集','before','{}',0)
        assert s.execute('select * from dataset_versions').fetchone()==('v','old',1,'old.json','hash','{}','before')
        assert s.execute('pragma integrity_check').fetchone()[0]=='ok' and s.execute('select version_num from alembic_version').fetchone()[0]==SCHEMA_HEAD
    assert list(tmp_path.glob('*.backup'))

def test_save_reopen_cas_and_independent_fault_datasets(services,truth,tmp_path):
    p,mids,ids,cams,label=truth;r=services.datasets.save_draft(draft_payload(truth));did=r['id'];assert r['revision']==1 and len(r['details']['draft']['members'])==6
    s=ApplicationServices(services.root,tmp_path/'reopen',step_seconds=.01)
    try:
        s.projects.open(p.root);same=s.datasets.load_dataset(did);assert same==r
        value=draft_payload(truth,dataset_id=did,expected_revision=1);value['frame_ids']=ids[:-1];r2=s.datasets.save_draft(value);assert r2['id']==did and r2['revision']==2
        with pytest.raises(AppError,match='修改'):services.datasets.save_draft(value)
        assert len(s.datasets.list_datasets())==1
        # Another fault dataset can share the same normal reference without relabeling it.
        other=services.annotations.save_label(dict(name='第二故障测试',annotation_type='box'))
        value=draft_payload(truth);value['name']='同摄像头第二故障';value['frame_ids']=[ids[1]];value['camera_ids']=[cams[0]];value['fault_ids']=[other['id']]
        b=s.datasets.save_draft(value);assert b['id']!=did and services.annotations.load(ids[1])['payload']['image_tag']=='NORMAL'
        assert [c['uuid'] for c in s.datasets.validate_draft(b['id'])['plan']['classes']]==[other['id']]
        assert len(s.datasets.load_dataset(did)['details']['draft']['members'])==5
    finally:s.close()

def test_scope_fault_and_project_guards(services,truth):
    value=draft_payload(truth);value['allow_multi_camera']=False
    with pytest.raises(AppError):services.datasets.save_draft(value)
    value=draft_payload(truth);value['project_id']='wrong'
    with pytest.raises(AppError):services.datasets.save_draft(value)
    value=draft_payload(truth);value['fault_ids']=[]
    with pytest.raises(AppError):services.datasets.save_draft(value)
    assert not services.datasets.list_datasets()

@pytest.mark.parametrize('preset,ratios',[('standard',[70,20,10]),('small',[80,20,0]),('custom',[60,20,20])])
def test_presets_class_statistics_and_reproducibility(services,truth,preset,ratios):
    p,mids,ids,cams,label=truth;a=services.datasets.split_preview(ids,preset=preset,ratios=ratios);b=services.datasets.split_preview(ids,preset=preset,ratios=ratios)
    assert a['split_counts']==b['split_counts'];assert sum(v['images'] for v in a['statistics'].values())==6 and sum(v['objects'] for v in a['statistics'].values())==3
    assert [v['target_percent'] for v in a['statistics'].values()]==ratios
    assert a['cross_source_groups']==0
    if preset=='small':assert a['split_counts']['test']==0 and a['split_status']=='LIMITED'

def test_validation_invalidation_versions_and_export(services,truth,tmp_path):
    p,mids,ids,cams,label=truth;r=services.datasets.save_draft(draft_payload(truth));did=r['id'];validated=services.datasets.validate_draft(did,expected_revision=1);assert validated['dataset']['details']['draft']['state']=='VALIDATED'
    frozen=services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=1));folder,snap=services.datasets.snapshot(frozen['version_id']);before=(folder/'manifest.json').read_bytes();assert snap['dataset_id']==did and snap['draft_revision']==1
    value=draft_payload(truth,dataset_id=did,expected_revision=1);value['frame_ids']=ids[:-1];services.datasets.save_draft(value)
    with pytest.raises(AppError):services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=2))
    services.datasets.validate_draft(did,expected_revision=2);v2=services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=2));assert v2['number']==2 and (folder/'manifest.json').read_bytes()==before
    services.datasets.export(Context(),dict(root=p.root,version_id=frozen['version_id'],format='yolo_detect',parent=str(tmp_path)))
    assert services.training.preflight(frozen['version_id'])[2]['val']>0
    with pytest.raises(AppError):services.training.preflight(did)
    # Editing source truth after validation cannot silently freeze a stale draft.
    doc=services.annotations.load(ids[0]);services.annotations.save(ids[0],doc['payload'],None,doc['revision'])
    with pytest.raises(AppError,match='检查'):services.datasets.freeze(Context(),dict(root=p.root,dataset_id=did,draft_revision=2))

def test_single_source_limited_engineering_fallback(services,truth):
    p,mids,ids,cams,label=truth;chosen=ids[:2]
    standard=services.datasets.split_preview(chosen,preset='standard');assert standard['split_counts']=={'train':2,'val':0,'test':0} and standard['split_status']=='LIMITED'
    small=services.datasets.split_preview(chosen,preset='small',pipeline_fallback=True,allow_leakage=True);assert small['effective_strategy']=='random' and small['split_counts']=={'train':1,'val':1,'test':0} and small['split_status']=='LIMITED'

def test_gui_save_failure_switch_and_restart(qtbot,services,truth,tmp_path,monkeypatch):
    p,mids,ids,cams,label=truth;w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:bool(d.all_rows) and not w.p2.refreshing,timeout=10000);d.camera.setCurrentIndex(0);d.select_all();d.allow_multi.setChecked(True);d.add_selected();d.tabs.setCurrentIndex(1);d.name.setText('GUI持久化草稿');real=services.datasets.save_draft
        monkeypatch.setattr(services.datasets,'save_draft',lambda *a,**k:(_ for _ in ()).throw(AppError('TEST','模拟保存失败')));click(qtbot,d,'dataset_save_draft');qtbot.waitUntil(lambda:not d.draft_saving and '失败' in d.action_info.text(),timeout=10000);assert len(d.draft_frames())==6 and d.draft_dirty and not d.active_dataset
        monkeypatch.setattr(services.datasets,'save_draft',real);click(qtbot,d,'dataset_save_draft');qtbot.waitUntil(lambda:bool(d.active_dataset) and not d.draft_saving,timeout=10000);did=d.active_dataset
        assert not d.draft_dirty and len(services.datasets.list_datasets())==1
        d.name.setText('尚未保存改名');monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel);d.existing.setCurrentIndex(0);assert d.active_dataset==did and d.draft_dirty
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Discard);d.existing.setCurrentIndex(0);assert d.active_dataset is None and not d.allow_multi.isChecked()
        d.existing.setCurrentIndex(d.existing.findData(did));assert len(d.draft_frames())==6 and d.name.text()=='GUI持久化草稿'
        assert '尚未创建数据集版本' in d.empty_versions.text() and not d.freeze_button.isEnabled()
    finally:d.draft_dirty=False;close_window(qtbot,w)


def test_real_copy_200_restart_versions_and_training_picker(qtbot,services,tmp_path,monkeypatch):
    location=os.environ.get('IVAD_LIFECYCLE_REAL_COPY')
    if not location:pytest.skip('Requires explicitly provided independent real-project copy')
    root=Path(location).resolve();assert root!=Path(r'E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2').resolve()
    services.projects.open(str(root));w=make_window(qtbot,services);w.resize(1920,1080);w.show_page('dataset');d=w.p2.dataset;output=Path(os.environ['IVAD_LIFECYCLE_EVIDENCE']);output.mkdir(parents=True,exist_ok=True)
    try:
        qtbot.waitUntil(lambda:bool(d.all_rows) and not w.p2.refreshing,timeout=10000);cid=next(c['id'] for c in services.cameras.list() if '8525' in c['name']);d.camera.setCurrentIndex(d.camera.findData(cid));click(qtbot,d,'dataset_select_all');d.add_selected();assert len(d.draft_frames())==200
        d.tabs.setCurrentIndex(1);d.name.setText('8525压滤板破裂测试1');d.preset.setCurrentIndex(d.preset.findData('small'));d.allow_random.setChecked(True);d.allow_limited.setChecked(True);click(qtbot,d,'dataset_save_draft');qtbot.waitUntil(lambda:bool(d.active_dataset) and not d.draft_saving,timeout=10000);did=d.active_dataset;members=services.datasets.load_dataset(did)['details']['draft']['members'];assert len(members)==200
        assert w.grab().save(str(output/'01-saved-200.png'))
    finally:d.draft_dirty=False;close_window(qtbot,w)
    reopened=ApplicationServices(services.root,tmp_path/'restarted',step_seconds=.01);reopened.projects.open(str(root));second=make_window(qtbot,reopened);second.resize(1920,1080);second.show_page('dataset');d=second.p2.dataset
    try:
        qtbot.waitUntil(lambda:did in d.dataset_records and not second.p2.refreshing,timeout=15000);d.existing.setCurrentIndex(d.existing.findData(did));assert len(d.draft_frames())==200 and reopened.datasets.load_dataset(did)['details']['draft']['members']==members
        d.tabs.setCurrentIndex(1);assert second.grab().save(str(output/'02-reopened-200.png'))
        d.tabs.setCurrentIndex(2);click(qtbot,d,'dataset_split_preview');qtbot.waitUntil(lambda:d.active_validated and d.isEnabled(),timeout=15000);report=reopened.datasets.load_dataset(did)['details']['draft']['validation']['report'];assert report['source_groups']==1 and report['split_status']=='LIMITED' and report['split_counts']['val']>0 and report['split_counts']['test']==0
        assert second.grab().save(str(output/'03-limited-split.png'));monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
        d.tabs.setCurrentIndex(3);click(qtbot,d,'freeze_dataset');qtbot.waitUntil(lambda:len(reopened.datasets.versions())==1 and bool(d.version_rows),timeout=20000);first=d.version_rows[0];folder,snap=reopened.datasets.snapshot(first['id']);before=(folder/'manifest.json').read_bytes();assert snap['dataset_id']==did and len(snap['samples'])==200
        assert second.grab().save(str(output/'04-v1-frozen.png'));counts=reopened.training.preflight(first['id'])[2]
        second.show_page('training');t=second.pages['training'];t.refresh();qtbot.waitUntil(lambda:t.dataset_group.findData(did)>=0 and t.dataset.findData(first['id'])>=0,timeout=15000);assert second.grab().save(str(output/'05-training-version-picker.png'))
        second.show_page('dataset');d.tabs.setCurrentIndex(0);d.clear_selection();d.candidates.item(0,0).setCheckState(Qt.CheckState.Checked);d.remove_selected();assert len(d.draft_frames())==199 and not d.active_validated
        d.tabs.setCurrentIndex(1);click(qtbot,d,'dataset_save_draft');qtbot.waitUntil(lambda:not d.draft_saving and not d.draft_dirty,timeout=10000);assert d.active_dataset==did and len(reopened.datasets.list_datasets())==1
        d.tabs.setCurrentIndex(2);click(qtbot,d,'dataset_split_preview');qtbot.waitUntil(lambda:d.active_validated and d.isEnabled(),timeout=15000);d.tabs.setCurrentIndex(3);click(qtbot,d,'freeze_dataset');qtbot.waitUntil(lambda:len(reopened.datasets.versions())==2 and len(d.version_rows)==2,timeout=20000);assert (folder/'manifest.json').read_bytes()==before
        assert second.grab().save(str(output/'06-v1-v2-independent.png'))
        (output/'results.json').write_text(json.dumps({'dataset_id':did,'project_id':reopened.projects.current.id,'saved_members':200,'reopened_members':200,'v2_members':199,'normal_abnormal':{'normal':16,'abnormal':184},'plan':report,'training_preflight_counts':counts,'v1_unchanged':True,'versions':[{'id':v['id'],'number':v['number'],'dataset_id':v['dataset_id'],'summary':v['summary']} for v in reopened.datasets.versions()]},ensure_ascii=False,indent=2),encoding='utf-8')
    finally:d.draft_dirty=False;close_window(qtbot,second);reopened.close()


def test_gui_exit_cancel_then_save(qtbot,services,truth,monkeypatch):
    p,mids,ids,cams,label=truth;w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    qtbot.waitUntil(lambda:bool(d.all_rows) and not w.p2.refreshing,timeout=10000);d.camera.setCurrentIndex(0);d.select_all();d.allow_multi.setChecked(True);d.add_selected();d.name.setText('退出时保存草稿')
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Cancel);w.close();assert not w.is_closing and d.draft_dirty
    monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Save);w.close();qtbot.waitUntil(lambda:w.may_close,timeout=15000)
    with sqlite3.connect(Path(p.root)/'project.sqlite') as raw:
        records=raw.execute('select id,details from datasets').fetchall();assert len(records)==1 and len(json.loads(records[0][1])['draft']['members'])==6


def test_gui_dataset_version_scope_and_advanced(qtbot,services,truth):
    p,mids,ids,cams,label=truth;a=services.datasets.save_draft(draft_payload(truth));services.datasets.validate_draft(a['id']);v=services.datasets.freeze(Context(),dict(root=p.root,dataset_id=a['id'],draft_revision=1));other=draft_payload(truth);other['name']='另一独立草稿';b=services.datasets.save_draft(other)
    w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:len(d.dataset_records)==2 and not w.p2.refreshing,timeout=10000);d.existing.setCurrentIndex(d.existing.findData(a['id']));assert len(d.version_rows)==1 and d.version_rows[0]['id']==v['version_id']
        d.existing.setCurrentIndex(d.existing.findData(b['id']));assert not d.version_rows and d.draft_frames()==ids
        d.tabs.setCurrentIndex(2);assert not d.advanced_split.isVisible()
        output=Path(os.environ.get('IVAD_LIFECYCLE_GUI_EVIDENCE',str(services.data_dir/'lifecycle-gui')));output.mkdir(parents=True,exist_ok=True);geometry=[]
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(80)
            for tab in range(4):
                d.tabs.setCurrentIndex(tab);qtbot.wait(30);assert w.grab().save(str(output/f'lifecycle-{width}-tab{tab+1}.png'))
            geometry.append({'requested':[width,height],'actual':[w.width(),w.height()],'dpr':w.devicePixelRatioF()})
        (output/'geometry.json').write_text(json.dumps(geometry,indent=2),encoding='utf-8');d.tabs.setCurrentIndex(2);d.preset.setCurrentIndex(d.preset.findData('custom'));assert d.advanced_split.isVisible() and d.draft_dirty and not d.split_button.isEnabled()
    finally:d.draft_dirty=False;close_window(qtbot,w)
