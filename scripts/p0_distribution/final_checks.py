"""Read-only original checks and transaction regression on an isolated copy."""
import hashlib,json,os,shutil,sqlite3,sys
from pathlib import Path
from sqlalchemy import select
repo=Path(__file__).resolve().parents[2];sys.path.insert(0,str(repo))
from ivad_app.services.local_security import initialize,authorize
from ivad_app.storage.project_store import ProjectStore
from ivad_app.storage.models import ProjectRecord
from ivad_app.services.ids_bridge import execute
private=Path(sys.argv[1]);before=json.loads((private/'protected-before.json').read_text(encoding='utf8'))
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
changed=[p for p,h in before['files'].items() if sha(p)!=h]
workspace=private/'historical-copy';initialize(workspace);os.environ['IVAD_IDS_CONTROLLED_ROOT']=str(workspace)
source=Path(next(iter(before['tables'])));target=workspace/'project';target.mkdir()
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as old,sqlite3.connect(target/'project.sqlite') as new:old.backup(new)
shutil.copy2(source.parent/'project.json',target/'project.json')
authorize(target,'identity');store=ProjectStore(None)
with store.open(str(target)) as (_,db,pid):
 with db.transaction() as s:
  row=s.get(ProjectRecord,pid);original=row.name;row.name='isolated-read-write-check'
 try:
  with db.transaction() as s:
   row=s.get(ProjectRecord,pid);assert row.name=='isolated-read-write-check';row.name='must-roll-back';raise RuntimeError('INJECTED')
 except RuntimeError:pass
 with db.transaction() as s:assert s.get(ProjectRecord,pid).name=='isolated-read-write-check';s.get(ProjectRecord,pid).name=original
 assert db.integrity_check()=='ok'
try:execute({'action':'hydrate','root':str(target)})
except ValueError as exc:
 assert 'LEGACY_PROJECT_REQUIRES_VALIDATED_IDS_COPY' in str(exc);gui={'status':'FAIL','reason':'legacy NVIDIA project has no canonical IDS projection; guarded rejection, no automatic rewrite'}
else:gui={'status':'NOT TESTED','reason':'unexpected hydration result'}
# The original source must remain byte-identical after the read/write copy test.
assert sha(source)==before['files'][str(source)]
result={'protected_file_count':len(before['files']),'original_changes':changed,'original_integrity':'PASS' if not changed else 'FAIL',
 'historical_storage_read_write':'PASS','historical_transaction_rollback':'PASS','historical_WPF_compatibility':gui}
(private/'final-checks.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result));assert not changed
