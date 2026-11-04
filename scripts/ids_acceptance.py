"""Local-only acceptance; stdout/report contain counts, never private entities."""
import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import zipfile
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from ivad_app.services.ids_import_service import IdsImportService,state,commit_document,digest
from ivad_app.storage.database import Database
from ivad_app.storage.models import *
from sqlalchemy import select


def verify(root, package):
    with zipfile.ZipFile(package) as z:doc=json.loads(z.read('document.json'))
    saved=state(root)
    assert json.loads(saved['canonical'])==doc
    groups=Counter(e['kind'] for e in doc['entities'])
    entities={e['id']:e for e in doc['entities']}
    db=Database(root/'project.sqlite')
    checks=0
    try:
        with db.transaction() as s:
            reviews={e['data']['frame_id']:e for e in doc['entities'] if e['kind']=='Review'}
            annotations={a.frame_id:a for a in s.scalars(select(Annotation))}
            frames={f.id:f for f in s.scalars(select(ExtractedFrame))}
            for e in doc['entities']:
                d=e['data']
                if e['kind']=='Frame':
                    f=frames[e['id']];a=annotations[f.id]
                    assert (f.media_id,f.pts_us,f.width,f.height,f.path)==(d['video_id'],d['pts_us'],d['width'],d['height'],d['asset_path'])
                    assert f.parameters['source_timestamp_100ns']==d['source_timestamp_100ns']
                    assert f.parameters['ids']['entity']==e
                    assert a.payload['ids_state']==d['state'] and a.payload['ids_review']==reviews.get(e['id'])
                    assert f.handling['is_excluded']==bool(d.get('queue_deleted',False))
                elif e['kind']=='Annotation' and not d.get('deleted'):
                    a=annotations[d['frame_id']]
                    obj=next(o for o in a.payload['objects'] if o['id']==e['id'])
                    assert obj['label_id']==d['fault_id'] and obj['ids']['entity']==e
                    points=d['points']
                    expected=[points[0],points[1],points[2]-points[0],points[3]-points[1]] if d['shape']=='box' else list(map(list,zip(points[::2],points[1::2])))
                    assert obj['geometry']==expected
                elif e['kind']=='ROI' and not d.get('deleted'):
                    row=s.get(RegionOfInterest,e['id']);assert row.payload['ids']['entity']==e
                    assert row.camera_id==d['camera_id'] and row.payload['frame_id']==d['frame_id']
                elif e['kind']=='Camera':
                    row=s.get(Camera,e['id']);assert row.details['ids']['entity']==e
                elif e['kind']=='Video':
                    row=s.get(MediaAsset,e['id']);assert row.camera_id==d['camera_id'] and row.video['ids']['entity']==e
                elif e['kind']=='Fault':
                    row=s.get(LabelCategory,e['id']);assert json.loads(row.description)['entity']==e
                checks+=1
            assert sum(not f.handling['is_excluded'] for f in frames.values())==groups['Frame']
        assert db.integrity_check()=='ok'
    finally:db.close()
    return {'counts':dict(groups),'field_entities_checked':checks,'field_errors':0,
        'metadata':'PASS','media_assets_present':sum((root/a['path']).is_file() for a in doc['assets']),
        'media_decode':'NOT_TESTED','reopened':'PASS'}


def snapshot(root):
    with sqlite3.connect((root/'project.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        return digest({n:db.execute('SELECT * FROM "'+n+'" ORDER BY rowid').fetchall() for n, in db.execute("SELECT name FROM sqlite_master WHERE type='table'")})


def main():
    parser=argparse.ArgumentParser();parser.add_argument('private_root');parser.add_argument('--output-name',default='ids-gate');parser.add_argument('--output-root',type=Path);args=parser.parse_args()
    private=Path(args.private_root).resolve()
    repo=Path(__file__).resolve().parents[1]
    service=IdsImportService(repo/'wpf_intel/build/final/Ivad.Annotator.Dev.exe')
    reference=private/'reference';index=json.loads((reference/'04_IDS_Private_Data/IDS_PACKAGE_INDEX.json').read_text(encoding='utf-8-sig'))
    if Path(args.output_name).name!=args.output_name:raise ValueError('Invalid output name')
    output=(args.output_root or private/args.output_name).resolve();output.mkdir(exist_ok=False)
    from ivad_app.services.local_security import initialize
    initialize(output);os.environ['IVAD_IDS_CONTROLLED_ROOT']=str(output)
    results=[];targets={}
    def test(name,fn):
        try:detail=fn();entry={'name':name,'status':'PASS','detail':detail}
        except Exception as exc:entry={'name':name,'status':'FAIL','error_type':type(exc).__name__,'error':str(exc)[:180]}
        results.append(entry);print(json.dumps({'name':name,'status':entry['status']}),flush=True)
        (output/'summary.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
    packages=index['packages']
    for i,p in enumerate(packages):
        if p['mode']!='full':continue
        root=output/('package-'+str(i));targets[p['target_sha256']]=root
        def full(p=p,root=root):
            service.import_package(reference/p['path'],root)
            fields=verify(root,reference/p['path']);before=snapshot(root)
            assert service.import_package(reference/p['path'],root)['duplicate']
            assert before==snapshot(root)
            return dict(fields,classification=p['classification'],duplicate='PASS')
        test('full-'+str(i),full)
    pending=sorted([(i,p) for i,p in enumerate(packages) if p['mode']=='incremental'],key=lambda x:x[1]['sequence'])
    for i,p in pending:
        def delta(p=p):
            root=targets[p['base_sha256']];before=snapshot(root)
            try:service.import_package(reference/p['path'],root,fail_after=4)
            except RuntimeError as exc:assert str(exc)=='IDS_INJECTED_ROLLBACK'
            else:raise AssertionError('fault not injected')
            assert before==snapshot(root)
            service.import_package(reference/p['path'],root)
            fields=verify(root,reference/p['path']);before=snapshot(root)
            assert service.import_package(reference/p['path'],root)['duplicate'] and before==snapshot(root)
            targets[p['target_sha256']]=root
            return dict(fields,classification=p['classification'],rollback='PASS',duplicate='PASS')
        test('incremental-'+str(i),delta)
    synthetic=next(p for p in packages if p['classification']=='ACTUAL_EXPORTER_SYNTHETIC' and p['mode']=='full')
    def rejected(package,target):
        try:service.import_package(package,target)
        except ValueError:return {'rejected':True}
        raise AssertionError('accepted invalid package')
    delta=next(p for p in packages if p['mode']=='incremental')
    test('missing-baseline',lambda:rejected(reference/delta['path'],output/'missing-baseline'))
    for kind in ('hash','schema'):
        damaged=output/(kind+'.ids')
        with zipfile.ZipFile(reference/synthetic['path']) as src,zipfile.ZipFile(damaged,'w') as dst:
            for e in src.infolist():
                data=src.read(e.filename)
                if kind=='schema' and e.filename=='document.json':data=data.replace(b'ids/1.0',b'ids/9.0')
                if kind=='hash' and e.filename.startswith('assets/') and data:data=bytes([data[0]^1])+data[1:]
                dst.writestr(e.filename,data)
        test('reject-'+kind,lambda damaged=damaged,kind=kind:rejected(damaged,output/('reject-'+kind)))
    root=output/'class-conflict'
    service.import_package(reference/synthetic['path'],root)
    db=Database(root/'project.sqlite')
    with db.transaction() as s:s.scalar(select(LabelCategory)).name='LOCAL CONFLICT'
    db.close();before=snapshot(root)
    test('category-conflict',lambda:rejected(reference/synthetic['path'],root))
    assert before==snapshot(root)
    print(json.dumps({'passed':sum(x['status']=='PASS' for x in results),'failed':sum(x['status']=='FAIL' for x in results)}))
    return int(any(x['status']=='FAIL' for x in results))


if __name__=='__main__':raise SystemExit(main())
