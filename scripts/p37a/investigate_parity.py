import json,sys,time,os,hashlib
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'artifacts/p37a-20261016/parity';out.mkdir(exist_ok=False)
os.environ['MPLCONFIGDIR']=str(out/'mpl');os.environ['HF_HOME']=str(out/'hf')
sys.path.insert(0,str(root/'experiments/p36_rfdetr'))
from adapter import NanoAdapter
import torch
weights=root/'artifacts/p36-rfdetr-20261016/engineering-seeded-run/checkpoint_best_total.pth'
model=NanoAdapter.restore(weights).model
results={}
for precision in [None,'bf16']:
 name='fp32' if precision is None else precision
 begin=time.time()
 result=model.evaluate(dataset_dir=str(root/'artifacts/p36-rfdetr-20261016/coco'),split='val',device='cuda',batch_size=4,num_workers=0,amp_dtype=precision,use_ema=False,multi_scale=False,scale_jitter=False,tensorboard=False,progress_bar=None,eval_backend='faster_coco_eval',eval_max_dets=500,output_dir=str(out/name),class_names=['压滤版破裂'])
 results[name]=dict(metrics=result,seconds=time.time()-begin)
 (out/'official-evaluation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf8')
 print(name,result,flush=True)
