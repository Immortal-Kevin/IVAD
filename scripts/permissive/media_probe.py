"""Isolated read-only MF validation; raw evidence is local and never committed."""
import ctypes as C
import hashlib
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ivad_app.video.windows_mf import SourceReader

def loaded_modules():
    kernel = C.WinDLL('kernel32', winmode=0x800)
    kernel.GetCurrentProcess.restype = C.c_void_p
    psapi = C.WinDLL('psapi', winmode=0x800)
    psapi.EnumProcessModules.argtypes = [C.c_void_p, C.c_void_p, C.c_uint32, C.POINTER(C.c_uint32)]
    psapi.GetModuleFileNameExW.argtypes = [C.c_void_p, C.c_void_p, C.c_wchar_p, C.c_uint32]
    process = kernel.GetCurrentProcess()
    handles, needed = (C.c_void_p * 4096)(), C.c_uint32()
    if not psapi.EnumProcessModules(process, handles, C.sizeof(handles), C.byref(needed)):
        raise C.WinError()
    paths = []
    for handle in handles[:needed.value // C.sizeof(C.c_void_p)]:
        name = C.create_unicode_buffer(32768)
        psapi.GetModuleFileNameExW(process, handle, name, len(name))
        paths.append(name.value)
    return sorted(paths)

def main(path, output):
    start = time.perf_counter()
    source, target = Path(path), Path(output)
    if target.exists():
        raise RuntimeError('Evidence exists')
    with source.open('rb') as f:
        sha = hashlib.file_digest(f, 'sha256').hexdigest()
    result = {'file': str(source), 'sha256': sha, 'protocol': 'windows-mf-v1', 'status': 'FAIL'}
    try:
        timestamps = []
        with SourceReader(source) as reader:
            result.update(container=reader.container, codec=reader.codec, size=[reader.width, reader.height], frame_rate=reader.frame_rate, duration_ticks=reader.duration_ticks, rotation=reader.rotation)
            for frame in reader.frames():
                timestamps.append(frame.pts)
                if len(timestamps) == 1:
                    result['first_pixel_sha256'] = hashlib.sha256(frame.pixels).hexdigest()
            result['loaded_modules'] = loaded_modules()
        if not timestamps:
            raise ValueError('No decoded samples')
        if any(b <= a for a, b in zip(timestamps, timestamps[1:])):
            raise ValueError('Non-monotonic presentation timestamps')
        forbidden = ('avcodec', 'avformat', 'avutil', 'swscale', 'swresample', 'ffmpeg', 'pyside', 'qt6')
        bad = [p for p in result['loaded_modules'] if any(v in Path(p).name.lower() for v in forbidden)]
        if bad:
            raise ValueError('Forbidden runtime modules: ' + repr(bad))
        result.update(status='PASS', frame_count=len(timestamps), timestamps=timestamps, time_base='1/10000000', clock_domain='Media Foundation presentation clock; not original container raw ticks', imported_modules=sorted(sys.modules))
    except Exception as exc:
        result['error'] = str(exc)
    result['seconds'] = time.perf_counter() - start
    target.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')
    print(json.dumps({k: v for k, v in result.items() if k not in ('timestamps', 'loaded_modules', 'imported_modules')}, ensure_ascii=False))
    return 0 if result['status'] == 'PASS' else 1

if __name__ == '__main__':
    raise SystemExit(main(*sys.argv[1:]))
