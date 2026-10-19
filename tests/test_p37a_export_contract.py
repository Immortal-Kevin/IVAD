"""Current export contract, including an explicitly supplied real frozen copy."""
import copy,json,os,sqlite3
from pathlib import Path
from PySide6.QtWidgets import QFileDialog
from ivad_app.storage.project_store import file_hash
from tests.test_gui import make_window,close_window
from tests.test_p2_gui import click

def assert_export_contract(target,snapshot,fmt,counts):
    target=Path(target);native=json.loads((target/'ivad_native.json').read_text(encoding='utf8'))
    assert native['export_format']==fmt
    expected=copy.deepcopy(snapshot)
    for sample in expected['samples']:
        sample['source_snapshot_image']=sample['image']
        sample['image']=f"images/{sample['split']}/{sample['frame_id']}{Path(sample['image']).suffix}"
    assert {k:v for k,v in native.items() if k not in {'export_format','export_warnings'}}==expected
    samples=native['samples']
    assert (len(samples),sum(len(s['annotation']['objects']) for s in samples),sum(s['annotation']['image_tag']=='NORMAL' for s in samples))==counts
    assert all(not s['annotation']['objects'] for s in samples if s['annotation']['image_tag']=='NORMAL')
    assert len(list((target/'images').rglob('*.*')))==counts[0]
    assert all(file_hash(target/s['image'])==s['sha256'] for s in samples)
    manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf8'))
    assert manifest['state']=='COMPLETE' and manifest['format']==fmt
    assert all(file_hash(target/name)==sha for name,sha in manifest['files'].items())
    assert not (target/'data.yaml').exists() and not (target/'labels').exists()
    if fmt=='coco':
        total_images=total_objects=total_negative=0
        categories=[dict(id=c['class_id']+1,name=c['name'],label_uuid=c['uuid']) for c in snapshot['classes']]
        ids={c['uuid']:c['class_id']+1 for c in snapshot['classes']}
        for split in ['train','val','test']:
            doc=json.loads((target/f'instances_{split}.json').read_text(encoding='utf8'))
            assert doc['categories']==categories
            expected_samples={s['frame_id']:s for s in samples if s['split']==split}
            assert {i['frame_uuid'] for i in doc['images']}==set(expected_samples)
            images={i['id']:i for i in doc['images']};seen=set()
            for annotation in doc['annotations']:
                sample=expected_samples[images[annotation['image_id']]['frame_uuid']]
                obj=next(o for o in sample['annotation']['objects'] if o['id']==annotation['annotation_uuid'])
                assert obj['kind']=='box' and annotation['bbox']==obj['geometry']
                assert annotation['category_id']==ids[obj['label_id']]
                seen.add((sample['frame_id'],obj['id']))
            assert seen=={(s['frame_id'],o['id']) for s in expected_samples.values() for o in s['annotation']['objects']}
            positive={a['image_id'] for a in doc['annotations']}
            negatives={i['frame_uuid'] for i in doc['images'] if i['id'] not in positive}
            assert negatives=={s['frame_id'] for s in expected_samples.values() if s['annotation']['image_tag']=='NORMAL'}
            total_images+=len(doc['images']);total_objects+=len(doc['annotations']);total_negative+=len(negatives)
        assert (total_images,total_objects,total_negative)==counts

def gui_export_both(qtbot,w,page,snapshot,output,counts):
    assert [(page.format.itemText(i),page.format.itemData(i)) for i in range(page.format.count())]==[('IVAD Native（完整）','ivad_native'),('COCO JSON','coco')]
    assert page.format.currentData()=='ivad_native'
    results=[]
    for fmt in ['ivad_native','coco']:
        if fmt=='coco':page.format.setCurrentIndex(page.format.findData('coco'))
        assert page.format.currentData()==fmt
        click(qtbot,page,'export_dataset')
        qtbot.waitUntil(lambda:bool(list(output.glob(f'IVAD-*-{fmt}-*'))),timeout=30000)
        qtbot.waitUntil(lambda:not w.p2.tracked,timeout=30000)
        target=next(output.glob(f'IVAD-*-{fmt}-*'))
        assert_export_contract(target,snapshot,fmt,counts);results.append(str(target))
    return results

def test_real_frozen_200_native_coco_gui(qtbot,services,tmp_path,monkeypatch):
    location=os.environ.get('IVAD_P37_FROZEN_COPY')
    assert location,'Acceptance test requires an explicitly prepared independent real frozen copy; no synthetic fallback.'
    root=Path(location).resolve();assert root.is_relative_to(Path(__file__).resolve().parents[1]/'artifacts/p37a-contract-20261019')
    services.projects.open(str(root));monkeypatch.setattr(services.training.rf,'devices_snapshot',lambda:[])
    versions=services.datasets.versions(str(root));version=next(v for v in versions if v['name']=='8525test1' and v['number']==1)
    folder,snapshot=services.datasets.snapshot(version['id'],str(root));before=(folder/'manifest.json').read_bytes()
    def source_tables():
        with sqlite3.connect((root/'project.sqlite').as_uri()+'?mode=ro',uri=True) as db:
            db.row_factory=sqlite3.Row
            return {name:sorted([dict(r) for r in db.execute('select * from '+name)],key=lambda r:json.dumps(r,sort_keys=True)) for name in ['frames','media_assets','cameras','annotations','annotation_revisions','datasets','dataset_versions','dataset_samples']}
    tables_before=source_tables();frames={r['id']:r for r in tables_before['frames']};media={r['id']:r for r in tables_before['media_assets']};cameras={r['id'] for r in tables_before['cameras']}
    assert all(s['media_id']==frames[s['frame_id']]['media_id'] and s['camera_id']==media[s['media_id']]['camera_id'] and s['camera_id'] in cameras for s in snapshot['samples'])
    annotation_rows=services.annotations.frames_status(root=str(root))
    w=make_window(qtbot,services);w.show_page('dataset');page=w.p2.dataset
    try:
        qtbot.waitUntil(lambda:not w.p2.refreshing and page.existing.findData(snapshot['dataset_id'])>=0,timeout=15000)
        page.existing.setCurrentIndex(page.existing.findData(snapshot['dataset_id']));page.tabs.setCurrentIndex(3)
        qtbot.waitUntil(lambda:any(v['id']==version['id'] for v in page.version_rows),timeout=15000)
        page.versions.selectRow(next(i for i,v in enumerate(page.version_rows) if v['id']==version['id']))
        monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(tmp_path))
        exports=gui_export_both(qtbot,w,page,snapshot,tmp_path,(200,402,16))
        assert (folder/'manifest.json').read_bytes()==before
        assert services.datasets.snapshot(version['id'],str(root))[1]==snapshot
        assert services.annotations.frames_status(root=str(root))==annotation_rows
        assert services.datasets.versions(str(root))==versions
        assert source_tables()==tables_before
        evidence=os.environ.get('IVAD_P37_CONTRACT_EVIDENCE')
        if evidence:Path(evidence).write_text(json.dumps(dict(images=200,objects=402,normal=16,version_id=version['id'],exports=exports,source_snapshot_unchanged=True,source_tables_unchanged=True,camera_media_frame_links=True),ensure_ascii=False,indent=2),encoding='utf8')
    finally:page.draft_dirty=False;close_window(qtbot,w)
