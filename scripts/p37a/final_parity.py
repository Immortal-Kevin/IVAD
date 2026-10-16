"""Final pinned-weight parity with per-frame raw and decoded prediction evidence."""
import json,sys,subprocess,os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.datasets.rfdetr import export
OUT=ROOT/'artifacts/p37a-20261016'/('final-parity-v2' if len(sys.argv)<2 else sys.argv[1]);OUT.mkdir(exist_ok=False)
manifest=ROOT/'artifacts/p37a-20261016/project-copy/datasets/5ea5cbb0-3e8e-4c45-a0bd-9ec7ae9e9782/v0001/manifest.json'
counts=export(manifest,OUT/'dataset');(OUT/'dataset-summary.json').write_text(json.dumps(counts,ensure_ascii=False,indent=2),encoding='utf8')
req=json.loads((ROOT/'artifacts/p37a-20261016/formal-parity/request.json').read_text(encoding='utf8'));req.update(work=str(OUT),data=str(OUT/'dataset'))
(OUT/'request.json').write_text(json.dumps(req,ensure_ascii=False,indent=2),encoding='utf8')
with (OUT/'console.log').open('w',encoding='utf8') as stream:
    child=subprocess.run([str(ROOT/'.venv-rfdetr/Scripts/python.exe'),'-I','-X','utf8',str(ROOT/'ivad_app/compute/rfdetr_train_worker.py'),str(OUT/'request.json')],stdout=stream,stderr=subprocess.STDOUT,env=dict(os.environ,CUDA_VISIBLE_DEVICES=req['device_uuid']))
result=json.loads((OUT/'result.json').read_text(encoding='utf8'));print(json.dumps({k:result.get(k) for k in ['status','error','metrics','prediction_frames','prediction_trace_sha256','seconds']},ensure_ascii=False));sys.exit(child.returncode)
