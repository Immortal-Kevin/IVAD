"""Isolated NVIDIA acceptance; write only to a fresh evidence directory."""
import os,sys,json,hashlib,time,shutil,traceback
from pathlib import Path

def digest(p):
    with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main(request):
    req=json.loads(Path(request).read_text(encoding='utf8'));out=Path(req['output']);out.mkdir(exist_ok=False,parents=True)
    result={'status':'FAIL'}
    try:
        import torch,numpy as np,onnx,onnxruntime as ort
        from PIL import Image
        import os
        os.environ['YOLO_OFFLINE']='true'
        from ultralytics import YOLO
        from ultralytics.utils.nms import non_max_suppression
        from ultralytics.data.augment import LetterBox
        from ultralytics.utils.ops import scale_boxes
        if not torch.cuda.is_available():raise RuntimeError('CUDA unavailable; CPU fallback forbidden')
        torch.cuda.set_device(0);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
        original=Path(req['weights']);before=digest(original)
        if before!=req['sha256']:raise RuntimeError('Weight SHA mismatch')
        weights=out/'validated-copy.pt';shutil.copyfile(original,weights)
        model=YOLO(str(weights));model.model.cuda().float().eval()
        expected=[c['name'] for c in req['classes']]
        if model.task!='detect' or [model.names[i] for i in sorted(model.names)]!=expected:raise RuntimeError('Detection class map mismatch')
        if 'yolo11' not in str(model.model.yaml.get('yaml_file','')).lower():raise RuntimeError('Not YOLO11')
        image=np.array(Image.open(req['image']).convert('RGB'));h,w=image.shape[:2];size=640
        letter=LetterBox((size,size),auto=False)(image=image);x=torch.from_numpy(np.ascontiguousarray(letter.transpose(2,0,1))).unsqueeze(0).cuda().float()/255
        forwards=[0]
        def guard(m,args):
            if any(not p.is_cuda for p in m.parameters(recurse=False)):raise RuntimeError('CPU parameter')
            if any(isinstance(v,torch.Tensor) and not v.is_cuda for v in args):raise RuntimeError('CPU forward')
            forwards[0]+=1
        handle=torch.nn.modules.module.register_module_forward_pre_hook(guard)
        with torch.inference_mode():
            for _ in range(3):model.model(x)
            torch.cuda.synchronize();start=time.perf_counter()
            for _ in range(20):pt=model.model(x)[0]
            torch.cuda.synchronize();seconds=(time.perf_counter()-start)/20
        exported=model.export(format='onnx',device=0,imgsz=size,batch=1,half=False,simplify=False,opset=17,dynamic=False,nms=False)
        # Export changes the module's export mode; reload a clean PT for comparison.
        model=YOLO(str(weights));model.model.cuda().float().eval()
        with torch.inference_mode():pt=model.model(x)[0].float().contiguous()
        handle.remove();onnx.checker.check_model(exported);ort.preload_dlls()
        so=ort.SessionOptions();so.enable_profiling=True;so.profile_file_prefix=str(out/'ort-profile');so.add_session_config_entry('session.disable_cpu_ep_fallback','1')
        session=ort.InferenceSession(exported,sess_options=so,providers=[('CUDAExecutionProvider',{'use_tf32':'0','cudnn_conv_algo_search':'HEURISTIC'})]);session.disable_fallback()
        binding=session.io_binding();binding.bind_input(session.get_inputs()[0].name,'cuda',0,np.float32,tuple(x.shape),x.data_ptr())
        for o in session.get_outputs():binding.bind_output(o.name,'cuda')
        session.run_with_iobinding(binding);raw=binding.copy_outputs_to_cpu()[0];expected_raw=pt.cpu().numpy()
        if raw.shape!=expected_raw.shape or not np.allclose(raw,expected_raw,rtol=.005,atol=.05):raise RuntimeError('PT/ONNX raw mismatch')
        nc=len(expected)
        if raw.shape[1]!=4+nc:raise RuntimeError('Unexpected raw output')
        threshold=req.get('confidence',.25)
        a=non_max_suppression(pt.clone(),conf_thres=threshold,iou_thres=.45,nc=nc)[0]
        b=non_max_suppression(torch.from_numpy(raw).cuda(),conf_thres=threshold,iou_thres=.45,nc=nc)[0]
        if a.shape!=b.shape or not torch.allclose(a,b,rtol=.005,atol=.1):raise RuntimeError('NMS mismatch')
        profile=Path(session.end_profiling());events=json.loads(profile.read_text());nodes=[e for e in events if e.get('args',{}).get('provider')]
        providers={e['args']['provider'] for e in nodes}
        if not nodes or providers!={'CUDAExecutionProvider'}:raise RuntimeError('ORT CPU node or no CUDA node evidence')
        boxes=a.cpu().tolist()
        for x1,y1,x2,y2,confidence,cls in boxes:
            if not (0<=x1<=x2<=size and 0<=y1<=y2<=size and 0<=confidence<=1 and int(cls)==cls and 0<=cls<nc):raise RuntimeError('Invalid output')
        if digest(original)!=before:raise RuntimeError('Original weights modified')
        mapped=a.clone();mapped[:,:4]=scale_boxes((size,size),mapped[:,:4],(h,w));mapped=mapped.cpu().tolist()
        result=dict(status='PASS',weights_sha256=before,original_unchanged=True,model_id=req['model_id'],version_id=req['version_id'],classes=expected,image=req['image'],input_shape=list(x.shape),raw_shape=list(raw.shape),raw_max_abs_error=float(np.max(np.abs(raw-expected_raw))),rtol=.005,atol=.05,nms_atol=.1,confidence=threshold,boxes_640=boxes,boxes_original=mapped,original_size=[w,h],pt_inference_ms=seconds*1000,pt_tensor_fps=1/seconds,gpu=torch.cuda.get_device_name(0),torch=torch.__version__,cuda=torch.version.cuda,peak_allocated_bytes=torch.cuda.max_memory_allocated(),cuda_forward_calls=forwards[0],onnx=exported,onnx_sha256=digest(exported),ort_node_providers=sorted(providers),ort_cuda_nodes=len(nodes),cpu_fallback=False,industrial_accuracy='NOT TESTED; training-source sample')
    except Exception as e:result.update(error=str(e),traceback=traceback.format_exc());traceback.print_exc()
    (out/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(result,ensure_ascii=False));return 0 if result['status']=='PASS' else 1
if __name__=='__main__':raise SystemExit(main(sys.argv[1]))
