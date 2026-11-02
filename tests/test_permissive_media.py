"""Native MF integration plus explicit failure/clock-provenance contracts."""
import json
import sys
import threading
import subprocess
from pathlib import Path
import pytest
from PIL import Image
from ivad_app.core.application import ApplicationServices
from ivad_app.core.contracts import AppError
from ivad_app.video.windows_mf import SourceReader, sniff_container
from ivad_app.video.windows_sink import Mp4Writer
from ivad_app.video.windows_source import WindowsVideoSource
from ivad_app.video.ps_timestamps import verify_frame_association

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / 'artifacts/p2/samples/sample.mp4'

class Context:
    job_id='native-media-test'
    cancel=threading.Event()
    def check(self): pass
    def progress(self, value): pass
    def log(self, value): pass

def test_reopen_aperture_and_seek():
    source=WindowsVideoSource(SAMPLE)
    first=source.at(0)
    assert first.image.size==(320,180)
    assert source.at(200000).time_us==200000
    assert source.at(200000,before=True).time_us==160000
    assert WindowsVideoSource(SAMPLE).at(0).image.tobytes()==first.image.tobytes()

def test_source_clock_does_not_silently_rebase_history():
    with pytest.raises(AppError,match='时间原点'):
        WindowsVideoSource(SAMPLE,dict(origin_us=999999))

@pytest.mark.parametrize('packets,ticks',[
    ([],[]),
    ([dict(raw_pts=5,stream=224)],[0,1]),
    ([dict(raw_pts=5,stream=224),dict(raw_pts=4,stream=224)],[0,1]),
    ([dict(raw_pts=5,stream=224),dict(raw_pts=9005,stream=224)],[0,400000]),
    ([dict(raw_pts=5,stream=224),dict(raw_pts=3605,stream=225)],[0,400000]),
])
def test_ambiguous_pts_refused(packets,ticks):
    with pytest.raises(ValueError):verify_frame_association(packets,ticks)

def test_sniff_does_not_trust_extension(tmp_path):
    path=tmp_path/'fake.mp4';path.write_bytes(b'not a video')
    assert sniff_container(path)=='unrecognized'
    with pytest.raises(Exception):SourceReader(path)

def test_noninteger_fps_preserves_actual_ticks(tmp_path):
    path=tmp_path/'fractional.mp4'
    stamps=[round(i*10010000/30) for i in range(12)]
    with SourceReader(SAMPLE):
        with Mp4Writer(path,64,48,(30000,1001)) as writer:
            for i,pts in enumerate(stamps):
                pixels=Image.new('RGB',(64,48),(i*10,80,20)).tobytes('raw','BGRX')
                writer.write(pixels,pts,stamps[1])
    with SourceReader(path) as reader:
        actual=[f.pts for f in reader.frames()]
    assert len(actual)==len(stamps)
    # MF MP4 sink selects an integer timescale (29970 on this Windows build).
    # Contract is <=1us, matching IVAD persisted time precision, not bit-exact
    # preservation of the encoder's 100ns input clock across container muxing.
    assert max(abs(a-b) for a,b in zip(actual,stamps))<=10

def test_vfr_clip_preserves_every_pts(tmp_path):
    sample=ROOT/'artifacts/p2/samples/vfr.mp4'
    source=WindowsVideoSource(sample)
    end=source.metadata['duration_us']
    expected=[f.time_us for f in source.iter_frames() if f.time_us<end]
    assert len(set(b-a for a,b in zip(expected,expected[1:])))>1
    output=tmp_path/'clip.mp4.partial'
    result=source.encode_clip(source,output,0,end,Context())
    actual=[f.time_us for f in WindowsVideoSource(output).iter_frames()]
    assert result[0]==len(expected) and actual==expected

def test_cancel_while_skipping_to_range():
    source=WindowsVideoSource(SAMPLE)
    def stop():raise InterruptedError('cancelled')
    source.check_cancel=stop
    with pytest.raises(InterruptedError):list(source.iter_frames(1000000))

def test_clip_cancel_and_invalid_range_leave_no_registry_record(tmp_path):
    app=ApplicationServices(ROOT,tmp_path/'runtime',media_backend='windows-mf')
    try:
        project=app.projects.create(str(tmp_path),'MF cancel fixture')
        imported=app.media.import_batch(Context(),dict(root=project.root,paths=[str(SAMPLE)],mode='REFERENCE'))
        mid=imported['imported'][0]
        class Cancel(Context):
            calls=0
            def check(self):
                self.calls+=1
                if self.calls>9:raise InterruptedError('cancel')
        payload=dict(root=project.root,media_id=mid,start_us=0,end_us=1000000)
        with pytest.raises(InterruptedError):app.media.save_video_clip(Cancel(),payload)
        assert len(app.media.list(project.root))==1
        assert not list((Path(project.root)/'media').glob('*'))
        with pytest.raises(AppError):app.media.save_video_clip(Context(),dict(payload,end_us=0))
        assert app.media.check(project.root)['status']=='PASS'
    finally:app.close()

def test_closed_or_wrong_thread_reader_rejected():
    reader=SourceReader(SAMPLE);reader.close()
    with pytest.raises(RuntimeError):next(reader.frames())

def test_isolated_decoder_owned_failure_does_not_kill_caller():
    from ivad_app.video.isolated_mf import IsolatedSourceReader
    with IsolatedSourceReader(SAMPLE) as reader:
        subprocess.run(['taskkill','/PID',str(reader.worker.pid),'/T','/F'],capture_output=True,check=True)
        with pytest.raises(RuntimeError):list(reader.frames())
    assert WindowsVideoSource(SAMPLE).at(0).image.size==(320,180)

def test_isolated_response_deadline():
    from ivad_app.video.isolated_mf import IsolatedSourceReader
    with IsolatedSourceReader(SAMPLE) as reader:
        reader.timeout=-1  # controlled timeout injection, not an observed OS hang
        with pytest.raises(TimeoutError):next(reader.frames())
