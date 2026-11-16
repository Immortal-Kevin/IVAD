"""User-authorized v1.1 cleanup. Evidence before deletion; never traverse outside ROOT."""
import csv, hashlib, importlib.metadata as md, json, os, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'governance/evidence'
OUT.mkdir(parents=True, exist_ok=True)
def digest(p):
    with p.open('rb') as f: return hashlib.file_digest(f, 'sha256').hexdigest()
def safe(p):
    p = p.resolve()
    if not p.is_relative_to(ROOT) or p == ROOT: raise RuntimeError(str(p))
    return p
def inventory():
    rows=[]
    for env in (ROOT/'.venvs').iterdir():
        for d in md.distributions(path=[str(env/'Lib/site-packages')]):
            rows.append(dict(environment=env.name, name=d.metadata['Name'], version=d.version,
                license=d.metadata.get('License-Expression') or d.metadata.get('License'),
                classifiers=d.metadata.get_all('Classifier', []), metadata_path=str(d._path.relative_to(ROOT))))
    return rows
before=inventory()
(OUT/'legacy_installed_before.json').write_text(json.dumps(before,ensure_ascii=False,indent=2),encoding='utf-8')
targets=set()
# Exclusively retired-model scripts. Generic network, GPU, hashing and resume tools stay.
for name in ['yolo_probe.py','download_assets.py','fetch_wheels.py','prepare_offline_handoff.py','finalize_resume_reports.py']:
    targets.add(ROOT/'scripts/p0'/name)
for p in (ROOT/'artifacts/p0').iterdir():
    if p.name in ['config','matplotlib','runs','synthetic','bus.jpg','sources_resume.json'] or p.name.startswith('yolo'):
        targets.add(p)
targets.add(ROOT/'reports/history/config_fallback_20261014')
for p in (ROOT/'artifacts/p0/wheels').rglob('*'):
    if p.is_file() and 'ultralytics' in p.name.lower(): targets.add(p)
for p in (ROOT/'reports/raw').iterdir():
    if p.name.startswith(('yolo','ultralytics','model_','bus_')) or p.name in ['download_assets.log','fetch_wheels.log','direct_download_20261014_models.log']:
        targets.add(p)
packages=[]
for env in (ROOT/'.venvs').iterdir():
    for d in md.distributions(path=[str(env/'Lib/site-packages')]):
        if d.metadata['Name'].lower().startswith('ultralytics'):
            packages.append((env,d.metadata['Name']))
            for f in d.files or []:
                p=safe(Path(d.locate_file(f)))
                if p.is_file(): targets.add(p)
files={f for p in targets if p.exists() for f in ([p] if p.is_file() else p.rglob('*')) if f.is_file()}
evidence=[dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=digest(p),reason='Retired Ultralytics-only experiment/package asset') for p in sorted(files)]
(OUT/'legacy_deletion_manifest.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf-8')
for env,name in packages:
    r=subprocess.run([str(env/'Scripts/python.exe'),'-m','pip','uninstall','-y',name],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=90)
    (OUT/('uninstall_'+name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode: raise RuntimeError('Uninstall failed '+name)
for p in sorted(targets,key=lambda x:len(str(x)),reverse=True):
    p=safe(p)
    if p.is_file(): p.unlink()
    elif p.is_dir(): shutil.rmtree(p)
# Filter reusable dependency manifests rather than delete their generic entries.
rewrites=[]
for p in list((ROOT/'reports/raw').glob('*.txt'))+list((ROOT/'reports/raw').glob('*.json')):
    if p.name.startswith('vpn_'): continue
    original=p.read_text(encoding='utf-8-sig')
    if 'ultralytics' not in original.lower(): continue
    if p.suffix=='.txt':
        updated='\n'.join(line for line in original.splitlines() if 'ultralytics' not in line.lower())+'\n'
    else:
        obj=json.loads(original)
        def clean(x):
            if isinstance(x,list):
                return [clean(v) for v in x if not (isinstance(v,dict) and str(v.get('name',v.get('package',''))).lower().startswith('ultralytics')) and not (isinstance(v,str) and 'ultralytics' in v.lower())]
            if isinstance(x,dict): return {k:clean(v) for k,v in x.items() if 'ultralytics' not in k.lower()}
            return x
        updated=json.dumps(clean(obj),ensure_ascii=False,indent=2)
    if updated!=original:
        rewrites.append(dict(path=str(p.relative_to(ROOT)),before_sha256=hashlib.sha256(original.encode()).hexdigest(),purpose='Remove retired dependency entries; retained manifest is historical, not install authorization'))
        p.write_text(updated,encoding='utf-8')
(OUT/'legacy_manifest_changes.json').write_text(json.dumps(rewrites,ensure_ascii=False,indent=2),encoding='utf-8')
after=inventory()
(OUT/'legacy_installed_after.json').write_text(json.dumps(after,ensure_ascii=False,indent=2),encoding='utf-8')
assert not any(r['name'].lower().startswith('ultralytics') for r in after)
print(json.dumps(dict(deleted_files=len(evidence),deleted_bytes=sum(e['bytes'] for e in evidence),packages=[n for _,n in packages],retained_generic_packages=len(after))))
