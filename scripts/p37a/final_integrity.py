"""Read-only comparison of protected user data and planning documents."""
import json,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-20261016'
before=json.loads((OUT/'before/inventory.json').read_text(encoding='utf8'));after=json.loads((OUT/('final-after' if (OUT/'final-after/inventory.json').exists() else 'after')/'inventory.json').read_text(encoding='utf8'))
planning=json.loads((OUT/'untracked-planning-protection.json').read_text(encoding='utf8'))
hash_file=lambda p:hashlib.file_digest(Path(p).open('rb'),'sha256').hexdigest()
unchanged={p:hash_file(ROOT/p)==digest for p,digest in planning.items()}
frames={r['id']:hash_file(Path(before['root'])/r['path'])==r['sha256'] for r in before['tables']['frames']}
old=json.loads((ROOT/'artifacts/p36-rfdetr-20261016/dependency-audit/p36-rfdetr/inventory.json').read_text(encoding='utf8'))
now=json.loads((OUT/'license-audit/rf-all/inventory.json').read_text(encoding='utf8'))
metadata=lambda inv:{r['name']:(r['version'],r['metadata_sha256']) for r in inv['packages']}
result=dict(status='PASS' if before==after and all(unchanged.values()) and all(frames.values()) and metadata(old)==metadata(now) else 'BLOCKED',tables_identical=before['tables']==after['tables'],protected_files_identical=before['files']==after['files'],protected_file_count=len(before['files']),frames_checked=len(frames),frames_valid=all(frames.values()),planning_unchanged=unchanged,rf_environment_metadata_unchanged=metadata(old)==metadata(now))
(OUT/'integrity-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(result));assert result['status']=='PASS'
