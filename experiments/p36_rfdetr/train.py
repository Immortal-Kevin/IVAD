"""CUDA-only experiment runner; official RF-DETR train API with evidence callback."""
import json
import os
import sys
import time
import traceback
from pathlib import Path

os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')
os.environ.setdefault('DO_NOT_TRACK','1')
_cache=Path(__file__).resolve().parents[2]/'artifacts/p36-rfdetr-20261016/process-cache'
os.environ['MPLCONFIGDIR']=str(_cache/'matplotlib')
os.environ['HF_HOME']=str(_cache/'huggingface')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from adapter import assert_isolated


def main(request):
    assert_isolated()
    req=json.loads(Path(request).read_text(encoding='utf8'))
    output=Path(req['output']);output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    result=dict(status='BLOCKED',cpu_ai_fallback=False,parameters=req)
    try:
        cancel=Path(request).with_suffix('.cancel.request')
        if cancel.exists():raise InterruptedError('Cancelled before model loading')
        import torch
        import pytorch_lightning as pl
        from rfdetr import RFDETRNano
        import rfdetr.training as training
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable')
        torch.cuda.reset_peak_memory_stats()
        evidence=dict(cuda_forward_calls=0,cuda_gradients=False,weight_changed=False,optimizer_steps=0)
        class Evidence(pl.Callback):
            def on_train_start(self,trainer,module):
                if module.device.type!='cuda':raise RuntimeError('CPU AI training forbidden')
                self.parameter=next(p for p in module.parameters() if p.requires_grad)
                self.before=self.parameter.detach().clone()
                def guard(_module,args):
                    if next(_module.parameters()).device.type!='cuda':raise RuntimeError('CPU model forward')
                    evidence['cuda_forward_calls']+=1
                self.hook=module.model.register_forward_pre_hook(guard)
            def on_after_backward(self,trainer,module):
                grads=[p.grad for p in module.parameters() if p.grad is not None]
                if not grads or any(not g.is_cuda or not torch.isfinite(g).all() for g in grads):raise RuntimeError('Invalid/CPU gradients')
                evidence['cuda_gradients']=True
            def on_train_batch_end(self,trainer,module,outputs,batch,batch_idx):
                evidence['optimizer_steps']=trainer.global_step
                evidence['weight_changed']=not torch.equal(self.before,self.parameter.detach())
                if cancel.exists() or (output/'cancel.request').exists():
                    trainer.save_checkpoint(output/'cancelled.ckpt')
                    raise InterruptedError('Explicit cancellation; partial checkpoint retained')
            def on_train_end(self,trainer,module):self.hook.remove()
        original=training.build_trainer
        def instrumented(*a,**kw):
            trainer=original(*a,**kw);trainer.callbacks.append(Evidence());return trainer
        training.build_trainer=instrumented
        # Seed before construction/class-head alignment, not only dataloader setup.
        pl.seed_everything(req['train']['seed'],workers=True)
        model=RFDETRNano(pretrain_weights=req['weights'],device='cuda')
        model.train(**req['train'],dataset_dir=req['dataset'],output_dir=str(output),device='cuda',notes='IVAD P36 isolated engineering experiment / LIMITED')
        if not all((evidence['cuda_gradients'],evidence['weight_changed'],evidence['optimizer_steps']>0,evidence['cuda_forward_calls']>0)):raise RuntimeError('Insufficient actual CUDA update evidence')
        result.update(status='PASS',evidence=evidence,peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name())
    except Exception as exc:
        result.update(status='CANCELLED' if isinstance(exc,InterruptedError) else 'BLOCKED',error=repr(exc),traceback=traceback.format_exc())
        traceback.print_exc()
    result['seconds']=time.perf_counter()-start
    (output/'experiment-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False))
    return 0 if result['status']=='PASS' else 1


if __name__=='__main__':sys.exit(main(sys.argv[1]))
