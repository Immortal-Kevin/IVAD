"""Intel UI extraction using the already verified NVIDIA MF source adapter."""
import json
import math
from pathlib import Path
import sys
from ivad_app.video.windows_source import WindowsVideoSource


def run(request):
    source=WindowsVideoSource(request['source'])
    stage=Path(request['stage']);stage.mkdir(parents=True,exist_ok=True)
    def check():
        if (stage/'cancel').exists():raise InterruptedError('cancelled')
    source.check_cancel=check
    next_time=request['start']*1_000_000
    seen=set(request['seen']);frames=[]
    iterator=source.iter_frames(int(next_time),int(request['end']*1_000_000) if request['end']<1e15 else None)
    try:
        for frame in iterator:
            check()
            if frame.time_us>=request['end']*1_000_000:break
            if frame.time_us < next_time:continue
            next_time=(request['start']+(math.floor((frame.time_us/1e6-request['start'])/request['seconds']+1e-9)+1)*request['seconds'])*1e6
            ticks=frame.timestamp_evidence['mf_presentation_ticks']
            if ticks in seen:continue
            seen.add(ticks)
            path=stage/(str(len(frames))+'.png')
            if not request['plan']:frame.image.save(path)
            frames.append({'path':str(path),'data':{'video_id':request['video'],
                'width':frame.image.width,'height':frame.image.height,
                'pts_us':ticks//10,'source_timestamp_100ns':ticks,
                'time_source':'media_foundation_sample','state':'unannotated',
                'relative_time_us':frame.time_us,'timestamp_evidence':frame.timestamp_evidence,
                'source_pts_us':frame.pts_us,'sampling_interval_seconds':request['seconds']}})
            (stage/'progress').write_text(str(len(frames)),encoding='utf8')
            if len(frames)>=request['maximum']:break
    finally:iterator.close()
    return frames


if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8-sig'))
    try:
        frames=run(request)
        Path(request['stage'],'result.json').write_text(json.dumps(frames),encoding='utf8')
    except Exception as exc:
        Path(request['stage'],'error.txt').write_text(str(exc),encoding='utf8');sys.exit(2 if isinstance(exc,InterruptedError) else 1)
