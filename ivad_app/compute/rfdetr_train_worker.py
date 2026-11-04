"""CUDA-only RF-DETR worker. Never imports legacy workers or GUI/database code."""
import hashlib
import importlib.abc
import importlib.util
from importlib.metadata import version
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.compute.gpu_lock import gpu_lease,ComputationCancelled
from ivad_app.compute.rfdetr_contract import parameters,PROTOCOL
from ivad_app.compute.rfdetr_evaluation import evaluate
from ivad_app.compute.rfdetr_weights import require_native_weights
from ivad_app.compute.offline_policy import enforce_offline_worker

class DenyLegacy(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname.split('.')[0] in {'ultralytics','ultralytics_thop','ultralytics_platform','thop','rfdetr_plus'}:raise ImportError('Forbidden RF dependency: '+fullname)

def write(path,data):
    path=Path(path);tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf8');tmp.replace(path)
def digest(path):
    with Path(path).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main(path):
    enforce_offline_worker()
    req=json.loads(Path(path).read_text(encoding='utf8'));work=Path(req['work']);start=time.monotonic();result={};cancel=lambda:(work/'cancel.request').exists()
    os.environ.update(HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',MPLCONFIGDIR=str(work/'mpl'),HF_HOME=str(work/'hf'))
    try:
        if any(importlib.util.find_spec(n) is not None for n in ['ultralytics','rfdetr_plus']):raise RuntimeError('RF environment contains forbidden packages')
        sys.meta_path.insert(0,DenyLegacy())
        with gpu_lease(ROOT,req['device_uuid'],cancel):
            import torch
            import pytorch_lightning as pl
            import rfdetr
            from rfdetr import RFDETRNano,RFDETR
            if version('rfdetr')!='1.11.2':raise RuntimeError('Unvalidated RF-DETR version')
            if any(version(k)!=v for k,v in PROTOCOL['versions'].items()):raise RuntimeError('Evaluation environment differs from pinned protocol')
            if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; no CPU fallback')
            if str(torch.cuda.get_device_properties(0).uuid).lower()!=req['device_uuid'].removeprefix('GPU-').lower():raise RuntimeError('CUDA UUID does not match acquired physical GPU lease')
            if digest(req['weights'])!=req['weights_sha256']:raise RuntimeError('Initial weight SHA256 changed')
            checkpoint=torch.load(req['weights'],map_location='cpu',weights_only=False)
            require_native_weights(checkpoint);del checkpoint
            p=parameters(req['parameters']);pl.seed_everything(p['seed'],workers=True);torch.cuda.reset_peak_memory_stats()
            if p['amp_dtype']=='bf16' and not torch.cuda.is_bf16_supported():raise RuntimeError('BF16 unsupported; choose FP32 explicitly')
            evidence=dict(cuda_forward=False,cuda_gradients=False,weight_changed=False,optimizer_steps=0)
            import rfdetr.training as training
            class Cancellation(pl.Callback):
                def on_validation_start(self,trainer,module):
                    if any(not v.is_cuda for v in module.model.parameters()):raise RuntimeError('Evaluation model is not on CUDA')
                    def proof(model,args):
                        if any(not v.is_cuda for v in model.parameters()):raise RuntimeError('CPU evaluation forbidden')
                        evidence['cuda_forward']=True
                    self.handle=module.model.register_forward_pre_hook(proof)
                def on_validation_end(self,*a,**kw):
                    if hasattr(self,'handle'):self.handle.remove()
                def on_validation_batch_end(self,*a,**kw):
                    if cancel():raise ComputationCancelled('验证batch边界取消')
            factory=training.build_trainer
            def cancellable(*a,**kw):
                trainer=factory(*a,**kw);trainer.callbacks.append(Cancellation());return trainer
            training.build_trainer=cancellable
            if req['operation']=='train':
                import rfdetr.training as training
                class Guard(pl.Callback):
                    def on_train_start(self,trainer,module):
                        self.p=next(v for v in module.parameters() if v.requires_grad);self.before=self.p.detach().clone()
                        def check(model,args):
                            if any(not v.is_cuda for v in model.parameters()):raise RuntimeError('CPU neural computation forbidden')
                            evidence['cuda_forward']=True
                        self.hook=module.model.register_forward_pre_hook(check)
                    def on_after_backward(self,trainer,module):
                        grads=[v.grad for v in module.parameters() if v.grad is not None]
                        if not grads or any(not g.is_cuda or not torch.isfinite(g).all() for g in grads):raise RuntimeError('Invalid CUDA gradients')
                        evidence['cuda_gradients']=True
                    def on_train_batch_end(self,trainer,module,outputs,batch,batch_idx):
                        evidence['optimizer_steps']=trainer.global_step;evidence['weight_changed']=not torch.equal(self.before,self.p.detach())
                        if cancel():trainer.save_checkpoint(work/'run/cancelled.ckpt');raise ComputationCancelled('训练batch边界取消')
                    def on_train_epoch_end(self,trainer,module):
                        write(work/'progress.json',dict(epoch=trainer.current_epoch+1,steps=trainer.global_step,phase='training'))
                    def on_validation_batch_end(self,*args,**kw):
                        if cancel():raise ComputationCancelled('验证取消')
                original=training.build_trainer
                def instrument(*a,**kw):
                    trainer=original(*a,**kw);trainer.callbacks.append(Guard());return trainer
                training.build_trainer=instrument
                model=RFDETRNano(pretrain_weights=req['weights'],device='cuda',resolution=p['resolution'])
                model.train(dataset_dir=req['data'],output_dir=str(work/'run'),device='cuda',epochs=p['epochs'],batch_size=p['batch_size'],grad_accum_steps=p['grad_accum_steps'],lr=p['lr'],lr_encoder=p['lr_encoder'],weight_decay=p['weight_decay'],num_workers=0,seed=p['seed'],amp_dtype=None if p['amp_dtype']=='fp32' else p['amp_dtype'],use_ema=p['use_ema'],multi_scale=False,scale_jitter=False,tensorboard=False,progress_bar=None,checkpoint_interval=1,eval_backend='faster_coco_eval',run_test=False,resume=req.get('resume_checkpoint'))
                if not all(evidence.values()):raise RuntimeError('No verified CUDA update')
                weights=work/'run/checkpoint_best_total.pth'
            else:weights=Path(req['weights'])
            if cancel():raise ComputationCancelled('评估前取消')
            model=RFDETR.from_checkpoint(weights,device='cuda');model.model.model.cuda().eval()
            if model.class_names!=req['class_names']:raise RuntimeError('Checkpoint class map does not match dataset')
            write(work/'progress.json',dict(epoch=p['epochs'] if req['operation']=='train' else 0,phase='unified_evaluation'))
            first=evaluate(model,req['data'],work/'eval-in-memory',p['resolution'])
            if cancel():raise ComputationCancelled('重载前取消')
            reloaded=RFDETR.from_checkpoint(weights,device='cuda');reloaded.model.model.cuda().eval()
            second=evaluate(reloaded,req['data'],work/'eval-reload',p['resolution'])
            delta={k:abs(first['metrics'][k]-second['metrics'][k]) for k in first['metrics']}
            if any(v>1e-4 for v in delta.values()):raise RuntimeError('Evaluation parity BLOCKED: '+str(delta))
            if first['prediction_trace_sha256']!=second['prediction_trace_sha256']:raise RuntimeError('Per-frame logits/boxes/scores/labels differ under the same protocol')
            if cancel():raise ComputationCancelled('保存结果前取消')
            if not evidence['cuda_forward']:raise RuntimeError('No observed CUDA evaluation forward')
            forbidden=[n for n in sys.modules if n.startswith(('ultralytics','rfdetr_plus'))]
            if forbidden:raise RuntimeError('Forbidden imports')
            result=dict(status='PASS',**second,evidence=dict(evidence,checkpoint_reloaded_cuda=True,cpu_fallback=False),parity=dict(status='PASS',first=first,second=second,delta=delta,tolerance=1e-4),weights=str(weights),weights_sha256=digest(weights),artifact_format='rf-detr-weights-pth',peak_allocated_bytes=torch.cuda.max_memory_allocated(),torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),forbidden_imports=forbidden,loaded_modules=sorted(sys.modules))
    except Exception as exc:
        from ivad_app.services.local_security import redact
        result=dict(status='CANCELLED' if isinstance(exc,ComputationCancelled) else 'BLOCKED',error=redact(repr(exc)),oom='out of memory' in str(exc).lower(),traceback=redact(traceback.format_exc()));traceback.print_exc()
    result['seconds']=time.monotonic()-start;write(work/'result.json',result)
    return 0 if result['status']=='PASS' else 3 if result['status']=='CANCELLED' else 1

if __name__=='__main__':sys.exit(main(sys.argv[1]))
