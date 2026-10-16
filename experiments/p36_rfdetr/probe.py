"""Independent CUDA update/save/reload and real RF-DETR prediction benchmark."""
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')
sys.path.insert(0,str(Path(__file__).resolve().parent))
from adapter import NanoAdapter, assert_isolated, convert


def run(weights,image,output):
    import torch
    import numpy as np
    import psutil
    from PIL import Image
    assert_isolated()
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    assert torch.cuda.is_available(),'CUDA mandatory'
    torch.manual_seed(20261016)
    net=torch.nn.Linear(16,4,device='cuda')
    before=net.weight.detach().clone();opt=torch.optim.SGD(net.parameters(),lr=.01)
    x=torch.randn(8,16,device='cuda');loss=net(x).square().mean();loss.backward()
    assert net.weight.grad.is_cuda and torch.isfinite(net.weight.grad).all()
    opt.step();assert not torch.equal(before,net.weight)
    torch.save(net.state_dict(),output/'tensor-check.pth')
    other=torch.nn.Linear(16,4,device='cuda');other.load_state_dict(torch.load(output/'tensor-check.pth',weights_only=True,map_location='cuda'))
    assert torch.equal(net(x),other(x))
    del net,other,opt,x
    start=time.perf_counter();adapter=NanoAdapter(weights);torch.cuda.synchronize();load=time.perf_counter()-start
    model=adapter.model.model.model
    assert all(p.is_cuda for p in model.parameters())
    cuda_calls=[0];kernel=[];begin=torch.cuda.Event(enable_timing=True);end=torch.cuda.Event(enable_timing=True)
    def pre(module,args):
        assert next(module.parameters()).is_cuda
        cuda_calls[0]+=1;begin.record()
    def post(module,args,result):
        end.record();end.synchronize();kernel.append(begin.elapsed_time(end))
    h1=model.register_forward_pre_hook(pre);h2=model.register_forward_hook(post)
    rgb=Image.open(image).convert('RGB')
    for _ in range(5):adapter.predict(rgb,threshold=.25)
    kernel.clear();elapsed=[]
    predictions=None
    torch.cuda.reset_peak_memory_stats()
    for _ in range(30):
        start=time.perf_counter();predictions=adapter.predict(rgb,threshold=.25);torch.cuda.synchronize();elapsed.append((time.perf_counter()-start)*1000)
    names=adapter.model.class_names
    # Official COCO checkpoint emits sparse COCO IDs, not positions in 80-name list.
    from rfdetr.assets.coco_classes import COCO_CLASSES
    names=dict(zip(COCO_CLASSES,names))
    context=dict(frame_id='experimental-input',camera_id=None,media_id=None,time_us=0,model_version='nano-official-pretrained')
    converted=convert(predictions,width=rgb.width,height=rgb.height,class_names=names,context=context)
    empty=adapter.predict(rgb,threshold=1.0)
    assert len(empty)==0
    empty_contract=convert(empty,width=rgb.width,height=rgb.height,class_names=names,context=context)
    h1.remove();h2.remove()
    data=dict(status='PASS',torch=torch.__version__,cuda=torch.version.cuda,gpu=torch.cuda.get_device_name(),compute_capability=torch.cuda.get_device_capability(),total_vram_bytes=torch.cuda.get_device_properties(0).total_memory,tensor_update_save_reload=True,cuda_forward_calls=cuda_calls[0],model_load_seconds=load,kernel_p50_ms=float(np.percentile(kernel,50)),kernel_p95_ms=float(np.percentile(kernel,95)),kernel_fps=1000/float(np.mean(kernel)),image_pipeline_p50_ms=float(np.percentile(elapsed,50)),image_pipeline_p95_ms=float(np.percentile(elapsed,95)),image_pipeline_fps=1000/float(np.mean(elapsed)),pipeline_scope='PIL RGB already decoded -> preprocess -> CUDA forward -> postprocess -> CPU detections; excludes video decode/display',peak_vram_allocated_bytes=torch.cuda.max_memory_allocated(),peak_vram_reserved_bytes=torch.cuda.max_memory_reserved(),process_rss_bytes=psutil.Process().memory_info().rss,predictions=converted,empty_result=empty_contract,kernel_samples_ms=kernel,pipeline_samples_ms=elapsed)
    (output/'result.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in data.items() if not k.endswith('samples_ms')},ensure_ascii=False))


if __name__=='__main__':run(*sys.argv[1:])
