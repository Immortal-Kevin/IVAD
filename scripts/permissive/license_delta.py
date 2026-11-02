"""Reuse P37-L evidence, verify actual metadata, and apply the user's strict policy.

Classification is engineering disposition, not a legal certification. Original
notices are referenced unchanged; native payload uncertainties fail closed.
"""
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import re
import subprocess

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/permissive-20261102'
ENVS={'gui':'.venv-p1','rf':'.venv-rfdetr','legacy':'.venv-nvidia','lite-build':'.venv-distribution'}

def canonical(value):return re.sub(r'[-_.]+','-',value).lower()
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    prior=json.loads((ROOT/'legal/licenses/p37l/SBOM.json').read_text(encoding='utf8'))
    installed={env:{canonical(d.metadata['Name']):d for d in distributions(path=[str(ROOT/path/'Lib/site-packages')])} for env,path in ENVS.items()}
    inference=json.loads((OUT/'rf-inference-compat/result.json').read_text(encoding='utf8'))
    modules=set(n.split('.')[0] for n in inference['python_imports'])
    rows=[]
    replace={'pyside6','pyside6-addons','pyside6-essentials','shiboken6','av','certifi','tqdm','numpy','scipy','ml-dtypes'}
    native_review={'torch','torchvision','onnxruntime-gpu','opencv-python-headless','opencv-python','onnx','onnxsim','pyarrow','pillow','tokenizers','hf-xet'}
    for old in prior:
        name=canonical(old['component']);env=old['environment'];dist=installed.get(env,{}).get(name)
        metadata=Path(dist._path)/'METADATA' if dist else None
        # Historical audit hashes normalized metadata text, not wheel CRLF bytes.
        matches=bool(metadata and metadata.exists() and hashlib.sha256((dist.read_text('METADATA') or '').encode()).hexdigest()==old['metadata_sha256'])
        policy='UNVERIFIED'
        reason='Reuse prior notices; unresolved evidence remains unresolved.'
        if env=='legacy':policy='HISTORICAL_ONLY';reason='Preserved legacy environment; not an approved target runtime.'
        elif name in replace:
            policy='REPLACE'
            reason='User excludes copyleft even where a commercial-use exception might exist.'
        elif name in native_review:
            reason='Native/transitive payload needs component-level clearance; top-level license is insufficient.'
        elif name in {'pip','setuptools','pytest','pytest-qt','pyinstaller','pyinstaller-hooks-contrib','altgraph'}:
            policy='REMOVE_FROM_RUNTIME';reason='Build/test tooling, not a required runtime feature.'
        elif matches and 'LicenseRef' not in old['spdx'] and old['spdx']!='NOASSERTION':
            policy='RETAIN';reason='Retain under identified upstream license and notices; not a distribution approval.'
        elif not matches:
            reason='Installed metadata differs or component missing; prior evidence cannot silently be reused.'
        rows.append(dict(environment=env,component=old['component'],version=dist.version if dist else None,
                         prior_version=old['version'],prior_spdx=old['spdx'],metadata_matches=matches,
                         actual_metadata_bytes_sha256=digest(metadata) if metadata and metadata.exists() else None,
                         policy=policy,reason=reason,source=old['source_url'],notice_files=old['notice_files'],
                         historical_status=old['audit_status']))
    for row in rows:
        if canonical(row['component']) in {'numpy','scipy'}:
            row['binary_warning']='Bundled Windows OpenBLAS license identifies statically linked GPL-3.0-or-later WITH GCC-exception-3.1. Strict no-GPL policy requires another build; do not treat top-level BSD as sufficient.'
    refs=subprocess.check_output(['git','for-each-ref','--format=%(refname) %(objectname)','refs/heads'],cwd=ROOT,text=True).splitlines()
    matches=subprocess.check_output(['git','log','--all','--format=%H','-G','PySide6|import av|ultralytics','--','ivad_app','requirements-p1.txt','requirements-p2.txt'],cwd=ROOT,text=True).splitlines()
    data=dict(policy='No GPL/AGPL/LGPL/MPL necessary target runtime; no paid licenses',distribution='BLOCKED',
              baseline_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
              refs=refs,history_matching_commits=sorted(set(matches)),prior_source='legal/licenses/p37l/SBOM.json',
              records=rows,rf_observed_top_level_modules=sorted(modules),
              scope_limit='No final WPF/IDS payload exists. Build variants, native DLL provenance and source-level embedded third-party notices remain subject to review.')
    data['candidate_inventories']={}
    for candidate in ['.venv-media-native-v2','.venv-rf-media-candidate']:
        data['candidate_inventories'][candidate]=sorted([
            dict(name=d.metadata['Name'],version=d.version)
            for d in distributions(path=[str(ROOT/candidate/'Lib/site-packages')])
        ],key=lambda r:r['name'].lower())
    data['candidate_changes']={
        'media':'8-package service candidate excludes Qt, PyAV, OpenCV and NumPy. Existing GUI remains legacy.',
        'rf':'Candidate excludes PyAV, OpenCV FFmpeg DLL, tqdm, certifi and pip. 47 import patches recorded in local compat-overlay manifest; original environments untouched.',
        'remaining':'RF NumPy/SciPy GCC runtime, optional ml_dtypes Eigen, unverified native provenance, Windows codecs and CUDA redistribution remain blocked. No final GUI/IDS runtime exists.'}
    target=ROOT/'legal/NVIDIA_PERMISSIVE_DEPENDENCY_DELTA.json'
    target.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(dict(records=len(rows),metadata_matches=sum(r['metadata_matches'] for r in rows),
                         classifications={p:sum(r['policy']==p for r in rows) for p in ['RETAIN','REPLACE','REMOVE_FROM_RUNTIME','HISTORICAL_ONLY','UNVERIFIED']},
                         history_matching_commits=len(set(matches)))))

if __name__=='__main__':main()
