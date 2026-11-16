"""Remove retired NumPy binary with GPL runtime and YOLO-only visualization/build deps.
Preserve file hashes and declared license evidence, not restricted binaries.
"""
import hashlib, importlib.metadata as md, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; OUT=ROOT/'governance/evidence'
names={'numpy','opencv-python','matplotlib','setuptools'}
rows=[]; jobs=[];wheel_files=[]
for env in (ROOT/'.venvs').iterdir():
    for d in md.distributions(path=[str(env/'Lib/site-packages')]):
        if d.metadata['Name'].lower() not in names: continue
        jobs.append((env,d.metadata['Name']))
        for f in d.files or []:
            p=Path(d.locate_file(f)).resolve()
            if not p.is_relative_to(ROOT): raise RuntimeError('Outside project')
            if p.is_file():
                with p.open('rb') as stream: sha=hashlib.file_digest(stream,'sha256').hexdigest()
                rows.append(dict(path=str(p.relative_to(ROOT)),sha256=sha,bytes=p.stat().st_size,package=d.metadata['Name']))
for p in (ROOT/'artifacts/p0/wheels').iterdir():
    if p.is_file() and p.name.startswith(('numpy-','opencv_python-','matplotlib-','setuptools-')):
        with p.open('rb') as f: sha=hashlib.file_digest(f,'sha256').hexdigest()
        rows.append(dict(path=str(p.relative_to(ROOT)),sha256=sha,bytes=p.stat().st_size,package='retired-wheel'));wheel_files.append(p)
(OUT/'incompatible_legacy_deletion_manifest.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
for env,name in jobs:
    r=subprocess.run([str(env/'Scripts/python.exe'),'-m','pip','uninstall','-y',name],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=120)
    (OUT/('remove_'+env.name+'_'+name+'.log')).write_text(r.stdout+r.stderr,encoding='utf-8')
    if r.returncode: raise RuntimeError(name)
for p in wheel_files:p.unlink()
print('removed',len(rows),'files; old GPU environments now retired, NOT usable training locks')
