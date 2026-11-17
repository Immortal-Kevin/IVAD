"""PyAV lives only in a disposable process, never the Qt GUI process."""
import argparse
import json
from pathlib import Path
import sys
import traceback
from demo_rf.diagnostics import install, record, exception

def emit(event, **data):
    print(json.dumps(dict(event=event, **data), ensure_ascii=False), flush=True)

def main():
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'): stream.reconfigure(encoding='utf8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--video', required=True)
    parser.add_argument('--interval', type=float, required=True)
    parser.add_argument('--session', required=True)
    parser.add_argument('--log-dir', required=True)
    args = parser.parse_args()
    log = install(args.log_dir, 'decode')
    decoded = 0
    try:
        import av
        record(log, 'decode', 'opening', library_versions=av.library_versions)
        # PyAV 15.1 global `options` is also copied into stream dictionaries.
        # Dynamically discovered MPEG-PS streams make that native cleanup unsafe.
        # Container-only options preserve the file whitelist without that path.
        with av.open(str(Path(args.video).resolve(strict=True)),
                     container_options={'protocol_whitelist': 'file'}) as container:
            stream = container.streams.video[0]
            record(log, 'decode', 'opened', format=container.format.name,
                   width=stream.width, height=stream.height)
            duration = float(stream.duration * stream.time_base) if stream.duration is not None else (
                float(container.duration / av.time_base) if container.duration is not None else 0.)
            origin = float(stream.start_time * stream.time_base) if stream.start_time is not None else None
            next_sample = last_pts = None
            for index, frame in enumerate(container.decode(stream)):
                if frame.pts is None or frame.time_base is None:
                    raise ValueError('录像缺少真实PTS，不能按FPS补造检测时间。')
                seconds = float(frame.pts * frame.time_base)
                if origin is None: origin = seconds
                if last_pts is not None and seconds < last_pts: raise ValueError('录像PTS倒退，已停止。')
                last_pts = seconds
                decoded = index + 1
                elapsed = max(0., seconds - origin)
                if index % 25 == 0: emit('progress', decoded=decoded, seconds=elapsed, duration=duration)
                if next_sample is None: next_sample = seconds
                if seconds + 1e-9 < next_sample: continue
                next_sample = seconds + args.interval
                destination = Path(args.session) / 'input.png'
                frame.to_image().save(destination)
                emit('sample', image=str(destination), frame_index=index, pts=int(frame.pts),
                     time_base=[frame.time_base.numerator, frame.time_base.denominator],
                     time_seconds=seconds, elapsed_seconds=elapsed, duration=duration, decoded=decoded)
                if sys.stdin.readline().strip() != 'ack':
                    record(log, 'decode', 'stopped', decoded=decoded)
                    return 0
            emit('complete', decoded=decoded)
        record(log, 'decode', 'exit', returncode=0, decoded=decoded)
        return 0
    except Exception as exc:
        exception(log, 'decode', exc)
        traceback.print_exc()
        emit('error', message='视频解码失败：' + str(exc))
        return 1

if __name__ == '__main__': raise SystemExit(main())
