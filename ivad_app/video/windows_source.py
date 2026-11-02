"""MF implementation of the existing IVAD FileVideoSource service contract."""
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from PIL import Image
from ivad_app.core.contracts import AppError
from .windows_mf import SourceReader as NativeSourceReader
from .isolated_mf import IsolatedSourceReader as SourceReader
from .ps_timestamps import video_pes_pts


@dataclass
class Frame:
    image: Image.Image
    pts_us: int
    time_us: int
    index: int | None
    rotation: int
    timestamp_evidence: dict


class WindowsVideoSource:
    def __init__(self, path, metadata=None):
        self.path = Path(path)
        self.check_cancel = lambda: None
        actual = self.probe(self.path)
        if metadata and metadata.get('origin_us') != actual['origin_us']:
            raise AppError('CLOCK_DOMAIN_CHANGED', '历史媒体与系统解码器的时间原点不同；停止写入，需独立核对时间映射。')
        self.metadata = actual

    @staticmethod
    def probe(path):
        with SourceReader(path) as reader:
            frames = reader.frames()
            try:
                first = next(frames)
            except StopIteration as exc:
                raise AppError('VIDEO_EMPTY', '没有可解码视频帧。') from exc
            finally:
                frames.close()
            packets = video_pes_pts(path) if reader.container == 'mpeg-ps' else []
            base = Fraction(1, 90000) if packets else Fraction(1, 10000000)
            start = packets[0]['raw_pts'] if packets else first.pts
            origin = round(start * base * 1_000_000)
            rotation = reader.rotation
            dimensions = [first.width, first.height]
            if rotation in (90, 270):
                dimensions.reverse()
            rate = reader.frame_rate
            return dict(codec=reader.codec, container=reader.container,
                        width=first.width, height=first.height, display_width=dimensions[0], display_height=dimensions[1],
                        duration_us=round(reader.duration_ticks / 10), time_base=str(base), start_pts=start,
                        origin_us=origin, first_pts_us=origin, nominal_fps=str(Fraction(*rate)) if rate and rate[1] else None,
                        declared_frames=None, rotation=rotation, capture_time=None, decoder='Windows Media Foundation',
                        timestamp_policy='verified-pes-to-mf' if packets else 'mf-presentation-clock',
                        clock_domain='mpeg-pes-90khz' if packets else first.clock_domain,
                        mf_origin_ticks=first.pts)

    def iter_frames(self, start_us=0, end_us=None):
        packets = video_pes_pts(self.path) if self.metadata['timestamp_policy'] == 'verified-pes-to-mf' else []
        previous = None
        with SourceReader(self.path) as reader:
            count = 0
            for index, frame in enumerate(reader.frames(check=self.check_cancel)):
                self.check_cancel()
                count += 1
                if previous is not None and frame.pts <= previous:
                    raise AppError('PTS_DISORDER', '系统解码帧时间戳重复或倒退，已停止。')
                previous = frame.pts
                relative_ticks = frame.pts - self.metadata['mf_origin_ticks']
                if packets:
                    if index >= len(packets):
                        raise AppError('PTS_MAPPING', 'PES数量与解码帧数量不一致。')
                    raw = packets[index]['raw_pts']
                    if abs((raw - packets[0]['raw_pts']) * 10000000 - relative_ticks * 90000) > 90000:
                        raise AppError('PTS_MAPPING', '原始PES与解码帧时间戳不对应，拒绝猜测。')
                    pts_us = round(Fraction(raw, 90000) * 1000000)
                    domain = 'mpeg-pes-90khz'
                    base = '1/90000'
                else:
                    raw, base, domain = frame.pts, '1/10000000', frame.clock_domain
                    pts_us = round(Fraction(raw, 10))
                relative = pts_us - self.metadata['origin_us']
                if relative < start_us:
                    continue
                if end_us is not None and relative > end_us:
                    return
                image = Image.frombytes('RGB', (frame.width, frame.height), frame.pixels, 'raw', 'BGRX', frame.stride, 1)
                if reader.rotation:
                    image = image.rotate(reader.rotation, expand=True)
                yield Frame(image, pts_us, relative, index, reader.rotation,
                            dict(raw_pts=raw, time_base=base, clock_domain=domain,
                                 mf_presentation_ticks=frame.pts, mf_time_base='1/10000000'))
            if packets and count != len(packets):
                raise AppError('PTS_MAPPING', '完整解码帧数与PES记录不一致。')

    def at(self, time_us, *, before=False):
        previous = None
        iterator = self.iter_frames()
        try:
            for frame in iterator:
                if frame.time_us >= time_us:
                    if before and previous is not None:
                        return previous
                    return frame
                previous = frame
            if before and previous is not None:
                return previous
        finally:
            iterator.close()
        raise AppError('FRAME_NOT_FOUND', '指定时间没有视频帧。')

    @staticmethod
    def encode_clip(source, stage, start, end, context):
        """Existing service owns transaction and cleanup; writer owns no DB."""
        from .windows_sink import Mp4Writer
        source.check_cancel = context.check
        # Keep MF initialized throughout encoder lifetime, including finalization.
        with NativeSourceReader(source.path):
            iterator = source.iter_frames(start, end)
            writer = None
            first = last = None
            count = 0
            pending = None
            try:
                for frame in iterator:
                    context.check()
                    if frame.time_us >= end:
                        break
                    if writer is None:
                        first = frame.time_us
                        writer = Mp4Writer(stage, frame.image.width, frame.image.height,
                                           tuple(Fraction(source.metadata['nominal_fps'] or '25').as_integer_ratio()))
                    if pending is not None:
                        writer.write(pending.image.tobytes('raw', 'BGRX'), (pending.time_us - first) * 10,
                                     (frame.time_us - pending.time_us) * 10)
                    pending = frame
                    count += 1
                    last = frame.time_us
                    context.progress(min(90, (last-start)*90/(end-start)))
                if count < 2:
                    raise AppError('CLIP_SHORT', '所选范围不足两帧。')
                # Final duration is bounded by the requested interval, never a fabricated PTS.
                writer.write(pending.image.tobytes('raw', 'BGRX'), (last-first)*10, max(1, (end-last)*10))
                writer.close()
                return count, first, last
            except BaseException:
                if writer:
                    writer.close(False)
                raise
            finally:
                iterator.close()
