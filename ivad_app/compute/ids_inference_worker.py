"""One local image, existing RF-DETR Nano CUDA adapter; no CPU fallback."""
import json
import os
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from ivad_app.compute.offline_policy import enforce_offline_worker
import hashlib
def file_hash(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main(request):
    enforce_offline_worker()
    import torch
    from PIL import Image
    from rfdetr import RFDETRNano
    from ivad_app.compute.gpu_lock import gpu_lease
    if not torch.cuda.is_available():raise RuntimeError('CUDA_REQUIRED')
    weights=Path(request['weights']);image=Path(request['image'])
    if file_hash(weights)!=request['weights_sha256'] or file_hash(image)!=request['image_sha256']:raise ValueError('INPUT_HASH_CHANGED')
    with gpu_lease(Path(request['repo']),request['gpu_uuid'],lambda:False):
        model=RFDETRNano(pretrain_weights=str(weights),num_classes=request['classes'],resolution=384,device='cuda')
        model.model.model.to('cuda');proof=[]
        def hook(module,args):
            assert all(p.is_cuda for p in module.parameters());proof.append(True)
        handle=model.model.model.register_forward_pre_hook(hook)
        with Image.open(image) as im:prediction=model.predict(im.convert('RGB'),threshold=.5)
        torch.cuda.synchronize();handle.remove();assert proof
        assert file_hash(weights)==request['weights_sha256']
        return {'status':'PASS','cuda_forward':True,'detections':len(prediction.xyxy),'weights_unchanged':True}

if __name__=='__main__':
    req=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
    result=main(req);Path(req['output']).write_text(json.dumps(result),encoding='utf8')
