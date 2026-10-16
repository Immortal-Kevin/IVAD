import copy,json,os
from pathlib import Path
from uuid import uuid4
import pytest
from sqlalchemy import select
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QMessageBox,QFileDialog
from ivad_app.core.contracts import AppError
from ivad_app.storage.models import Annotation,ExtractedFrame,MediaAsset
from tests.test_p2_services import media_project
from tests.test_p2_media import sample_videos,Context
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click

@pytest.fixture
def truth(services,media_project):
    p,mids,ids=media_project;label=services.annotations.labels()[0]['id'];cams=[];chosen=[]
    for i,mid in enumerate(mids):
        cam=services.cameras.save('测试摄像头 '+str(i),root=p.root,mode='CREATE');cams.append(cam['id']);services.cameras.associate(mid,cam['id'],None,p.root)
        frames=[f for f in services.media.frames() if f['media_id']==mid]
        for j,f in enumerate(frames[:2]):
            services.annotations.save(f['id'],{'image_tag':'NORMAL' if j else 'ABNORMAL','objects':[] if j else [{'id':str(uuid4()),'kind':'box','geometry':[10,10,30,30],'label_id':label}]},None,0)
            chosen.append(f['id'])
    return p,mids,chosen,cams,label

def payload(p,ids,**values):return dict(root=p.root,name='独立实验数据集',frame_ids=ids,strategy='source',admission='experimental',allow_limited=True,allow_multi_camera=True,**values)

def test_auto_admission_preserves_review_and_export(services,truth,tmp_path):
    p,mids,ids,cams,label=truth;before=[services.annotations.load(f) for f in ids]
    assert not services.datasets.candidates()
    preview=services.datasets.preview(ids,admission='experimental');assert preview['count']==6 and not preview['issues']
    r=services.datasets.freeze(Context(),payload(p,ids));folder,snap=services.datasets.snapshot(r['version_id'])
    assert snap['admission']['scope']=='EXPERIMENT_ONLY' and not snap['admission']['independent_review']
    assert all(s['annotation_status']=='DRAFT' and s['validation_level']=='AUTO_CHECKED_HUMAN' for s in snap['samples'])
    services.training.preflight(r['version_id']);out=services.datasets.export(Context(),dict(root=p.root,version_id=r['version_id'],format='yolo_detect',parent=str(tmp_path)))
    files=list((Path(out['path'])/'labels').rglob('*.txt'));assert len(files)==6 and sum(not f.read_text().strip() for f in files)==3
    assert [services.annotations.load(f) for f in ids]==before

def test_invalid_truth_rejected_and_classification_not_detection(services,truth):
    p,mids,ids,cams,label=truth;f=ids[1]
    services.annotations.save(f,{'image_tag':'ABNORMAL','objects':[],'image_label_id':label},None,1)
    result=services.datasets.preview([f],admission='experimental');assert result['issues'] and not result['samples']
    with pytest.raises(AppError):services.datasets.freeze(Context(),payload(p,[f]))
    rows={r['id']:r for r in services.datasets.screening()};assert rows[f]['fault_text']=='整帧异常 / 无目标框' and not rows[f]['eligible']
    services.annotations.batch_apply(services.annotations.batch_preview([ids[0]],'exclude'),'TEST FIXTURE')
    assert services.datasets.preview([ids[0]],admission='experimental')['issues']
    with services.store.open() as (_,db,_),db.transaction() as s:
        doc=s.scalar(select(Annotation).where(Annotation.frame_id==ids[2]));data=copy.deepcopy(doc.payload);data['objects'][0]['geometry']=[-1,0,2000,20];doc.payload=data
    assert services.datasets.preview([ids[2]],admission='experimental')['issues']

@pytest.mark.parametrize('strategy',['source','camera','random'])
def test_split_reproducible_and_risks(services,truth,strategy):
    p,mids,ids,cams,label=truth;opts=dict(strategy=strategy,seed=123,allow_leakage=True)
    a=services.datasets.split_preview(ids,**opts);b=services.datasets.split_preview(ids,**opts)
    assert [(s['frame_id'],s['split']) for s in a['samples']]==[(s['frame_id'],s['split']) for s in b['samples']]
    assert sum(a['split_counts'].values())==6 and all(a['split_counts'].values())
    if strategy=='random':assert a['split_status']=='LIMITED'
    else:
        key='source_group_id' if strategy=='source' else 'camera_id'
        assert all(len({b['split'] for b in a['samples'] if b[key]==s[key]})==1 for s in a['samples'])

def test_insufficient_groups_ratio_and_multi_consent(services,truth):
    p,mids,ids,cams,label=truth
    with pytest.raises(AppError,match='100'):services.datasets.split_preview(ids,ratios=[70,20,20])
    with pytest.raises(AppError,match='确认'):services.datasets.split_preview(ids,strategy='random')
    result=services.datasets.split_preview(ids[:2],strategy='camera');assert result['split_status']=='LIMITED' and not result['split_counts']['val']
    v=payload(p,ids[:2]);v['allow_limited']=False
    with pytest.raises(AppError,match='LIMITED'):services.datasets.freeze(Context(),v)
    v=payload(p,ids);v['allow_multi_camera']=False
    with pytest.raises(AppError,match='摄像头'):services.datasets.freeze(Context(),v)

def test_clip_lineage_and_snapshot_immutability(services,truth):
    p,mids,ids,cams,label=truth
    with services.store.open() as (_,db,_),db.transaction() as s:
        child=s.get(MediaAsset,mids[1]);child.parent_id=mids[0];child.kind='CLIP'
    result=services.datasets.split_preview(ids,strategy='source');by={s['media_id']:s for s in result['samples']}
    assert by[mids[1]]['source_group_id']==mids[0] and by[mids[0]]['split']==by[mids[1]]['split']
    r=services.datasets.freeze(Context(),payload(p,ids));folder,snap=services.datasets.snapshot(r['version_id']);before=(folder/'manifest.json').read_bytes()
    services.annotations.batch_apply(services.annotations.batch_preview([ids[0]],'exclude'),'TEST FIXTURE')
    assert (folder/'manifest.json').read_bytes()==before
    with pytest.raises(AppError):services.training.preflight(r['version_id'])
    services.annotations.batch_apply(services.annotations.batch_preview([ids[0]],'restore'))
    assert services.annotations.load(ids[0])['payload']['objects']

def test_tampered_experimental_admission_rejected(services,truth,monkeypatch):
    p,mids,ids,cams,label=truth;r=services.datasets.freeze(Context(),payload(p,ids));folder,snap=services.datasets.snapshot(r['version_id']);snap=copy.deepcopy(snap);snap['samples'][0]['validation_level']='NOT_CHECKED'
    monkeypatch.setattr(services.datasets,'snapshot',lambda *args:(folder,snap))
    with pytest.raises(AppError):services.training.preflight(r['version_id'])

def test_four_tabs_filter_sort_draft_batch_freeze_and_export(qtbot,services,truth,tmp_path,monkeypatch):
    p,mids,ids,cams,label=truth;services.annotations.batch_apply(services.annotations.batch_preview([ids[1]],'exclude'),'TEST FIXTURE')
    w=make_window(qtbot,services);w.show_page('dataset');d=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:bool(d.all_rows) and not w.p2.refreshing,timeout=10000)
        assert [d.tabs.tabText(i) for i in range(4)]==['图片列表与筛查','新建数据集','训练集划分设置','数据集版本']
        assert not hasattr(w.p2.hotfix,'review_table')
        assert d.camera.currentData()==cams[0] and not any(r['excluded'] for r in d.candidate_rows)
        d.select_all();d.camera.setCurrentIndex(d.camera.findData(cams[1]));assert not d.selected_frames() and all(r['camera_id']==cams[1] for r in d.candidate_rows)
        d.fault.setCurrentIndex(d.fault.findData(label));assert all(label in r['fault_ids'] for r in d.candidate_rows)
        d.source.setCurrentIndex(d.source.findData(mids[1]));assert all(r['media_id']==mids[1] for r in d.candidate_rows)
        d.select_all();d.omit_selected();assert not d.candidate_rows;d.restore_omitted();assert d.candidate_rows
        d.fault.setCurrentIndex(0);d.source.setCurrentIndex(0);d.camera.setCurrentIndex(0);d.select_all();d.allow_multi.setChecked(True);d.add_selected();assert len(d.draft_frames())==5
        d.candidates.sortItems(2,Qt.SortOrder.DescendingOrder);d.clear_selection();d.select_all();assert set(d.selected_frames())=={r['id'] for r in d.candidate_rows if r['eligible']}
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
        d.name.setText('GUI实验数据集');d.validation_mode.setCurrentIndex(0);d.tabs.setCurrentIndex(1);click(qtbot,d,'dataset_save_draft');qtbot.waitUntil(lambda:bool(d.active_dataset) and not d.draft_saving,timeout=10000);d.tabs.setCurrentIndex(2);click(qtbot,d,'dataset_split_preview');qtbot.waitUntil(lambda:'split_status' in d.split_detail.toPlainText(),timeout=10000)
        output=Path(os.environ.get('IVAD_DATASET_EVIDENCE',str(tmp_path/'screens')));output.mkdir(parents=True,exist_ok=True)
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(80)
            for tab in range(4):
                d.tabs.setCurrentIndex(tab);qtbot.wait(50);assert w.grab().save(str(output/f'dataset-{width}-tab{tab+1}.png'))
        monkeypatch.setattr(QMessageBox,'question',lambda *a,**k:QMessageBox.StandardButton.Yes)
        d.tabs.setCurrentIndex(3);click(qtbot,d,'freeze_dataset');qtbot.waitUntil(lambda:len(services.datasets.versions())==1,timeout=15000);qtbot.waitUntil(lambda:bool(d.version_rows),timeout=10000)
        d.versions.selectRow(0);click(qtbot,d,'dataset_check_version');qtbot.waitUntil(lambda:'source_trace' in d.detail.toPlainText(),timeout=10000);monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path));click(qtbot,d,'export_dataset');qtbot.waitUntil(lambda:bool(list(tmp_path.glob('IVAD-*-yolo_detect-*'))),timeout=15000)
        # Restore the excluded frame using real controller action; old payload remains.
        d.tabs.setCurrentIndex(0);d.exclusion.setCurrentIndex(1)
        for i in range(d.candidates.rowCount()):d.candidates.item(i,0).setCheckState(Qt.CheckState.Checked)
        click(qtbot,d,'dataset_restore');qtbot.waitUntil(lambda:not services.annotations.frames_status()[ids[1]]['processing_state']=='EXCLUDED' and d.isEnabled(),timeout=10000)
        assert services.annotations.load(ids[1])['payload']['image_tag']=='NORMAL'
    finally:d.draft_dirty=False;close_window(qtbot,w)


def test_single_camera_source_split_and_freeze_conflict(services,truth):
    p,mids,ids,cams,label=truth
    for i,mid in enumerate(mids[1:],1):services.cameras.associate(mid,cams[0],cams[i],p.root)
    r=services.datasets.freeze(Context(),payload(p,ids));assert services.training.preflight(r['version_id'])[2]['val']>0
    class ChangeContext(Context):
        changed=False
        def progress(self,value):
            if not self.changed:
                self.changed=True;services.cameras.associate(mids[0],cams[1],cams[0],p.root)
    with pytest.raises(AppError,match='摄像头'):services.datasets.freeze(ChangeContext(),payload(p,ids))
    assert len(services.datasets.versions())==1


def test_duplicate_hash_and_rejected_review(services,truth):
    p,mids,ids,cams,label=truth
    with services.store.open() as (folder,db,_),db.transaction() as s:
        a=s.get(ExtractedFrame,ids[0]);b=s.get(ExtractedFrame,ids[2]);b.path=a.path;b.sha256=a.sha256;b.perceptual_hash=a.perceptual_hash
    result=services.datasets.split_preview(ids);assert result['count']==5 and any('SHA256' in w for w in result['warnings'])
    services.annotations.review_frames({ids[0]:1},'REJECTED')
    assert services.datasets.preview([ids[0]],admission='experimental')['issues']


def test_frozen_version_integrity_reports_corrupt_image(services,truth):
    p,mids,ids,cams,label=truth;r=services.datasets.freeze(Context(),payload(p,ids));result=services.datasets.check_version(r['version_id']);assert result['status']=='PASS' and len(result['source_trace'])==6
    folder,snap=services.datasets.snapshot(r['version_id']);(folder/snap['samples'][0]['image']).write_bytes(b'corrupt test fixture')
    assert services.datasets.check_version(r['version_id'])['status']=='BLOCKED'
