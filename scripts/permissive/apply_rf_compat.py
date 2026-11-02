"""Apply explicit, recorded import patches ONLY to this turn's RF candidate.

Original environments/notices stay intact. Removed candidate components are
archived locally, never relabeled. Algorithm/model source is not rewritten.
"""
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT=Path(__file__).resolve().parents[2]
SITE=(ROOT/'.venv-rf-media-candidate/Lib/site-packages').resolve()
OUT=(ROOT/'artifacts/permissive-20261102/compat-overlay').resolve()

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()

if __name__=='__main__':
    assert SITE.is_relative_to(ROOT.resolve()) and OUT.is_relative_to(ROOT.resolve())
    if not SITE.is_dir() or OUT.exists():raise RuntimeError('Candidate missing or overlay already applied')
    OUT.mkdir()
    changes=[]
    for path in sorted(SITE.rglob('*.py')):
        relative=path.relative_to(SITE)
        if relative.parts[0] in {'tqdm','certifi','pip'} or '__pycache__' in relative.parts:continue
        original=path.read_text(encoding='utf8')
        new=re.sub(r'(?m)^([ \t]*)from tqdm(?=\.| import )',r'\1from ivad_app.compat.progress',original)
        new=re.sub(r'(?m)^([ \t]*)import tqdm\b(?!\.)',r'\1import ivad_app.compat.progress as tqdm',new)
        if relative.as_posix()=='requests/certs.py':
            assert 'from certifi import where' in new
            new=new.replace('from certifi import where','from ivad_app.compat.windows_trust import where')
        if relative.as_posix()=='matplotlib/__init__.py':
            new=new.replace('        import certifi','        from ivad_app.compat import windows_trust as certifi')
        if relative.as_posix()=='transformers/dependency_versions_check.py':
            assert '    "tqdm",' in new
            new=new.replace('    "tqdm",','    # Upstream tqdm replaced by explicitly versioned IVAD progress adapter.')
            new+='\nfrom ivad_app.compat.progress import __version__ as _ivad_progress_version\nif _ivad_progress_version != "ivad-progress-v1":\n    raise ImportError("Unsupported IVAD progress adapter")\n'
        if new!=original:
            backup=OUT/'original'/relative;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup)
            # Add a modification notice without displacing __future__ imports.
            new='# IVAD modification 2026-11-02: offline progress / Windows CA adapters; original license retained.\n'+new
            before=digest(path);path.write_text(new,encoding='utf8')
            changes.append(dict(path=relative.as_posix(),before_sha256=before,after_sha256=digest(path)))
    removed=[]
    for path in list(SITE.iterdir()):
        name=path.name.lower()
        if name in {'tqdm','certifi','pip'} or any(name.startswith(p+'-') and name.endswith('.dist-info') for p in ('tqdm','certifi','pip')):
            destination=(OUT/'excluded'/path.name).resolve()
            assert path.resolve().is_relative_to(SITE) and destination.is_relative_to(OUT)
            destination.parent.mkdir(exist_ok=True)
            shutil.move(str(path),str(destination))
            removed.append(path.name)
    # Existing bytecode belongs to the unpatched code. Relocate, don't erase it.
    for path in list(SITE.rglob('__pycache__')):
        if not path.is_dir():continue
        destination=(OUT/'bytecode'/path.relative_to(SITE)).resolve()
        assert path.resolve().is_relative_to(SITE) and destination.is_relative_to(OUT)
        destination.parent.mkdir(parents=True,exist_ok=True)
        shutil.move(str(path),str(destination))
    (OUT/'manifest.json').write_text(json.dumps(dict(patched=changes,excluded=removed,
        status='candidate-only; runtime tests required',remaining=['NumPy/SciPy GCC runtime','ml_dtypes Eigen MPL','full native/NOTICE clearance'],
        no_upstream_license_relabeling=True),indent=2),encoding='utf8')
    print(json.dumps(dict(patched=len(changes),excluded=removed)))
