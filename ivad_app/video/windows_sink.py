"""MP4/H.264 through Windows MF Sink Writer. No external codec executable."""
import ctypes as C
from pathlib import Path
from .windows_mf import (GUID, PTR, U32, U64, I64, PG, MAJOR, SUBTYPE,
                         VIDEO_TYPE, RGB32, SIZE, RATE, STRIDE, _call, _check, _release)

H264 = GUID('34363248-0000-0010-8000-00aa00389b71')
BITRATE = GUID('20332624-fb0d-4d9e-bd0d-cbf6786c102e')
INTERLACE = GUID('e2724bb8-e676-4806-b4b2-a8d6efb44ccd')
ASPECT = GUID('c6376a1e-8d0a-4027-be45-6d9a0ad39bb6')
CONTAINER = GUID('150ff23f-4abc-478b-ac4f-e1916fba1cca')
MPEG4 = GUID('dc6cd05d-b9d0-40ef-bd35-fa622c1ab28a')
SINK_EX = GUID('588d72ab-5bc1-496a-8714-b70617141b25')
NO_FRC = GUID('2c0afa19-7a97-4d5a-9ee8-16d4fc518d8c')


class Mp4Writer:
    """Call inside a SourceReader/MF lifetime. Input BGRX top-down pixels."""
    def __init__(self, path, width, height, rate=(25, 1), bitrate=8_000_000):
        if width % 2 or height % 2:
            raise ValueError('Windows H.264 requires even dimensions; no silent crop')
        if Path(path).exists():
            raise FileExistsError(path)
        self.width, self.height = width, height
        self.writer = PTR()
        self.closed = False
        self.last_pts = None
        self.mf = C.WinDLL('mfplat', winmode=0x800)
        self.rw = C.WinDLL('mfreadwrite', winmode=0x800)
        self.rw.MFCreateSinkWriterFromURL.argtypes = [C.c_wchar_p, PTR, PTR, C.POINTER(PTR)]
        self.mf.MFCreateMediaType.argtypes = [C.POINTER(PTR)]
        self.mf.MFCreateMemoryBuffer.argtypes = [U32, C.POINTER(PTR)]
        self.mf.MFCreateSample.argtypes = [C.POINTER(PTR)]
        self.mf.MFCreateAttributes.argtypes = [C.POINTER(PTR), U32]
        media, incoming, attrs = PTR(), PTR(), PTR()
        try:
            _check(self.mf.MFCreateAttributes(C.byref(attrs), 1), 'sink attributes')
            _check(_call(attrs, 24, [PG, PG], C.byref(CONTAINER), C.byref(MPEG4)), 'explicit MP4 container')
            _check(self.rw.MFCreateSinkWriterFromURL(str(Path(path).resolve()), None, attrs, C.byref(self.writer)), 'create MP4 sink')
            for ptr, subtype in [(media, H264), (incoming, RGB32)]:
                _check(self.mf.MFCreateMediaType(C.byref(ptr)), 'sink media type')
                for key, value in [(MAJOR, VIDEO_TYPE), (SUBTYPE, subtype)]:
                    _check(_call(ptr, 24, [PG, PG], C.byref(key), C.byref(value)), 'sink GUID')
                for key, value in [(SIZE, (width << 32) | height), (RATE, (rate[0] << 32) | rate[1]), (ASPECT, (1 << 32) | 1)]:
                    _check(_call(ptr, 22, [PG, U64], C.byref(key), value), 'sink ratio')
                _check(_call(ptr, 21, [PG, U32], C.byref(INTERLACE), 2), 'progressive output')
            _check(_call(media, 21, [PG, U32], C.byref(BITRATE), bitrate), 'output bitrate')
            _check(_call(incoming, 21, [PG, U32], C.byref(STRIDE), width * 4), 'input stride')
            self.stream = U32()
            _check(_call(self.writer, 3, [PTR, C.POINTER(U32)], media, C.byref(self.stream)), 'AddStream')
            _check(_call(self.writer, 4, [U32, PTR, PTR], self.stream, incoming, None), 'SetInputMediaType')
            self._disable_frame_rate_conversion()
            _check(_call(self.writer, 5, []), 'BeginWriting')
        except BaseException:
            self.close(False)
            raise
        finally:
            _release(media)
            _release(incoming)
            _release(attrs)

    def _disable_frame_rate_conversion(self):
        extended = PTR()
        _check(_call(self.writer, 0, [PG, C.POINTER(PTR)], C.byref(SINK_EX), C.byref(extended)), 'SinkWriterEx')
        try:
            for index in range(16):
                transform, attrs = PTR(), PTR()
                category = GUID('00000000-0000-0000-0000-000000000000')
                hr = _call(extended, 14, [U32, U32, PG, C.POINTER(PTR)], self.stream, index, C.byref(category), C.byref(transform))
                if hr < 0:
                    break
                try:
                    # IMFTransform::GetAttributes is slot 8. The attribute is
                    # honored by the video processor; codecs can ignore it.
                    if _call(transform, 8, [C.POINTER(PTR)], C.byref(attrs)) >= 0:
                        _check(_call(attrs, 21, [PG, U32], C.byref(NO_FRC), 1), 'disable frame-rate conversion')
                finally:
                    _release(attrs)
                    _release(transform)
        finally:
            _release(extended)

    def write(self, pixels, pts, duration):
        if len(pixels) != self.width * self.height * 4 or pts < 0 or duration <= 0:
            raise ValueError('Invalid pixels, PTS or sample duration')
        if self.last_pts is not None and pts <= self.last_pts:
            raise ValueError('Non-increasing encoder PTS')
        buffer, sample = PTR(), PTR()
        try:
            _check(self.mf.MFCreateMemoryBuffer(len(pixels), C.byref(buffer)), 'create encode buffer')
            data, maximum, length = PTR(), U32(), U32()
            _check(_call(buffer, 3, [C.POINTER(PTR), C.POINTER(U32), C.POINTER(U32)], C.byref(data), C.byref(maximum), C.byref(length)), 'encode buffer lock')
            try:
                C.memmove(data, pixels, len(pixels))
            finally:
                _check(_call(buffer, 4, []), 'encode buffer unlock')
            _check(_call(buffer, 6, [U32], len(pixels)), 'encode buffer length')
            _check(self.mf.MFCreateSample(C.byref(sample)), 'create encode sample')
            _check(_call(sample, 42, [PTR], buffer), 'add encode buffer')
            _check(_call(sample, 36, [I64], pts), 'encode PTS')
            _check(_call(sample, 38, [I64], duration), 'encode duration')
            _check(_call(self.writer, 6, [U32, PTR], self.stream, sample), 'WriteSample')
            self.last_pts = pts
        finally:
            _release(sample)
            _release(buffer)

    def close(self, finalize=True):
        if self.closed:
            return
        self.closed = True
        try:
            if finalize and self.writer:
                _check(_call(self.writer, 11, []), 'Finalize MP4')
        finally:
            _release(self.writer)
            self.writer = PTR()

    def __enter__(self):
        return self

    def __exit__(self, kind, *args):
        self.close(kind is None)
