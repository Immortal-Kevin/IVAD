"""Real MediaService import/extract/clip regression on a NEW local project."""
import importlib.abc
import json
import sys
import threading
from uuid import uuid4
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

class Guard(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname.split('.')[0] in {'av', 'cv2', 'PySide6', 'shiboken6', 'ultralytics', 'numpy'}:
            raise ImportError('Forbidden target dependency: ' + fullname)

sys.meta_path.insert(0, Guard())
from ivad_app.core.application import ApplicationServices
from scripts.permissive.media_probe import loaded_modules

class Context:
    job_id = 'permissive-media-fixture'
    cancel = threading.Event()
    def check(self): pass
    def log(self, value): pass
    def progress(self, value): pass

def main():
    out = ROOT / 'artifacts/permissive-20261102' / ('service-' + uuid4().hex[:8])
    if out.exists():
        raise RuntimeError('Test directory already exists')
    out.mkdir()
    app = ApplicationServices(ROOT, out / 'runtime', media_backend='windows-mf')
    result = {}
    try:
        project = app.projects.create(str(out), 'Windows 原生媒体独立测试')
        source = ROOT.parent / '测试1号/超高压压滤机/超高压车间8525压滤机_1026191715.mp4'
        c = Context()
        imported = app.media.import_batch(c, dict(root=project.root, paths=[str(source)], mode='REFERENCE'))
        assert len(imported['imported']) == 1, imported
        mid = imported['imported'][0]
        payload = dict(root=project.root, media_id=mid, options=dict(mode='fixed', start_us=5_000_000, end_us=7_000_000, interval_us=200_000, maximum=100, format='PNG'))
        frames = app.media.extract(c, payload)
        again = app.media.extract(c, payload)
        assert frames['count'] == 10 and frames == again
        saved = app.media.frames(project.root)
        assert all(f['parameters']['timestamp_evidence']['clock_domain'] == 'mpeg-pes-90khz' for f in saved)
        clip = app.media.save_video_clip(c, dict(root=project.root, media_id=mid, start_us=5_000_000, end_us=7_000_000, name='Windows clip'))
        assert clip['frames'] == 50, clip
        selected = dict(payload, media_id=clip['media_id'], options=dict(payload['options'], start_us=0, end_us=1_900_000))
        clip_frames = app.media.extract(c, selected)
        assert clip_frames['count'] == 10
        check = app.media.check(project.root)
        assert check['status'] == 'PASS', check
        result.update(project=str(project.root), imported=imported, extracted=frames, retry=again, clip=clip, clip_frames=clip_frames, consistency=check, loaded_modules=loaded_modules(), python_imports=sorted(sys.modules))
        forbidden = ('avcodec','avformat','avutil','swscale','swresample','ffmpeg','qt6','pyside')
        assert not any(any(x in Path(p).name.lower() for x in forbidden) for p in result['loaded_modules'])
        result['status'] = 'PASS'
    finally:
        app.close()
        (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k:v for k,v in result.items() if k not in {'loaded_modules','python_imports'}}, ensure_ascii=False))

if __name__ == '__main__':
    main()
