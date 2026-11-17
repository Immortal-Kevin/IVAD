"""One-epoch SOFTWARE FIXTURE regression, explicitly NOT an Intel IDS test.

Independent scenes/splits, no industrial labels, no original DB or Registry
writes. Exercises the unchanged CUDA worker after progress/CA/media removal.
"""
import hashlib
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time
from uuid import uuid4
from PIL import Image, ImageDraw

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/permissive-20261102'/('rf-fixture-'+uuid4().hex[:8])

def main():
    sealed=json.loads((ROOT/'artifacts/permissive-20261102/compat-sealed.json').read_text(encoding='utf8'))
    assert sealed['excluded_absent'] and all(c['current_matches'] for c in sealed['checks'])
    site=ROOT/'.venv-rf-media-candidate/Lib/site-packages'
    manifest=json.loads((ROOT/'artifacts/permissive-20261102/compat-overlay/manifest.json').read_text(encoding='utf8'))
    assert all(hashlib.sha256((site/c['path']).read_bytes()).hexdigest()==c['after_sha256'] for c in manifest['patched'])
    OUT.mkdir()
    hashes=set()
    for split,count,seed in [('train',4,12345),('valid',2,98765)]:
        folder=OUT/'dataset'/split;folder.mkdir(parents=True)
        data=dict(info={'description':'IVAD SOFTWARE TEST FIXTURE; not IDS, not industrial truth'},licenses=[],
                  categories=[dict(id=0,name='IVAD software fixture rectangle',supercategory='IVAD software fixture rectangle')],images=[],annotations=[])
        rng=random.Random(seed)
        for index in range(count):
            image=Image.frombytes('RGB',(384,384),rng.randbytes(384*384*3))
            # Each split has independent scene generation, including normal negatives.
            name=f'{split}-{index}.png'
            if index!=count-1:
                x,y=rng.randrange(20,130),rng.randrange(20,130)
                ImageDraw.Draw(image).rectangle((x,y,x+80,y+90),fill=(rng.randrange(100,250),20,40))
                data['annotations'].append(dict(id=index+1,image_id=index+1,category_id=0,bbox=[x,y,80,90],area=7200,iscrowd=0,segmentation=[]))
            image.save(folder/name)
            sha=hashlib.sha256((folder/name).read_bytes()).hexdigest()
            assert sha not in hashes;hashes.add(sha)
            data['images'].append(dict(id=index+1,file_name=name,width=384,height=384,ivad_fixture_group=split,sha256=sha))
        (folder/'_annotations.coco.json').write_text(json.dumps(data,indent=2),encoding='utf8')
    weights=ROOT/'artifacts/p36-rfdetr-20261016/weights/rf-detr-nano.pth'
    with weights.open('rb') as f:weight_hash=hashlib.file_digest(f,'sha256').hexdigest()
    assert weight_hash=='d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d'
    request=dict(work=str(OUT),data=str(OUT/'dataset'),weights=str(weights),weights_sha256=weight_hash,
                 device_uuid='GPU-c942e790-0e56-4262-a96d-16122a858702',parameters=dict(epochs=1,batch_size=2),
                 operation='train',class_names=['IVAD software fixture rectangle'],fixture_only=True)
    (OUT/'request.json').write_text(json.dumps(request,indent=2),encoding='utf8')
    env=dict(os.environ,HF_HUB_OFFLINE='1',HF_DATASETS_OFFLINE='1',WANDB_MODE='disabled',DO_NOT_TRACK='1',CUDA_VISIBLE_DEVICES=request['device_uuid'])
    cancel_test='--cancel' in sys.argv
    with (OUT/'worker.log').open('w',encoding='utf8') as log:
        child=subprocess.Popen([str(ROOT/'.venv-rf-media-candidate/Scripts/python.exe'),'-I','-X','utf8',str(ROOT/'ivad_app/compute/rfdetr_train_worker.py'),str(OUT/'request.json')],stdout=log,stderr=subprocess.STDOUT,env=env)
        deadline=time.monotonic()+300
        while child.poll() is None:
            if cancel_test and 'GPU available: True' in (OUT/'worker.log').read_text(encoding='utf8',errors='replace'):
                (OUT/'cancel.request').touch()
            if time.monotonic()>deadline:
                (OUT/'cancel.request').touch()
                child.wait(timeout=30)
                raise TimeoutError('Owned CUDA fixture exceeded deadline')
            time.sleep(.1)
    result=json.loads((OUT/'result.json').read_text(encoding='utf8'))
    result['fixture_only']=True
    result['ids_compatibility']='NOT VERIFIED: real Intel files unavailable'
    result['registered_industrial_model']=False
    if cancel_test:
        assert result['status']=='CANCELLED' and '训练batch边界取消' in result.get('error',''),result
        assert (OUT/'run/cancelled.ckpt').is_file()
        sys.path.insert(0,str(ROOT))
        from ivad_app.compute.gpu_lock import gpu_lease
        with gpu_lease(ROOT,request['device_uuid'],lambda:False):pass
        result['cancelled_gpu_lock_released']=True
    (OUT/'scope.json').write_text(json.dumps({k:result[k] for k in ['fixture_only','ids_compatibility','registered_industrial_model']},indent=2),encoding='utf8')
    print(json.dumps(dict(directory=str(OUT),status=result['status'],error=result.get('error'),evidence=result.get('evidence'),seconds=result['seconds'],fixture_only=True)))
    return 0 if cancel_test else child.returncode

if __name__=='__main__':raise SystemExit(main())
