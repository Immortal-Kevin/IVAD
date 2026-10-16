"""PTH artifact export is not an application distribution build."""
import json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.core.application import ApplicationServices
from ivad_app.storage.project_store import file_hash
OUT=ROOT/'artifacts/p37a-20261016';s=ApplicationServices(ROOT,OUT/'export-read-runtime')
try:
    mid='fd9f9bf2-3b69-45b9-b713-242c06783711';root=str(OUT/'project-copy')
    path,data=s.models.verify(mid,root)
    export=Path(s.models.export(mid,OUT,root));assert (export/'model.pth').is_file() and not (export/'model.onnx').exists()
    assert file_hash(export/'model.pth')==data['sha256']
    result=dict(status='PASS',model_id=mid,sha256=data['sha256'],export_path=str(export),format='PTH, no fake extension or generated ONNX')
    (OUT/'registry-export-check.json').write_text(json.dumps(result,indent=2),encoding='utf8');print(json.dumps(result))
finally:s.close()
