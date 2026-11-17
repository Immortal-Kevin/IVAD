import threading, json
from pathlib import Path
import pytest
from ivad_app.jobs.manager import JobContext
from ivad_app.core.contracts import AppError
from ivad_app.video.reader import FileVideoSource
from scripts.p2.make_samples import make_all

@pytest.fixture(scope='session')
def sample_videos(tmp_path_factory): return make_all(tmp_path_factory.mktemp('p2-video'))

class Context:
    job_id = 'test'
    def __init__(self): self.cancel=threading.Event(); self.values=[]
    def check(self):
        if self.cancel.is_set(): raise AppError('JOB_CANCELLED','取消')
    def progress(self,x): self.check(); self.values.append(x)
    def log(self,x): pass

@pytest.mark.parametrize('name',['sample.mp4','sample.avi','sample.mov','sample.mkv','vfr.mp4','noninteger.mp4','rotation.mp4'])
def test_real_decode_actual_pts(sample_videos, name):
    source = FileVideoSource(sample_videos/name)
    frames = list(source.iter_frames())
    assert len(frames)==36 and all(a.pts_us < b.pts_us for a,b in zip(frames,frames[1:]))
    chosen=source.at(frames[8].time_us)
    assert chosen.pts_us==frames[8].pts_us
    assert source.at(chosen.time_us,before=True).pts_us==frames[7].pts_us
    if name=='vfr.mp4': assert len({b.pts_us-a.pts_us for a,b in zip(frames,frames[1:])})>1
    if name=='rotation.mp4': assert source.metadata['rotation']%360 in {90,270} and chosen.image.size==(180,320)
    if name=='noninteger.mp4': assert source.metadata['nominal_fps']=='30000/1001'

def test_corrupt_video_no_fake_metadata(sample_videos):
    with pytest.raises(AppError): FileVideoSource(sample_videos/'corrupt.mp4')

@pytest.mark.parametrize('pts',[[None],[0,0],[10,0]])
def test_controlled_decoder_missing_duplicate_backward_pts(sample_videos,monkeypatch,pts):
    # Fault injection explicitly distinguished from a real malformed codec sample.
    from fractions import Fraction
    from types import SimpleNamespace
    import av
    source=FileVideoSource(sample_videos/'sample.mp4')
    frames=[]
    for value in pts:
        frame=av.VideoFrame(320,180,'rgb24');frame.pts=value;frame.time_base=Fraction(1,1000);frames.append(frame)
    class Container:
        streams=SimpleNamespace(video=[SimpleNamespace(time_base=Fraction(1,1000))])
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def decode(self,stream):return iter(frames)
    monkeypatch.setattr('ivad_app.video.reader.av.open',lambda *a,**k:Container())
    with pytest.raises(AppError):list(source.iter_frames())
