"""Pinned NVIDIA training worker. Invoked by isolated GPU Python, never GUI Python."""
import os,sys,json,time,traceback,hashlib,shutil
from pathlib import Path

def write(path,data):
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,allow_nan=False,indent=2),encoding='utf8');tmp.replace(path)

class Cancelled(Exception):pass

def main(request_path):
    req=json.loads(Path(request_path).read_text(encoding='utf8'));work=Path(req['work']);start=time.perf_counter();result={}
    lock=None;handle=None
    try:
        # One physical GPU across separate GUI processes. Persistent lock file, OS releases byte lock on crash.
        import msvcrt
        lockdir=Path(__file__).resolve().parents[2]/'runtime/gpu-locks';lockdir.mkdir(parents=True,exist_ok=True)
        lock=(lockdir/(req['device_uuid']+'.lock')).open('a+b');lock.seek(0);lock.write(b'0');lock.flush()
        while True:
            if (work/'cancel.request').exists():raise Cancelled()
            try:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:time.sleep(.2)
        import torch,numpy as np
        from ultralytics import YOLO,settings
        from ultralytics.models.yolo.detect import DetectionTrainer
        from ultralytics.utils.nms import non_max_suppression
        settings.update({'sync':False,'datasets_dir':str(work/'dataset'),'weights_dir':str(work/'weights'),'runs_dir':str(work/'runs')})
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; CPU fallback forbidden')
        torch.cuda.set_device(0);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        forwards=[0]
        def guard(module,args):
            forwards[0]+=1
            for p in module.parameters(recurse=False):
                if not p.is_cuda:raise RuntimeError('CPU neural network parameter forbidden')
            def check(v):
                if isinstance(v,torch.Tensor) and not v.is_cuda:raise RuntimeError('CPU neural network forward forbidden')
                if isinstance(v,(tuple,list)):
                    for x in v:check(x)
                if isinstance(v,dict):
                    for x in v.values():check(x)
            check(args)
        handle=torch.nn.modules.module.register_module_forward_pre_hook(guard)
        if hashlib.sha256(Path(req['weights']).read_bytes()).hexdigest()!=req['weights_sha256']:raise RuntimeError('Initial weight hash changed')
        if req.get('operation')=='validate':
            model=YOLO(req['weights']);model.model.cuda().eval()
            if len(model.names)!=req['class_count'] or [model.names[k] for k in sorted(model.names)]!=req['class_names']:raise RuntimeError('Model class mapping differs from frozen dataset; validation refused')
            def cancelled(_):
                if (work/'cancel.request').exists():raise Cancelled()
            model.add_callback('on_val_batch_end',cancelled)
            m=model.val(data=req['data'],device=0,workers=0,batch=req['parameters']['batch'],imgsz=req['parameters']['imgsz'],half=False,plots=True,project=str(work),name='validation',verbose=False)
            metrics={k:float(m.results_dict[key]) for k,key in [('precision','metrics/precision(B)'),('recall','metrics/recall(B)'),('map50','metrics/mAP50(B)'),('map50_95','metrics/mAP50-95(B)')]}
            if not forwards[0]:raise RuntimeError('No verified GPU neural forward')
            write(work/'result.json',{'status':'PASS','metrics':metrics,'evidence':{'cuda_forward':True,'forward_calls':forwards[0],'cpu_fallback':False},'environment':{'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'uuid':req['device_uuid']},'seconds':time.perf_counter()-start,'industrial_accuracy':'NOT TESTED'});return 0
        evidence={'cuda_parameters':False,'cuda_gradients':False,'weight_changed':False,'optimizer_steps':0,'cpu_fallback':False};before={}
        class Trainer(DetectionTrainer):
            def check_resume(self,overrides):
                super().check_resume(overrides)
                if req.get('resume'):
                    # Resume must never write back into the original experiment directory.
                    self.args.save_dir=str(work/'run');self.args.project=str(work);self.args.name='run'
            def get_model(self,cfg=None,weights=None,verbose=True):
                with torch.device('cuda:0'):return super().get_model(cfg,weights,verbose)
            def optimizer_step(self):
                if not all(p.grad is None or p.grad.is_cuda for p in self.model.parameters()):raise RuntimeError('CPU gradient forbidden')
                evidence['cuda_gradients']=any(p.grad is not None for p in self.model.parameters())
                super().optimizer_step();evidence['optimizer_steps']+=1
            def save_model(self):
                saved=super().save_model()
                if saved and self.last.exists():shutil.copyfile(self.last,self.last.with_name('resume.pt'))
                return saved
        def begin(t):
            evidence['resumed_start_epoch']=t.start_epoch;evidence['actual_epochs']=t.epochs
            evidence['cuda_parameters']=all(p.is_cuda for p in t.model.parameters())
            if not evidence['cuda_parameters']:raise RuntimeError('Training model not CUDA')
            for k,p in t.model.named_parameters():
                if p.requires_grad:before[k]=p.detach().clone();break
        def batch(t):
            if (work/'cancel.request').exists():raise Cancelled()
        def epoch(t):
            evidence['weight_changed']=any(not torch.equal(before[k],p) for k,p in t.model.named_parameters() if k in before)
        def progress(t):
            metrics={str(k):float(v) for k,v in dict(t.metrics or {},**t.label_loss_items(t.tloss,prefix='train')).items()}
            write(work/'progress.json',{'epoch':t.epoch+1,'epochs':t.epochs,'metrics':metrics,'gpu_allocated_bytes':torch.cuda.memory_allocated(),'gpu_peak_bytes':torch.cuda.max_memory_allocated(),'elapsed_seconds':time.perf_counter()-start})
        model=YOLO(req['weights']);model.add_callback('on_train_start',begin);model.add_callback('on_train_batch_end',batch);model.add_callback('on_train_epoch_end',epoch);model.add_callback('on_fit_epoch_end',progress)
        architecture=str(model.model.yaml.get('yaml_file','')).lower()
        if req['model'].removesuffix('n') not in architecture or model.model.yaml.get('scale','n')!='n':raise RuntimeError('Weight architecture does not match selected model adapter')
        if req['parameters']['amp']:
            # Avoid framework AMP smoke test that downloads another model; verify CUDA AMP locally.
            probe=torch.nn.Linear(16,4).cuda();sample=torch.randn(8,16,device='cuda')
            with torch.autocast('cuda',dtype=torch.float16):amp_out=probe(sample)
            if not amp_out.is_cuda or not torch.isfinite(amp_out).all():raise RuntimeError('CUDA AMP probe failed')
            import ultralytics.engine.trainer as trainer_module
            trainer_module.check_amp=lambda _: True
        p=dict(req['parameters']);augmentation=p.pop('augment')
        args=dict(p,data=req['data'],device=0,workers=0,nbs=p['batch'],warmup_epochs=0,project=str(work),name='run',exist_ok=False,save=True,save_period=1,val=True,plots=True,pretrained=True,verbose=False)
        if not augmentation:args.update(hsv_h=0.,hsv_s=0.,hsv_v=0.,degrees=0.,translate=0.,scale=0.,shear=0.,perspective=0.,flipud=0.,fliplr=0.,mosaic=0.,mixup=0.,copy_paste=0.)
        if req.get('resume'):args['resume']=req['weights']
        train_result=model.train(trainer=Trainer,**args)
        if (work/'cancel.request').exists():raise Cancelled()
        if not evidence['cuda_gradients'] or not evidence['weight_changed'] or not evidence['optimizer_steps']:raise RuntimeError('No proven CUDA backpropagation / weight update')
        best=work/'run/weights/best.pt';reload=YOLO(str(best));reload.model.cuda().eval();x=torch.rand(1,3,p['imgsz'],p['imgsz'],device='cuda')
        with torch.inference_mode():reload.model(x)
        metrics={k:float(train_result.results_dict[key]) for k,key in [('precision','metrics/precision(B)'),('recall','metrics/recall(B)'),('map50','metrics/mAP50(B)'),('map50_95','metrics/mAP50-95(B)')]}
        result={'status':'PASS','metrics':metrics,'evidence':dict(evidence,checkpoint_reloaded_cuda=True),'environment':{'torch':torch.__version__,'cuda':torch.version.cuda,'gpu':torch.cuda.get_device_name(0),'uuid':req['device_uuid']},'seconds':time.perf_counter()-start,'industrial_accuracy':'NOT TESTED','model':req['model']}
        # ONNX is a model artifact, not software packaging. Validate raw tensors and NMS separately.
        reload.model.model[-1].end2end=False
        onnx_path=reload.export(format='onnx',device=0,imgsz=p['imgsz'],batch=1,half=False,simplify=False,opset=17,dynamic=False,end2end=False,nms=False)
        import onnxruntime as ort
        ort.preload_dlls();so=ort.SessionOptions();so.enable_profiling=True;so.profile_file_prefix=str(work/'ort-profile');so.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        session=ort.InferenceSession(onnx_path,sess_options=so,providers=[('CUDAExecutionProvider',{'use_tf32':'0','cudnn_conv_algo_search':'HEURISTIC'})]);session.disable_fallback()
        with torch.inference_mode():pt=reload.model(x)[0].float().contiguous()
        binding=session.io_binding();binding.bind_input(session.get_inputs()[0].name,'cuda',0,np.float32,tuple(x.shape),x.data_ptr())
        for o in session.get_outputs():binding.bind_output(o.name,'cuda')
        session.run_with_iobinding(binding);raw=binding.copy_outputs_to_cpu()[0];expected=pt.cpu().numpy()
        if raw.shape!=expected.shape or not np.allclose(raw,expected,rtol=.005,atol=.05):raise RuntimeError('ONNX raw output differs from PyTorch')
        nc=len(reload.names)
        # Explicitly raw YOLO26 non-end2end + NMS, and YOLO11 raw + NMS. Do not mix end2end output.
        if raw.ndim!=3 or raw.shape[1]!=4+nc:raise RuntimeError('Unsupported raw output structure')
        a=non_max_suppression(pt.clone(),conf_thres=.25,iou_thres=.45,nc=nc)[0].cpu().numpy();b=non_max_suppression(torch.from_numpy(raw).cuda(),conf_thres=.25,iou_thres=.45,nc=nc)[0].cpu().numpy()
        if a.shape!=b.shape or not np.allclose(a,b,rtol=.005,atol=.1):raise RuntimeError('ONNX final detections differ')
        profile=Path(session.end_profiling());providers={e.get('args',{}).get('provider') for e in json.loads(profile.read_text()) if e.get('args',{}).get('provider')}
        if providers!={'CUDAExecutionProvider'}:raise RuntimeError('ORT CPU node/fallback detected')
        result['onnx']={'path':str(onnx_path),'sha256':hashlib.sha256(Path(onnx_path).read_bytes()).hexdigest(),'providers':sorted(providers),'raw_shape':list(raw.shape),'raw_max_abs_error':float(np.max(np.abs(raw-expected))),'nms_count':len(a),'nms_comparison':'PASS','class_names':reload.names,'format':req['model']+' raw non-end2end + NMS','industrial_accuracy':'NOT TESTED'}
        write(work/'result.json',result);return 0
    except Cancelled:
        write(work/'result.json',{'status':'CANCELLED','error':'用户取消；保留已完成epoch检查点，不登记假成功模型。'});return 3
    except Exception as exc:
        traceback.print_exc();write(work/'result.json',{'status':'FAIL','error':str(exc),'traceback':traceback.format_exc(),'oom':type(exc).__name__=='OutOfMemoryError'});return 1
    finally:
        if handle:handle.remove()
        if lock:
            try:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
            except OSError:pass
            lock.close()

if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
