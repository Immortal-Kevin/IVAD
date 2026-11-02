"""Windows Media Foundation reader; stdlib only, no FFmpeg/Qt fallback.

Source Reader timestamps are actual presentation times in 100 ns units.
They are NOT original container ticks: retain the explicit clock domain.
Use in an isolated worker; COM instances belong to their creating thread.
"""
from __future__ import annotations

import ctypes as C
import os
import threading
import uuid
from dataclasses import dataclass
from pathlib import Path


class MediaFoundationError(RuntimeError):
    def __init__(self, operation, hr):
        self.hresult = hr & 0xFFFFFFFF
        super().__init__(f'{operation}: HRESULT 0x{self.hresult:08X}')


class GUID(C.Structure):
    _fields_ = [('bytes', C.c_ubyte * 16)]

    def __init__(self, value):
        super().__init__()
        self.bytes[:] = uuid.UUID(value).bytes_le


def _check(hr, operation):
    if hr < 0:
        raise MediaFoundationError(operation, hr)


def _call(pointer, index, types, *args):
    table = C.cast(pointer, C.POINTER(C.POINTER(C.c_void_p))).contents
    method = C.WINFUNCTYPE(C.c_int32, C.c_void_p, *types)(table[index])
    return method(pointer, *args)


def _release(pointer):
    if pointer:
        _call(pointer, 2, [])


U32 = C.c_uint32
U64 = C.c_uint64
I64 = C.c_int64
PTR = C.c_void_p
PG = C.POINTER(GUID)
VIDEO = 0xFFFFFFFC
MAJOR = GUID('48eba18e-f8c9-4687-bf11-0a74c9f96a8f')
SUBTYPE = GUID('f7e34c9a-42e8-4714-b74b-cb29d72c35e5')
VIDEO_TYPE = GUID('73646976-0000-0010-8000-00aa00389b71')
RGB32 = GUID('00000016-0000-0010-8000-00aa00389b71')
SIZE = GUID('1652c33d-d6b2-4012-b834-72030849a37d')
STRIDE = GUID('644b4e48-1e02-4516-b0eb-c01ca9d49ac6')
RATE = GUID('c459a2e8-3d2c-4e44-b132-fee5156c7bb0')
PROCESSING = GUID('fb394f3d-ccf1-42ee-bbb3-f9b845d5681d')
DURATION = GUID('6c990d33-bb8e-477a-8598-0d5d96fcd88a')
ROTATION = GUID('c380465d-2271-428c-9b83-ecea3b4a85c1')
APERTURE = GUID('d7388766-18fe-48c6-a177-ee894867c8c4')


@dataclass(frozen=True)
class VideoFrame:
    pts: int
    width: int
    height: int
    stride: int
    pixels: bytes
    time_base_num: int = 1
    time_base_den: int = 10_000_000
    clock_domain: str = 'media-foundation-presentation-100ns'

    @property
    def seconds(self):
        return self.pts / self.time_base_den


def sniff_container(path):
    """Evidence from bytes, never choose decoder solely by file extension."""
    with Path(path).open('rb') as f:
        header = f.read(4096)
    if b'\x00\x00\x01\xba' in header and b'\x00\x00\x01\xe0' in header:
        return 'mpeg-ps'
    if header.startswith(b'RIFF') and header[8:12] == b'AVI ':
        return 'avi'
    if header.startswith(b'\x1a\x45\xdf\xa3'):
        return 'matroska-ebml'
    if len(header) >= 12 and header[4:8] == b'ftyp':
        return 'iso-bmff'
    return 'unrecognized'


class SourceReader:
    """Synchronous native reader; cancellation checked between ReadSample calls.

    Host process must enforce timeout/cancel if a system decoder stalls.
    No global COM registration or codec installation is performed.
    """
    def __init__(self, path):
        if os.name != 'nt':
            raise OSError('Windows Media Foundation requires Windows')
        self.thread = threading.get_ident()
        self.reader = PTR()
        self.started = False
        self.com = False
        self.path = Path(path).resolve(strict=True)
        if not self.path.is_file():
            raise ValueError('A local video file is required')
        self.container = sniff_container(self.path)
        self.ole = C.WinDLL('ole32', winmode=0x800)
        self.mf = C.WinDLL('mfplat', winmode=0x800)
        self.rw = C.WinDLL('mfreadwrite', winmode=0x800)
        self.ole.CoInitializeEx.argtypes = [PTR, U32]
        self.mf.MFStartup.argtypes = [U32, U32]
        self.mf.MFCreateAttributes.argtypes = [C.POINTER(PTR), U32]
        self.mf.MFCreateMediaType.argtypes = [C.POINTER(PTR)]
        self.rw.MFCreateSourceReaderFromURL.argtypes = [C.c_wchar_p, PTR, C.POINTER(PTR)]
        attrs, media = PTR(), PTR()
        try:
            _check(self.ole.CoInitializeEx(None, 0), 'CoInitializeEx(MTA)')
            self.com = True
            _check(self.mf.MFStartup(0x20070, 0), 'MFStartup')
            self.started = True
            _check(self.mf.MFCreateAttributes(C.byref(attrs), 1), 'MFCreateAttributes')
            _check(_call(attrs, 21, [PG, U32], C.byref(PROCESSING), 1), 'video processing')
            _check(self.rw.MFCreateSourceReaderFromURL(str(self.path), attrs, C.byref(self.reader)), 'open ' + self.container)
            _check(_call(self.reader, 4, [U32, C.c_int], 0xFFFFFFFE, 0), 'disable streams')
            _check(_call(self.reader, 4, [U32, C.c_int], VIDEO, 1), 'enable video')
            native = PTR()
            _check(_call(self.reader, 5, [U32, U32, C.POINTER(PTR)], VIDEO, 0, C.byref(native)), 'native video type')
            try:
                subtype = GUID('00000000-0000-0000-0000-000000000000')
                _check(_call(native, 10, [PG, PG], C.byref(SUBTYPE), C.byref(subtype)), 'native codec subtype')
                raw = bytes(subtype.bytes)
                self.codec = raw[:4].decode('ascii') if all(32 <= v < 127 for v in raw[:4]) else str(uuid.UUID(bytes_le=raw))
            finally:
                _release(native)
            _check(self.mf.MFCreateMediaType(C.byref(media)), 'MFCreateMediaType')
            for key, value in [(MAJOR, VIDEO_TYPE), (SUBTYPE, RGB32)]:
                _check(_call(media, 24, [PG, PG], C.byref(key), C.byref(value)), 'SetGUID')
            _check(_call(self.reader, 7, [U32, PTR, PTR], VIDEO, None, media), 'RGB32 output')
            self._format()
            value = (C.c_ubyte * 24)()
            _check(_call(self.reader, 12, [U32, PG, PTR], 0xFFFFFFFF, C.byref(DURATION), value), 'presentation duration')
            try:
                if int.from_bytes(bytes(value[:2]), 'little') != 21:
                    raise ValueError('Duration is not VT_UI8')
                self.duration_ticks = int.from_bytes(bytes(value[8:16]), 'little')
            finally:
                self.ole.PropVariantClear(C.byref(value))
        except BaseException:
            self.close()
            raise
        finally:
            _release(media)
            _release(attrs)

    def _format(self):
        media = PTR()
        _check(_call(self.reader, 6, [U32, C.POINTER(PTR)], VIDEO, C.byref(media)), 'current type')
        try:
            size, stride, rate = U64(), U32(), U64()
            _check(_call(media, 8, [PG, C.POINTER(U64)], C.byref(SIZE), C.byref(size)), 'frame size')
            self.width, self.height = size.value >> 32, size.value & 0xFFFFFFFF
            self.coded_height = self.height
            self.crop_x = self.crop_y = 0
            area, actual = (C.c_ubyte * 16)(), U32()
            hr = _call(media, 15, [PG, PTR, U32, C.POINTER(U32)], C.byref(APERTURE), area, 16, C.byref(actual))
            if hr >= 0 and actual.value == 16:
                raw = bytes(area)
                if raw[0:2] != b'\x00\x00' or raw[4:6] != b'\x00\x00':
                    raise ValueError('Fractional display aperture is unsupported')
                x, y = int.from_bytes(raw[2:4], 'little', signed=True), int.from_bytes(raw[6:8], 'little', signed=True)
                width, height = int.from_bytes(raw[8:12], 'little', signed=True), int.from_bytes(raw[12:16], 'little', signed=True)
                if width > 0 and height > 0:
                    if x < 0 or y < 0 or x + width > self.width or y + height > self.height:
                        raise ValueError('Invalid display aperture')
                    self.width, self.height, self.crop_x, self.crop_y = width, height, x, y
            if not 0 < self.width <= 16384 or not 0 < self.height <= 16384:
                raise ValueError('Invalid or unsupported decoded dimensions')
            hr = _call(media, 7, [PG, C.POINTER(U32)], C.byref(STRIDE), C.byref(stride))
            self.stride = C.c_int32(stride.value).value if hr >= 0 else self.width * 4
            hr = _call(media, 8, [PG, C.POINTER(U64)], C.byref(RATE), C.byref(rate))
            self.frame_rate = (rate.value >> 32, rate.value & 0xFFFFFFFF) if hr >= 0 else None
            rotation = U32()
            hr = _call(media, 7, [PG, C.POINTER(U32)], C.byref(ROTATION), C.byref(rotation))
            self.rotation = rotation.value if hr >= 0 else 0
            if self.rotation not in (0, 90, 180, 270):
                raise ValueError('Unsupported rotation')
        finally:
            _release(media)

    def frames(self, cancelled=lambda: False):
        if threading.get_ident() != self.thread or not self.reader:
            raise RuntimeError('Reader must be open on its owning thread')
        while not cancelled():
            stream, flags, timestamp, sample = U32(), U32(), I64(), PTR()
            _check(_call(self.reader, 9, [U32, U32, C.POINTER(U32), C.POINTER(U32), C.POINTER(I64), C.POINTER(PTR)], VIDEO, 0, C.byref(stream), C.byref(flags), C.byref(timestamp), C.byref(sample)), 'ReadSample')
            try:
                if flags.value & 1:
                    raise RuntimeError('Source reader reports decoding error')
                if flags.value & 0x20:
                    self._format()
                if sample:
                    # Sample PTS is authoritative; fail rather than invent missing time.
                    pts, buffer = I64(), PTR()
                    _check(_call(sample, 35, [C.POINTER(I64)], C.byref(pts)), 'sample presentation time')
                    _check(_call(sample, 41, [C.POINTER(PTR)], C.byref(buffer)), 'contiguous buffer')
                    try:
                        data, maximum, length = PTR(), U32(), U32()
                        _check(_call(buffer, 3, [C.POINTER(PTR), C.POINTER(U32), C.POINTER(U32)], C.byref(data), C.byref(maximum), C.byref(length)), 'buffer lock')
                        try:
                            if length.value < abs(self.stride) * self.coded_height:
                                raise ValueError('Truncated decoded RGB32 buffer')
                            raw = C.string_at(data, length.value)
                            rows = []
                            for y in range(self.crop_y, self.crop_y + self.height):
                                row = y if self.stride > 0 else self.coded_height - 1 - y
                                offset = row * abs(self.stride) + self.crop_x * 4
                                rows.append(raw[offset:offset + self.width * 4])
                            pixels = b''.join(rows)
                        finally:
                            _check(_call(buffer, 4, []), 'buffer unlock')
                        yield VideoFrame(pts.value, self.width, self.height, self.width * 4, pixels)
                    finally:
                        _release(buffer)
                if flags.value & 2:
                    break
            finally:
                _release(sample)

    def close(self):
        if threading.get_ident() != self.thread:
            raise RuntimeError('Close on owning thread')
        _release(self.reader)
        self.reader = PTR()
        if self.started:
            self.mf.MFShutdown()
            self.started = False
        if self.com:
            self.ole.CoUninitialize()
            self.com = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
