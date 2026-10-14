"""Upgrade a backup copy of prior real P2 project; original remains read-only."""
import json,sqlite3,sys
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.storage.database import Database
source=next((ROOT/'artifacts/p2/gui-evidence-native').glob('IVAD-*/project.sqlite'))
destination=ROOT/'artifacts/p2-adjustment'/('migration-check-'+uuid4().hex+'.sqlite')
with sqlite3.connect(source.as_uri()+'?mode=ro',uri=True) as raw:
    tables=[r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name<>'alembic_version'")]
    before={}
    for name in tables:
        quoted='"'+name.replace('"','""')+'"';columns=[r[1] for r in raw.execute('PRAGMA table_info('+quoted+')')]
        before[name]=(columns,raw.execute('SELECT * FROM '+quoted+' ORDER BY rowid').fetchall())
    with sqlite3.connect(destination) as copy:raw.backup(copy)
db=Database(destination);assert db.integrity_check()=='ok';db.close()
with sqlite3.connect(destination) as migrated:
    for name,(columns,rows) in before.items():
        query='SELECT '+','.join('"'+c.replace('"','""')+'"' for c in columns)+' FROM "'+name.replace('"','""')+'" ORDER BY rowid'
        assert migrated.execute(query).fetchall()==rows,name
result={'status':'PASS','source':str(source.relative_to(ROOT)),'destination':str(destination.relative_to(ROOT)),'tables_preserved':len(before),'rows_preserved':{name:len(data[1]) for name,data in before.items()},'backup_created':bool(list(destination.parent.glob(destination.name+'.migration-*.backup'))),'schema':'0004'}
(ROOT/'artifacts/p2-adjustment/migration-check.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8');print('PASS',result['tables_preserved'],'tables preserved')
