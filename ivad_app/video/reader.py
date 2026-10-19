"""PyAV/FFmpeg实际PTS，统一播放器和抽帧时间定义；不按FPS推算。"""
from dataclasses import dataclass
from fractions import Fraction
from itertools import chain
from pathlib import Path
import av
from PIL import Image
from ivad_app.core.contracts import AppError
from ivad_app.video.timestamps import relative_time_us

@dataclass
class VideoFrame:
    image: Image.Image
    pts_us: int
    time_us: int
    index: int | None
    rotation: int

def micros(value, base): return int(round(Fraction(value) * base * 1000000))

def open_local_video(path):
    from ivad_app.core.demo_policy import enabled
    # Python socket hooks cannot see native FFmpeg protocol handlers. Restrict
    # nested playlist/media references too, rather than only checking the path.
    options = {'protocol_whitelist': 'file'} if enabled() else {}
    return av.open(str(path), timeout=(5, 10), options=options)

def image_of(frame, rotation):
    image = frame.to_image().convert('RGB')
    angle = int(round(rotation)) % 360
    if angle not in {0, 90, 180, 270}:
        raise AppError('ROTATION_UNSUPPORTED', '视频包含非直角旋转，当前不支持精确显示和抽帧。')
    if angle: image = image.rotate(angle, expand=True)
    return image

class FileVideoSource:
    def __init__(self, path: Path, metadata: dict | None = None):
        self.path = Path(path)
        if not self.path.is_file(): raise AppError('MEDIA_MISSING', '视频文件Missing，请重新定位引用或恢复项目副本。')
        self.metadata = metadata or self.probe(self.path)

    @staticmethod
    def probe(path: Path) -> dict:
        try:
            with open_local_video(path) as container:
                if not container.streams.video: raise AppError('NO_VIDEO', '文件没有可解码的视频轨道。')
                stream = container.streams.video[0]
                frame = next(container.decode(stream), None)
                if frame is None: raise AppError('VIDEO_EMPTY', '视频没有可解码画面。')
                if frame.pts is None or frame.time_base is None: raise AppError('PTS_MISSING', '视频缺少可信PTS时间戳，已拒绝按FPS估计。')
                rotation = int(round(frame.rotation or float(stream.metadata.get('rotate', 0))))
                image = image_of(frame, rotation)
                origin_us = micros(stream.start_time, stream.time_base) if stream.start_time is not None else micros(frame.pts, frame.time_base)
                duration = micros(stream.duration, stream.time_base) if stream.duration is not None else container.duration
                if duration is None or duration <= 0: raise AppError('DURATION_UNKNOWN', '视频时长未知，当前无法安全设置抽帧范围。')
                rate = stream.average_rate
                return {'codec': stream.codec_context.name, 'container': container.format.name,
                        'width': frame.width, 'height': frame.height, 'display_width': image.width, 'display_height': image.height,
                        'duration_us': int(duration), 'time_base': str(stream.time_base), 'start_pts': stream.start_time,
                        'origin_us': origin_us, 'first_pts_us': micros(frame.pts, frame.time_base),
                        'nominal_fps': str(rate) if rate else None, 'declared_frames': stream.frames or None,
                        'rotation': rotation, 'capture_time': None, 'timestamp_policy': 'actual_frame_pts', 'decoder': 'PyAV/FFmpeg'}
        except AppError: raise
        except (av.error.FFmpegError, OSError, ValueError) as exc:
            raise AppError('VIDEO_DECODE', '视频损坏、无法读取或编码不受支持；扩展名不能保证可解码。') from exc

    def iter_frames(self, start_us: int = 0, end_us: int | None = None):
        with open_local_video(self.path) as container:
            stream = container.streams.video[0]
            indexed_seek=start_us>0 and not {'mpeg','mpegts'}.intersection(container.format.name.split(','))
            if indexed_seek:
                # Some MPEG recordings have coarse/incomplete seek indexes and
                # return a frame AFTER the requested time despite backward=True.
                # Back off using actual decoded PTS; finally decode from start.
                for retreat in [0,1000000,2000000,4000000,8000000,16000000,None]:
                    requested=0 if retreat is None else max(0,start_us-retreat)
                    target=Fraction(requested+self.metadata['origin_us'],1000000)/stream.time_base
                    container.seek(int(target),stream=stream,backward=True,any_frame=False)
                    decoded=container.decode(stream);first=next(decoded,None)
                    if first is None:continue
                    if first.pts is None or first.time_base is None:
                        raise AppError('PTS_MISSING','解码帧缺少PTS；停止处理，不按FPS补造时间。')
                    if relative_time_us(micros(first.pts,first.time_base),self.metadata)<=start_us or requested==0:
                        decoded=chain([first],decoded);break
                else:decoded=iter(())
            else:decoded=container.decode(stream)
            previous_pts = None
            for index, frame in enumerate(decoded):
                if frame.pts is None or frame.time_base is None:
                    raise AppError('PTS_MISSING', '解码帧缺少PTS；停止处理，不按FPS补造时间。')
                pts_us = micros(frame.pts, frame.time_base)
                if previous_pts is not None and pts_us <= previous_pts:
                    raise AppError('PTS_DISORDER', '显示帧PTS倒退或重复，停止处理以避免错误标注定位。')
                previous_pts = pts_us
                time_us = relative_time_us(pts_us,self.metadata)
                if time_us < start_us: continue
                if end_us is not None and time_us > end_us: break
                rotation = int(round(frame.rotation or self.metadata['rotation']))
                yield VideoFrame(image_of(frame, rotation), pts_us, time_us, index if start_us == 0 else None, rotation)

    def at(self, time_us: int, *, before=False) -> VideoFrame:
        if before:
            if {'mpeg','mpegts'}.intersection(self.metadata['container'].split(',')):
                previous=None
                for frame in self.iter_frames(max(0,time_us-2000000),time_us):
                    if frame.time_us>=time_us:break
                    previous=frame
                if previous:return previous
                return self._before_sequential(time_us)
            # 从前一个关键帧到目标顺序解码，返回严格早于目标的实际显示帧。
            with open_local_video(self.path) as container:
                stream = container.streams.video[0]
                target = Fraction(max(0, time_us) + self.metadata['origin_us'], 1000000) / stream.time_base
                container.seek(int(target), stream=stream, backward=True, any_frame=False)
                previous = None
                for frame in container.decode(stream):
                    if frame.pts is None: raise AppError('PTS_MISSING', '帧没有PTS时间戳。')
                    pts = micros(frame.pts, frame.time_base); relative = relative_time_us(pts,self.metadata)
                    current = VideoFrame(image_of(frame, int(round(frame.rotation or self.metadata['rotation']))), pts, relative, None, self.metadata['rotation'])
                    if relative >= time_us:
                        if previous: return previous
                        if time_us <= 0: return current
                        # 目标恰好是关键帧时需退到更早关键帧。
                        return self._before_sequential(time_us)
                    previous = current
                if previous: return previous
        else:
            iterator = self.iter_frames(max(0, int(time_us)))
            try:
                frame = next(iterator, None)
                if frame: return frame
            finally: iterator.close()
        raise AppError('FRAME_NOT_FOUND', '该时间位置没有可解码帧，请检查视频边界。')

    def _before_sequential(self, time_us):
        previous = None
        for frame in self.iter_frames():
            if frame.time_us >= time_us: break
            previous = frame
        if not previous: raise AppError('FRAME_NOT_FOUND', '已经位于首帧。')
        return previous
