"""Evaluate actual CUDA predictions against the unchanged experiment COCO copy."""
import json
import hashlib
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('HF_HUB_DISABLE_TELEMETRY','1')
sys.path.insert(0,str(Path(__file__).parent))
from adapter import NanoAdapter,convert


def iou(a,b):
    x=max(0,min(a[2],b[2])-max(a[0],b[0]));y=max(0,min(a[3],b[3])-max(a[1],b[1]))
    intersection=x*y
    return intersection/((a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-intersection)


def run(weights,dataset,output):
    import torch
    from PIL import Image
    from pycocotools.coco import COCO
    from pycocotools.cocoeval import COCOeval
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    root=Path(dataset);raw=json.loads((root/'valid/_annotations.coco.json').read_text(encoding='utf8'))
    provenance=json.loads((root/'provenance.json').read_text(encoding='utf8'))
    sources={p['sample']['frame_id']:p['sample'] for p in provenance['samples']}
    with Path(weights).open('rb') as f:model_id='experimental-sha256:'+hashlib.file_digest(f,'sha256').hexdigest()
    model=NanoAdapter.restore(weights)
    names=model.model.class_names;names=names if isinstance(names,dict) else dict(enumerate(names))
    expected={c['id']:c['name'] for c in raw['categories']}
    if names!=expected:raise ValueError(f'Class mapping mismatch: {names} / {expected}')
    gt={i['id']:[] for i in raw['images']}
    for a in raw['annotations']:
        x,y,w,h=a['bbox'];gt[a['image_id']].append((a['category_id'],[x,y,x+w,y+h]))
    calls=[0]
    def guard(module,args):
        if not all(p.is_cuda for p in module.parameters()):raise RuntimeError('CPU AI inference forbidden')
        calls[0]+=1
    hook=model.model.model.model.register_forward_pre_hook(guard)
    predictions=[];records=[];tp=fp=fn=0;timings=[]
    for image in raw['images']:
        start=time.perf_counter()
        rgb=Image.open(root/'valid'/image['file_name']).convert('RGB')
        det=model.predict(rgb,threshold=.001);torch.cuda.synchronize()
        timings.append(time.perf_counter()-start)
        source=sources[image['ivad_frame_id']]
        record=convert(det,width=image['width'],height=image['height'],class_names=names,context=dict(frame_id=image['ivad_frame_id'],camera_id=source['camera_id'],media_id=source['media_id'],time_us=source['time_us'],model_version=model_id))
        records.append(record)
        candidates=sorted(record['boxes'],key=lambda b:-b['confidence']);matched=set()
        for box in candidates:
            x1,y1,x2,y2=box['xyxy']
            predictions.append(dict(image_id=image['id'],category_id=box['class_id'],score=box['confidence'],bbox=[x1,y1,x2-x1,y2-y1]))
            if box['confidence']<.25:continue
            available=[(iou(box['xyxy'],g[1]),j) for j,g in enumerate(gt[image['id']]) if j not in matched and g[0]==box['class_id']]
            overlap,j=max(available,default=(0,-1))
            if overlap>=.5:tp+=1;matched.add(j)
            else:fp+=1
        fn+=len(gt[image['id']])-len(matched)
    selected=[next(i for i in raw['images'] if not gt[i['id']]),next(i for i in raw['images'] if gt[i['id']])]
    batch=model.predict([Image.open(root/'valid'/i['file_name']).convert('RGB') for i in selected],threshold=.25)
    if not isinstance(batch,list) or len(batch)!=2:raise RuntimeError('Invalid batch output cardinality')
    batch_records=[]
    for image,det in zip(selected,batch):
        source=sources[image['ivad_frame_id']]
        batch_records.append(convert(det,width=image['width'],height=image['height'],class_names=names,context=dict(frame_id=image['ivad_frame_id'],camera_id=source['camera_id'],media_id=source['media_id'],time_us=source['time_us'],model_version=model_id)))
    hook.remove()
    coco=COCO(str(root/'valid/_annotations.coco.json'))
    if not predictions:raise RuntimeError('No predictions for AP evaluator; record zero separately')
    predicted=coco.loadRes(predictions);evaluation=COCOeval(coco,predicted,'bbox');evaluation.params.maxDets=[1,10,100]
    evaluation.evaluate();evaluation.accumulate();evaluation.summarize()
    data=dict(status='PASS',limitation='LIMITED same-source train/val; no independent industrial test',class_names=names,cuda_forward_calls=calls[0],batch_test=dict(status='PASS',normal_and_abnormal_inputs=True,records=batch_records),map50_95=float(evaluation.stats[0]),map50=float(evaluation.stats[1]),precision_at_conf025_iou050=tp/(tp+fp) if tp+fp else 0,recall_at_conf025_iou050=tp/(tp+fn) if tp+fn else 0,tp=tp,fp=fp,fn=fn,metric_scope='40-image validation; COCO AP maxDets100, prediction cutoff .001; P/R greedy same-class IoU .5 at confidence .25',pipeline_fps=len(timings)/sum(timings),pipeline_scope='image file decode + preprocess + CUDA prediction + postprocess, excludes GUI/video decode',predictions=records)
    (output/'evaluation.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'coco-predictions.json').write_text(json.dumps(predictions),encoding='utf8')
    print(json.dumps({k:v for k,v in data.items() if k!='predictions'},ensure_ascii=False))


if __name__=='__main__':run(*sys.argv[1:])
