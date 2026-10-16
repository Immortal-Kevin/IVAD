"""Experimental RF-DETR boundary. Never registers a production IVAD backend."""
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path


def assert_isolated():
    if importlib.util.find_spec('ultralytics') is not None:
        raise RuntimeError('RF experiment refuses an environment containing Ultralytics')
    if any(n.startswith('ultralytics') for n in sys.modules):
        raise RuntimeError('Ultralytics runtime contamination')


def convert(detections, *, width, height, class_names, context):
    """Validate actual model predictions and serialize original-pixel xyxy."""
    required=('frame_id','camera_id','media_id','time_us','model_version')
    if any(k not in context for k in required):
        raise ValueError('Incomplete source/model identity')
    boxes=[];background_removed=0;degenerate_removed=0
    emitted_names=getattr(detections,'data',{}).get('class_name',[])
    for index,(xyxy, score, cid) in enumerate(zip(detections.xyxy,detections.confidence,detections.class_id)):
        xyxy=[float(v) for v in xyxy];score=float(score);cid=int(cid)
        if not all(math.isfinite(v) for v in xyxy+[score]) or not 0<=score<=1:
            raise ValueError('Nonfinite or invalid confidence')
        # RF-DETR 1.11.2 may emit its explicit no-object slot at low thresholds.
        # Only drop the upstream-declared background, never an unknown fault ID.
        if cid not in class_names and index<len(emitted_names) and emitted_names[index]=='__background__':
            background_removed+=1;continue
        x1,y1,x2,y2=xyxy
        if x1>x2 or y1>y2 or cid not in class_names:
            raise ValueError(f'Invalid predicted box/class: {cid}, {xyxy}')
        clipped=[max(0.,min(float(width),x1)),max(0.,min(float(height),y1)),max(0.,min(float(width),x2)),max(0.,min(float(height),y2))]
        if clipped[0]>=clipped[2] or clipped[1]>=clipped[3]:
            degenerate_removed+=1;continue
        boxes.append(dict(xyxy=clipped,raw_xyxy=xyxy,confidence=score,class_id=cid,class_name=class_names[cid]))
    return dict(schema='ivad-rfdetr-experimental-v1',backend='rfdetr',status='EXPERIMENTAL / LIMITED',**context,boxes=boxes,background_removed=background_removed,degenerate_removed=degenerate_removed)


class NanoAdapter:
    backend='rfdetr-nano-experimental'

    def __init__(self,weights):
        assert_isolated()
        import torch
        from rfdetr import RFDETRNano
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA required; CPU AI fallback forbidden')
        self.model=RFDETRNano(pretrain_weights=str(Path(weights).resolve()),device='cuda')
        # 1.11.2 stages checkpoint loading on CPU and moves lazily on predict.
        # Make placement explicit so load/benchmark evidence has no ambiguity.
        self.model.model.model.to('cuda')

    def predict(self, images, threshold=.25):
        assert_isolated()
        return self.model.predict(images,threshold=threshold)

    @classmethod
    def restore(cls, checkpoint):
        assert_isolated()
        import torch
        from rfdetr import RFDETR
        if not torch.cuda.is_available():raise RuntimeError('CUDA required')
        instance=cls.__new__(cls)
        instance.model=RFDETR.from_checkpoint(checkpoint,device='cuda')
        instance.model.model.model.to('cuda')
        return instance

    @staticmethod
    def validate_dataset(directory):
        directory=Path(directory)
        summary={}
        for split in ('train','valid','test'):
            data=json.loads((directory/split/'_annotations.coco.json').read_text(encoding='utf8'))
            image_ids={i['id'] for i in data['images']}
            category_ids={c['id'] for c in data['categories']}
            for obj in data['annotations']:
                if obj['image_id'] not in image_ids or obj['category_id'] not in category_ids:raise ValueError('COCO orphan')
            summary[split]=dict(images=len(image_ids),objects=len(data['annotations']))
        return summary

    def export(self, destination):
        return self.model.export(output_dir=str(destination),fp16=False,verbose=False)


class TrainingJob:
    """Dedicated subprocess, cancellation sentinel; never touches registry/GUI."""
    def __init__(self,request):
        self.request=Path(request).resolve()
        self.output=Path(json.loads(self.request.read_text(encoding='utf8'))['output'])
        self.process=None

    def start(self, log):
        if self.process is not None:
            raise RuntimeError('Already started')
        self.process=subprocess.Popen([sys.executable,'-I','-X','utf8',str(Path(__file__).with_name('train.py')),str(self.request)],stdout=log,stderr=subprocess.STDOUT)

    def cancel(self):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError('No running experiment to cancel')
        self.request.with_suffix('.cancel.request').touch()

    def status(self):
        if self.process is None:return 'NOT_STARTED'
        rc=self.process.poll()
        if rc is None:return 'RUNNING'
        result=self.output/'experiment-result.json'
        if result.exists():return json.loads(result.read_text(encoding='utf8'))['status']
        return 'FAILED'
