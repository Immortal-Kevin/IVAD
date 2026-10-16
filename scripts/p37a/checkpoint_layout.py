import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
import torch
from ivad_app.compute.rfdetr_weights import require_native_weights
paths=['artifacts/p36-rfdetr-20261016/engineering-seeded-run/checkpoint_best_total.pth','artifacts/p36-rfdetr-20261016/weights/rf-detr-nano.pth','artifacts/p37a-20261016/project-copy/training/9c86e892-13b9-4e2d-a3ee-c133acc87ecd/run/cancelled.ckpt']
results=[]
for path in paths:
    try:
        require_native_weights(torch.load(ROOT/path,map_location='cpu',weights_only=False));accepted=True
    except ValueError:accepted=False
    results.append(dict(path=path,accepted=accepted))
assert [r['accepted'] for r in results]==[True,True,False]
(ROOT/'artifacts/p37a-20261016/checkpoint-layout.json').write_text(json.dumps(results,indent=2),encoding='utf8')
print('PASS: real native PTH/hybrid PTH accepted; training-only CKPT rejected independent of extension')
