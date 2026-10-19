"""Read-only source protection and fresh-copy validation. Never train or package."""
import hashlib,json,shutil,sqlite3,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
BASE=ROOT/'artifacts/p37a-contract-20261019'
OUT=(BASE/sys.argv[2]).resolve() if len(sys.argv)>2 else BASE
assert OUT.resolve().is_relative_to(BASE.resolve()),'Evidence must stay inside this round directory'
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=Path(json.loads((ROOT/'artifacts/p37a-closure-20261019/before.json').read_text(encoding='utf8'))['root'])
COPY=OUT/'project-copy'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def snapshot():
    with sqlite3.connect((SOURCE/'project.sqlite').as_uri()+'?mode=ro',uri=True) as db:
        db.row_factory=sqlite3.Row
        names=[r[0] for r in db.execute("select name from sqlite_master where type='table' order by name")]
        tables={n:sorted([dict(r) for r in db.execute('select * from "'+n+'"')],key=lambda r:json.dumps(r,sort_keys=True)) for n in names}
    files={str(p):sha(p) for p in SOURCE.rglob('*') if p.is_file() and p.name not in {'project.sqlite','project.sqlite-wal','project.sqlite-shm'}}
    for row in tables['media_assets']:
        p=Path(row['original_path']) if row.get('original_path') else None
        if p and p.is_file():files[str(p.resolve())]=sha(p)
    preserved={str(p):sha(p) for p in [ROOT/'docs/P37_IMPLEMENTATION_PLAN.md',ROOT/'reports/P36_GIT_CLOSEOUT_AND_P37_PLANNING.md',ROOT/'artifacts/p37a-20261016/regression.log',ROOT/'artifacts/p37a-closure-20261019/windows-events.json',ROOT/'artifacts/p37a-closure-20261019/wer-details.txt']}
    return dict(tables=tables,files=files,preserved=preserved)
mode=sys.argv[1]
if mode=='prepare':
    assert not COPY.exists(),'Refusing to overwrite acceptance evidence'
    before=snapshot();(OUT/'before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf8')
    COPY.mkdir()
    with sqlite3.connect((SOURCE/'project.sqlite').as_uri()+'?mode=ro',uri=True) as src,sqlite3.connect(COPY/'project.sqlite') as dst:src.backup(dst)
    shutil.copyfile(SOURCE/'project.json',COPY/'project.json')
    for n in ['datasets','models','frames']:shutil.copytree(SOURCE/n,COPY/n)
    for row in before['tables']['model_versions']:
        d=json.loads(row['details'])
        if d.get('onnx'):
            src=(SOURCE/d['onnx']['path']).resolve();dst=(COPY/d['onnx']['path']).resolve()
            assert src.is_relative_to(SOURCE.resolve()) and dst.is_relative_to(COPY.resolve())
            if not dst.exists():dst.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,dst)
    print('Prepared current independent frozen copy',COPY)
elif mode=='gpu':
    from ivad_app.core.application import ApplicationServices
    s=ApplicationServices(ROOT,OUT/'gpu-runtime')
    try:
        p=s.projects.open(str(COPY));models=s.models.versions(str(COPY));all_models=s.models.versions(str(COPY),include_archived=True)
        assert len(all_models)==len(json.loads((OUT/'before.json').read_text(encoding='utf8'))['tables']['model_versions'])
        for model in all_models:s.models.verify(model['id'],str(COPY))
        model=next(m for m in models if m.get('evaluation_protocol_sha256'))
        gpu=next(d for d in s.training.rf_devices() if d.backend_available)
        payload=dict(root=str(COPY),version_id=model['dataset_version'],model='rfdetr-nano',device_id=gpu.id,initial_model_id=model['id'],parameters=model['parameters'],operation='validate')
        s.training.configuration_preflight(payload);jid=s.jobs.submit('p3_validate',p.id,payload);deadline=time.monotonic()+300
        while s.jobs.get(jid)['state'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:
            if time.monotonic()>deadline:s.jobs.cancel(jid);raise TimeoutError('Validation timeout')
            time.sleep(.2)
        result=s.jobs.get(jid);(OUT/'gpu-validation.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');assert result['state']=='SUCCEEDED',result
        assert len(s.models.versions(str(COPY),include_archived=True))==len(all_models)
        print('Real CUDA reload SUCCEEDED',result['result'])
    finally:s.close()
elif mode=='after':
    exported=json.loads((OUT/'export-gui-final.json').read_text(encoding='utf8'))
    retained=[]
    for location in exported['exports']:
        source=Path(location);target=OUT/'verified-exports'/source.name
        assert not target.exists(),'Refusing to overwrite retained export evidence'
        shutil.copytree(source,target)
        manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf8'))
        assert all(sha(target/name)==digest for name,digest in manifest['files'].items())
        retained.append(str(target))
    (OUT/'retained-exports.json').write_text(json.dumps(retained,ensure_ascii=False,indent=2),encoding='utf8')
    after=snapshot();before=json.loads((OUT/'before.json').read_text(encoding='utf8'))
    (OUT/'after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf8')
    result=dict(tables=after['tables']==before['tables'],files=after['files']==before['files'],preserved=after['preserved']==before['preserved'],file_count=len(after['files']))
    (OUT/'integrity.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(result);assert all(result[k] for k in ['tables','files','preserved'])
else:raise ValueError(mode)
