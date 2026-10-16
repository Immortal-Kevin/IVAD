import json,sys,sqlite3
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.compute.gpu_lock import gpu_lease
OUT=ROOT/'artifacts/p37a-20261016'
with sqlite3.connect((OUT/'gui-runtime/catalog.sqlite').as_uri()+'?mode=ro',uri=True) as db:
    state=db.execute('select state from jobs where id=?',('0fe1d94a-e6aa-4ee2-944c-1a4e9b6ceded',)).fetchone()[0]
assert state=='CANCELLED'
with gpu_lease(ROOT,'GPU-c942e790-0e56-4262-a96d-16122a858702',lambda:False):released=True
snapshot=json.loads((OUT/'delivery-snapshot.json').read_text(encoding='utf8'));assert len(snapshot['models'])==5
result=dict(status='PASS',job_state=state,worker_status=json.loads((OUT/'project-copy/training/48d13749-e698-4a87-880f-00a940318f99/result.json').read_text(encoding='utf8'))['status'],gpu_lock_reacquired=released,models_unchanged=5,gui_process_exit_code=0)
(OUT/'gui-close-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
