"""Read-only project inventory; SQLite online backup; never open the business store."""
import hashlib,json,sqlite3,sys
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2]);out.mkdir(parents=True,exist_ok=True)
db=sqlite3.connect((root/'project.sqlite').as_uri()+'?mode=ro',uri=True)
with sqlite3.connect(out/'project.backup.sqlite') as backup:db.backup(backup)
tables={r[0]:[dict(zip([c[0] for c in cur.description],row)) for row in cur.fetchall()] for r in db.execute("select name from sqlite_master where type='table'").fetchall() if (cur:=db.execute('select * from "'+r[0]+'"'))}
db.close()
files={}
for folder in ['datasets','models','training']:
 for p in (root/folder).rglob('*'):
  if p.is_file():files[p.relative_to(root).as_posix()]=hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
for name in ['project.json']:
 p=root/name
 if p.exists():files[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'inventory.json').write_text(json.dumps({'root':str(root),'tables':tables,'files':files},ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'tables':{k:len(v) for k,v in tables.items()},'protected_files':len(files),'runs':[r['id'] for r in tables.get('training_runs',[])],'models':[r['id'] for r in tables.get('model_versions',[])]},ensure_ascii=False))
