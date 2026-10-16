"""RF-DETR contracts; no ML/framework imports in the GUI process."""
import hashlib
import json
import math
from ivad_app.core.contracts import AppError

MODEL='rfdetr-nano'
DEFAULTS=dict(epochs=1,resolution=384,batch_size=4,lr=0.0001,lr_encoder=0.00015,weight_decay=0.0001,grad_accum_steps=1,seed=20261016,amp_dtype='bf16',use_ema=True)
PROTOCOL=dict(id='ivad-rfdetr-eval-v2',framework='rfdetr==1.11.2',entry='RFDETR.evaluate',split='val',precision='fp32',tf32=False,batch_size=4,resize='RFDETRDataModule torchvision square BILINEAR antialias=True',normalization='ImageNet RGB',max_dets=500,backend='faster_coco_eval',precision_recall='official F1 sweep',iou='COCO .50:.95',cpu_ai_fallback=False,versions={'torch':'2.9.1+cu128','torchvision':'0.24.1+cu128','pytorch-lightning':'2.6.6','faster-coco-eval':'1.8.0','pillow':'12.3.0'})

def signature(value):return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def parameters(values):
    if set(values)-set(DEFAULTS):raise AppError('RF_PARAMETER','RF-DETR存在不支持参数，不会套用YOLO参数。')
    p=dict(DEFAULTS,**values)
    for k,lo,hi in [('epochs',1,10000),('resolution',128,1024),('batch_size',1,32),('grad_accum_steps',1,32),('seed',0,2147483647)]:
        if type(p[k]) is not int or not lo<=p[k]<=hi:raise AppError('RF_PARAMETER',k+'超出允许范围。')
    if p['resolution']%32:raise AppError('RF_PARAMETER','Nano分辨率须为32倍数。')
    for k in ['lr','lr_encoder','weight_decay']:
        if type(p[k]) not in [float,int] or not math.isfinite(p[k]) or not (0<=p[k]<=1) or (k!='weight_decay' and p[k]==0):raise AppError('RF_PARAMETER',k+'无效。')
    if p['amp_dtype'] not in ['fp32','bf16','fp16'] or type(p['use_ema']) is not bool:raise AppError('RF_PARAMETER','精度或EMA参数无效。')
    return p
