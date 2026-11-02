"""Read-only patch verification; never seal a partially modified candidate."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/permissive-20261102'

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def verify():
    manifest=json.loads((OUT/'compat-overlay/manifest.json').read_text(encoding='utf8'))
    source=ROOT/'.venv-rfdetr/Lib/site-packages'
    candidate=ROOT/'.venv-rf-media-candidate/Lib/site-packages'
    checks=[]
    for row in manifest['patched']:
        path=Path(row['path'])
        if path.is_absolute() or '..' in path.parts:raise ValueError('Unsafe manifest path')
        upstream=digest(source/path)
        checks.append(dict(path=row['path'],current_matches=digest(candidate/path)==row['after_sha256'],
                           upstream_sha256=upstream,manifest_before_matches_upstream=upstream==row['before_sha256']))
    absent=all(not (candidate/name).exists() for name in manifest['excluded'])
    assert checks and absent and all(r['current_matches'] and r['manifest_before_matches_upstream'] for r in checks)
    result=dict(checks=checks,excluded_absent=absent)
    target=OUT/'compat-sealed.json'
    if target.exists():
        previous=json.loads(target.read_text(encoding='utf8'))
        assert previous['checks']==checks and previous['excluded_absent']==absent
    else:target.write_text(json.dumps(result,indent=2),encoding='utf8')
    print(json.dumps(dict(status='PASS',checked=len(checks),excluded_absent=absent)))

if __name__=='__main__':verify()
