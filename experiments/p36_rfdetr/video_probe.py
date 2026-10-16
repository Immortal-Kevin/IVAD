"""Real video decode -> actual CUDA inference -> serialized result timing, no GUI."""
import json
import hashlib
import sys
import time
from pathlib import Path

sys.path.insert(0,str(Path(__file__).parent))
from adapter import NanoAdapter,convert


def run(weights,video,output):
    import av
    import torch
    import numpy as np
    from PIL import Image
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    adapter=NanoAdapter.restore(weights)
    with Path(weights).open('rb') as f:model_id='experimental-sha256:'+hashlib.file_digest(f,'sha256').hexdigest()
    names=dict(enumerate(adapter.model.class_names))
    records=[];timings=[]
    with av.open(video) as container:
        stream=container.streams.video[0]
        origin=(stream.start_time or 0)*stream.time_base
        decoded=container.decode(stream)
        warm=next(decoded).to_image()
        for _ in range(5):adapter.predict(warm)
        for _ in range(30):
            begin=time.perf_counter()
            try:frame=next(decoded)
            except StopIteration:break
            image=frame.to_image();detections=adapter.predict(image,threshold=.25)
            torch.cuda.synchronize()
            record=convert(detections,width=frame.width,height=frame.height,class_names=names,context=dict(frame_id=None,camera_id='6cfade53-2a3d-4a78-b27b-415b567ab60d',media_id='12a11464-0581-4bf1-8977-47fbcd5364b7',time_us=round(float(frame.pts*stream.time_base-origin)*1e6),raw_pts=frame.pts,time_base=str(frame.time_base),model_version=model_id))
            json.dumps(record,ensure_ascii=False,allow_nan=False)
            timings.append(time.perf_counter()-begin);records.append(record)
        result=dict(status='PASS',av=av.__version__,video=str(video),fps=float(stream.average_rate),time_base=str(stream.time_base),start_pts=stream.start_time,duration_seconds=float(stream.duration*stream.time_base),frames=len(records),pipeline_fps=len(records)/sum(timings),pipeline_p50_ms=float(np.percentile(timings,50)*1000),pipeline_p95_ms=float(np.percentile(timings,95)*1000),scope='sequential PyAV decode + PIL conversion + preprocess + CUDA prediction + postprocess + JSON serialization; excludes model load, warmup, GUI/render/file write',records=records)
    (output/'video-result.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k!='records'},ensure_ascii=False))


if __name__=='__main__':run(*sys.argv[1:])
