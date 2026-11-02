"""Read-only CUDA reload/inference in the media-free candidate environment."""
import hashlib
import importlib.util
import json
import os
import sys
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
folder=sys.argv[1] if len(sys.argv)>1 else 'rf-inference-final'
if Path(folder).name!=folder:raise ValueError('Output must be a simple local evidence name')
OUT=ROOT/'artifacts/permissive-20261102'/folder
os.environ.update(HF_HUB_OFFLINE='1',HF_HUB_DISABLE_TELEMETRY='1',DO_NOT_TRACK='1',WANDB_MODE='disabled',HF_DATASETS_OFFLINE='1')

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    from ivad_app.compute.offline_policy import enforce_offline_worker
    enforce_offline_worker()
    OUT.mkdir(exist_ok=False)
    os.environ.update(MPLCONFIGDIR=str(OUT/'mpl'),HF_HOME=str(OUT/'hf'))
    import torch
    import cv2
    import torchvision
    from rfdetr import RFDETRNano
    from ivad_app.compute.gpu_lock import gpu_lease
    from ivad_app.video.windows_source import WindowsVideoSource
    from scripts.permissive.media_probe import loaded_modules
    assert torch.cuda.is_available(), 'No CPU fallback'
    assert importlib.util.find_spec('av') is None
    assert importlib.util.find_spec('ultralytics') is None
    assert not cv2.videoio_registry.hasBackend(cv2.CAP_FFMPEG)
    assert not torchvision.io._video_opt._HAS_VIDEO_OPT
    project=ROOT.parent/'测试1号/IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2'
    baseline=json.loads((OUT.parent/'before.json').read_text(encoding='utf8'))
    rows=[json.loads(r['details']) for r in baseline['tables']['model_versions'] if r['id'].startswith(('0d48a0e4','50de2cc6'))]
    assert len(rows)==2
    source=ROOT.parent/'测试1号/超高压压滤机/超高压车间8525压滤机_1026191715.mp4'
    frame=WindowsVideoSource(source).at(0)
    results=[]
    device=torch.cuda.get_device_properties(0)
    gpu_uuid=str(device.uuid)
    if not gpu_uuid.startswith('GPU-'):gpu_uuid='GPU-'+gpu_uuid
    with gpu_lease(ROOT,gpu_uuid,lambda:False):
        for row in rows:
            weight=project/row['path'];before=sha(weight)
            assert before==row['sha256']
            model=RFDETRNano(pretrain_weights=str(weight),num_classes=len(row['class_map']),resolution=384,device='cuda')
            model.model.model.to('cuda')
            assert all(p.is_cuda for p in model.model.model.parameters())
            proof={'cuda_forward':False}
            def hook(module,args):
                assert all(p.is_cuda for p in module.parameters())
                proof['cuda_forward']=True
            handle=model.model.model.register_forward_pre_hook(hook)
            torch.cuda.reset_peak_memory_stats();torch.cuda.synchronize();start=time.perf_counter()
            prediction=model.predict(frame.image,threshold=.5)
            torch.cuda.synchronize();seconds=time.perf_counter()-start
            handle.remove()
            assert proof['cuda_forward'] and before==sha(weight)
            boxes=prediction.xyxy.tolist();scores=prediction.confidence.tolist();classes=prediction.class_id.tolist()
            assert all(0<=v<=1 for v in scores)
            assert all(0<=c<len(row['class_map']) for c in classes)
            assert all(0<=b[0]<b[2]<=frame.image.width and 0<=b[1]<b[3]<=frame.image.height for b in boxes)
            results.append(dict(model_path=row['path'],sha256=before,seconds=seconds,peak_allocated_bytes=torch.cuda.max_memory_allocated(),proof=proof,boxes=boxes,scores=scores,classes=classes))
            del model
            torch.cuda.empty_cache()
    modules=loaded_modules()
    forbidden=('ffmpeg','avcodec','avformat','avutil','swscale','swresample','qt6','pyside')
    assert not any(any(s in Path(p).name.lower() for s in forbidden) for p in modules)
    result=dict(status='PASS-technical-inference-only',license_status='BLOCKED',gpu=device.name,models=results,
                source_time=frame.timestamp_evidence,loaded_modules=modules,python_imports=sorted(sys.modules),
                limitation='Existing NVIDIA training-source playback, not IDS compatibility or independent accuracy; no new training')
    (OUT/'result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'loaded_modules','python_imports'}},ensure_ascii=False))

if __name__=='__main__':main()
