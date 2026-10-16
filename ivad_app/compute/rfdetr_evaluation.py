"""One pinned validation protocol for end-of-training and independent reload."""
from pathlib import Path
import math
import json,hashlib
from ivad_app.compute.rfdetr_contract import PROTOCOL,signature

def evaluate(model,dataset,output,resolution=384):
    import torch
    import pytorch_lightning as pl
    import rfdetr.training as training
    if not torch.cuda.is_available():raise RuntimeError('CUDA required')
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    traces=[];output=Path(output);output.mkdir(parents=True,exist_ok=True)
    class Capture(pl.Callback):
        def on_validation_start(self,trainer,module):
            # RF build_trainer sets precision('high'); enforce AFTER its factory.
            torch.set_float32_matmul_precision('highest')
            torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
            def raw(network,args,value):
                if any(not p.is_cuda for p in network.parameters()):raise RuntimeError('CPU evaluation forbidden')
                self.raw={k:value[k].detach().float().cpu().tolist() for k in ['pred_logits','pred_boxes']}
            self.hook=module.model.register_forward_hook(raw)
        def on_validation_batch_end(self,trainer,module,outputs,batch,batch_idx,*args):
            for i,(prediction,target) in enumerate(zip(outputs['results'],outputs['targets'])):
                traces.append(dict(image_id=int(target['image_id'].item()),raw={k:v[i] for k,v in self.raw.items()},postprocessed={k:prediction[k].detach().cpu().tolist() for k in ['boxes','scores','labels']}))
        def on_validation_end(self,*args):self.hook.remove()
    factory=training.build_trainer
    def instrument(*a,**kw):
        trainer=factory(*a,**kw);torch.set_float32_matmul_precision('highest');torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False;trainer.callbacks.append(Capture());return trainer
    training.build_trainer=instrument
    try:metrics=model.evaluate(dataset_dir=str(dataset),split='val',device='cuda',batch_size=4,num_workers=0,amp_dtype=None,use_ema=False,multi_scale=False,scale_jitter=False,tensorboard=False,progress_bar=None,eval_backend='faster_coco_eval',eval_max_dets=500,resolution=resolution,output_dir=str(output))
    finally:training.build_trainer=factory
    result={k:float(metrics[v]) for k,v in [('precision','val/precision'),('recall','val/recall'),('map50','val/mAP_50'),('map50_95','val/mAP_50_95')]}
    if any(not math.isfinite(v) or not 0<=v<=1 for v in result.values()):raise RuntimeError('Invalid evaluation metric')
    protocol=dict(PROTOCOL,resolution=resolution)
    payload=json.dumps(traces,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    (output/'predictions.json').write_bytes(payload)
    if not traces or len({t['image_id'] for t in traces})!=len(traces):raise RuntimeError('Missing or duplicate validation predictions')
    return dict(metrics=result,protocol=protocol,protocol_sha256=signature(protocol),prediction_trace_sha256=hashlib.sha256(payload).hexdigest(),prediction_frames=len(traces))
