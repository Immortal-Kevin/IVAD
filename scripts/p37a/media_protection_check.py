"""Hash only paths already registered in the protected project. No video decoding or scan."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-20261016';b=json.loads((OUT/'before/inventory.json').read_text(encoding='utf8'));project=Path(b['root']);cache={};rows=[]
for r in b['tables']['media_assets']:
    values=[]
    for kind,path in [('project_file',project/r['path'] if r['path'] else None),('original_source',Path(r['original_path']) if r['original_path'] else None)]:
        if path and path.is_file():
            key=str(path.resolve())
            if key not in cache:
                with path.open('rb') as stream:cache[key]=hashlib.file_digest(stream,'sha256').hexdigest()
            values.append(dict(kind=kind,path=key,sha256=cache[key],matches_registered_sha256=cache[key]==r['sha256']))
        else:values.append(dict(kind=kind,status='NO_REGISTERED_FILE_OR_MISSING',original_state=r['state']))
    rows.append(dict(media_id=r['id'],state_at_baseline=r['state'],files=values))
result=dict(status='PASS' if all(f.get('matches_registered_sha256',True) for row in rows for f in row['files']) else 'BLOCKED',unique_files_hashed=len(cache),records=rows)
(OUT/'media-protection.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');print(json.dumps(dict(status=result['status'],unique_files_hashed=len(cache),records=len(rows))))
