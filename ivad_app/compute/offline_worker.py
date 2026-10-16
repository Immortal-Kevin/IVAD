"""JSON-lines inference worker. Input images only; never reads human annotations."""
import sys,json,time,contextlib,hashlib
from pathlib import Path

def main(request):
    import os
    os.environ['YOLO_OFFLINE']='true'
    req=json.loads(Path(request).read_text(encoding='utf8'))
    with contextlib.redirect_stdout(sys.stderr):
        import torch
        from PIL import Image
        from ultralytics import YOLO
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; CPU fallback forbidden')
        if hashlib.sha256(Path(req['weights']).read_bytes()).hexdigest()!=req['weights_sha256']:raise RuntimeError('Weight hash changed')
        torch.cuda.set_device(0);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        model=YOLO(req['weights']);model.model.cuda().float().eval()
        if model.task!='detect' or [model.names[k] for k in sorted(model.names)]!=req['class_names']:raise RuntimeError('Model class map/task mismatch')
        calls=[0]
        def guard(module,args):
            if any(not p.is_cuda for p in module.parameters(recurse=False)):raise RuntimeError('CPU model parameter forbidden')
            if any(isinstance(x,torch.Tensor) and not x.is_cuda for x in args):raise RuntimeError('CPU neural forward forbidden')
            calls[0]+=1
        handle=torch.nn.modules.module.register_module_forward_pre_hook(guard)
    print(json.dumps({'ready':True,'gpu':torch.cuda.get_device_name(0)}),flush=True)
    try:
        for line in sys.stdin:
            value=json.loads(line)
            if value.get('close'):break
            image=Image.open(value['image']).convert('RGB');torch.cuda.synchronize();start=time.perf_counter();before=calls[0]
            with contextlib.redirect_stdout(sys.stderr),torch.inference_mode():
                result=model.predict(image,device=0,imgsz=640,conf=req['confidence'],iou=req['iou'],verbose=False,half=False,max_det=300)[0]
            torch.cuda.synchronize();seconds=time.perf_counter()-start
            if calls[0]<=before or not result.boxes.data.is_cuda:raise RuntimeError('No proven CUDA inference')
            print(json.dumps({'index':value['index'],'boxes':result.boxes.data.cpu().tolist(),'inference_seconds':seconds,'gpu_peak_bytes':torch.cuda.max_memory_allocated(),'cuda_forward_calls':calls[0]-before,'cpu_fallback':False}),flush=True)
    finally:handle.remove()
if __name__=='__main__':
    import msvcrt
    # Same per-GPU OS lock as training, including across two GUI instances.
    req=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'));folder=Path(__file__).resolve().parents[2]/'runtime/gpu-locks';folder.mkdir(parents=True,exist_ok=True)
    with (folder/(req['device_uuid']+'.lock')).open('a+b') as lock:
        lock.seek(0,2)
        if lock.tell()==0:lock.write(b'0');lock.flush()
        while True:
            try:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1);break
            except OSError:time.sleep(.2)
        try:main(sys.argv[1])
        finally:lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_UNLCK,1)
