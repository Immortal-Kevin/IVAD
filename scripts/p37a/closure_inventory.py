"""Read-only, current original-project snapshot. Run before/after; no ORM writes."""
import hashlib,json,sqlite3,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/p37a-closure-20261019';OUT.mkdir(exist_ok=True)
project=Path(json.loads((ROOT/'artifacts/p37a-20261016/before/inventory.json').read_text(encoding='utf8'))['root'])
digest=lambda p:hashlib.file_digest(p.open('rb'),'sha256').hexdigest()
db=sqlite3.connect((project/'project.sqlite').as_uri()+'?mode=ro',uri=True)
db.row_factory=sqlite3.Row
tables={}
for row in db.execute("select name from sqlite_master where type='table' order by name"):
    name=row[0];tables[name]=sorted([dict(r) for r in db.execute('select * from "'+name.replace('"','""')+'"')],key=lambda r:json.dumps(r,sort_keys=True))
files={str(p):digest(p) for p in project.rglob('*') if p.is_file() and p.name not in {'project.sqlite','project.sqlite-wal','project.sqlite-shm'}}
for r in tables.get('media_assets',[]):
    p=Path(r['original_path']) if r.get('original_path') else None
    if p and p.is_file():files[str(p.resolve())]=digest(p)
planning={str(ROOT/p):digest(ROOT/p) for p in ['docs/P37_IMPLEMENTATION_PLAN.md','reports/P36_GIT_CLOSEOUT_AND_P37_PLANNING.md']}
result=dict(root=str(project),tables=tables,files=files,planning=planning)
target=OUT/(sys.argv[1]+'.json')
if target.exists():raise SystemExit('Refusing to overwrite evidence')
target.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(snapshot=sys.argv[1],tables={k:len(v) for k,v in tables.items()},files=len(files))))
if sys.argv[1]=='after':
    before=json.loads((OUT/'before.json').read_text(encoding='utf8'))
    check={k:before[k]==result[k] for k in ['tables','files','planning']}
    (OUT/'integrity.json').write_text(json.dumps(check,indent=2),encoding='utf8');print(check);assert all(check.values())
db.close()
