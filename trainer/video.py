"""Local Media Foundation playback and bounded detection sampling."""

import importlib
import math
import os
import shutil
from collections import Counter
from contextlib import ExitStack, contextmanager
from pathlib import Path
from queue import Empty, Full, Queue
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import monotonic, sleep

from events import emit


def jpeg(path, frame, boxes=None, names=None, timestamp=0.0, anomaly=None):
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    scale = min(1, 960 / frame.shape[1])
    image = cv2.resize(frame, None, fx=scale, fy=scale) if scale < 1 else frame
    image = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    if boxes is not None:
        draw = ImageDraw.Draw(image)
        font_path = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts" / "msyh.ttc"
        font = ImageFont.truetype(str(font_path), 17) if font_path.exists() else ImageFont.load_default()
        draw.rectangle((6, 6, 135, 31), fill="#13283e")
        draw.text((12, 8), f"{timestamp:.3f} s", fill="white", font=font)
        if anomaly:
            score, threshold = anomaly
            draw.rectangle((6, 32, 310, 57), fill="#13283e")
            draw.text((12, 34), f"异常分数 {score:.4f} / 阈值 {threshold:.4f}", fill="white", font=font)
        for bounds, ident, score in boxes:
            x1, y1, x2, y2 = (round(value * scale) for value in bounds)
            label = f"{names.get(ident, str(ident))}  " + (f"{score:.4f}" if anomaly else f"{score:.1%}")
            draw.rectangle((x1, y1, x2, y2), outline="#55e9bf", width=3)
            x, y = max(x1, 0), max(y1 - 24, 0)
            draw.rectangle((x, y, x + int(draw.textlength(label, font=font)) + 10, y + 23), fill="#13283e")
            draw.text((x + 5, y + 1), label, fill="white", font=font)
    temp = path.with_suffix(".tmp")
    image.save(temp, "JPEG", quality=82)
    try:
        temp.replace(path)
    except PermissionError:
        # A reader may still hold the previous image on Windows.
        pass


def verify(args):
    from worker import configure, device, validate_size, weights_path

    validate_size(args)
    if not 0 < args.confidence <= 1 or not 0 < args.sample_fps <= 60:
        raise ValueError("置信度须大于 0 且不超过 1，验证帧率须大于 0 且不超过 60")
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds <= 0):
        raise ValueError("验证时长必须大于零")
    with TemporaryDirectory(prefix="ivad-video-") as temporary, open_video(args.video, Path(temporary)) as source:
        cap, first, info = source
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            jpeg(args.preview / "source.jpg", first)
        emit("video_probe", **info)
        if stopped(args):
            return
        configure(Path(temporary))
        if args.model != "anomaly":
            device(args)
        emit("stage", value="正在加载检测权重")
        try:
            args.weights = weights_path(args.weights, args.model)
            names, predict = importlib.import_module(args.model).predictor(args)
        except Exception as error:
            raise RuntimeError(f"权重加载失败：{error}") from error
        stream(args, cap, first, info["source_fps"], names, predict)


def probe(args):
    with TemporaryDirectory(prefix="ivad-probe-") as temporary, open_video(args.video, Path(temporary)) as source:
        _, first, info = source
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
            jpeg(args.preview / "source.jpg", first)
        emit("video_probe", **info)


@contextmanager
def open_video(path, temporary):
    import cv2

    if path is None:
        raise FileNotFoundError("视频文件无法访问：尚未选择文件")
    try:
        path = path.resolve(strict=True)
        with path.open("rb") as stream:
            header = stream.read(16)
            codec = mp4_video_codec(stream) if header[4:8] == b"ftyp" else None
    except OSError as error:
        raise OSError(f"视频文件无法访问：{path}（{error}）") from error
    if header[4:8] == b"ftyp":
        container = "QuickTime" if header[8:12] == b"qt  " else "ISO BMFF/MP4"
    else:
        container = "AVI" if header[:4] == b"RIFF" and header[8:12] == b"AVI " else "未知"
    attempts = []

    def open_path(source, route):
        for api, name in ((cv2.CAP_MSMF, "MSMF"), (cv2.CAP_OPENCV_MJPEG, "CV_MJPEG")):
            cap = cv2.VideoCapture()
            ready = False
            try:
                if not cap.open(str(source), api):
                    attempts.append({"route": route, "backend": name, "error": "VideoCapture.open returned false"})
                    continue
                ok, first = cap.read()
                if not ok or first is None:
                    attempts.append({"route": route, "backend": name, "error": "VideoCapture.read returned no first frame"})
                    continue
                fps = cap.get(cv2.CAP_PROP_FPS)
                if not math.isfinite(fps) or fps <= 0:
                    attempts.append({"route": route, "backend": name, "error": f"Invalid source FPS: {fps!r}"})
                    continue
                raw_fourcc = cap.get(cv2.CAP_PROP_FOURCC)
                fourcc = int(raw_fourcc) & 0xffffffff if math.isfinite(raw_fourcc) else 0
                tag = fourcc.to_bytes(4, "little")
                fallback_codec = tag.decode("ascii") if all(32 <= b <= 126 for b in tag) else None
                h, w = first.shape[:2]
                backend = cap.getBackendName()
                ready = True
                return cap, first, {"path": str(path), "route": route, "container": container,
                                    "codec_fourcc": codec or fallback_codec, "backend_fourcc": f"0x{fourcc:08x}",
                                    "width": w, "height": h, "source_fps": fps,
                                    "backend": backend, "attempts": attempts}
            except cv2.error as error:
                attempts.append({"route": route, "backend": name, "error": str(error)})
            finally:
                if not ready:
                    cap.release()
        return None

    with ExitStack() as stack:
        opened = open_path(path, "original")
        if opened is None and not str(path).isascii():
            # OpenCV's Windows capture wrappers can reject a valid UTF-16 path.
            # Keep the original bytes and use an ASCII alias in a private writable directory.
            roots = (temporary, Path(os.environ.get("LOCALAPPDATA", str(Path.home()))))
            for root in dict.fromkeys(roots):
                if not str(root).isascii():
                    continue
                try:
                    folder = Path(stack.enter_context(TemporaryDirectory(prefix="ivad-source-", dir=root)))
                    suffix = path.suffix if path.suffix.isascii() else ""
                    alias = folder / ("source" + suffix)
                    try:
                        os.link(path, alias)
                        route = "ascii-hardlink"
                    except OSError:
                        shutil.copyfile(path, alias)
                        route = "ascii-copy"
                except OSError as error:
                    attempts.append({"route": "ascii-alias", "backend": "filesystem", "error": str(error)})
                    continue
                opened = open_path(alias, route)
                break
        if opened is None:
            emit("video_open_attempts", path=str(path), attempts=attempts)
            raise ValueError("视频流无法解码：无法读取首帧或有效的源视频 FPS（Windows Media Foundation / OpenCV MJPEG）")
        stack.callback(opened[0].release)
        yield opened


def mp4_video_codec(stream):
    """Read the first video sample-entry tag without loading media payloads."""
    def children(start, end):
        while start + 8 <= end:
            stream.seek(start)
            raw = stream.read(8)
            size, kind = int.from_bytes(raw[:4], "big"), raw[4:]
            header = 8
            if size == 1:
                size, header = int.from_bytes(stream.read(8), "big"), 16
            elif size == 0:
                size = end - start
            if size < header or start + size > end:
                return
            yield kind, (start + header, start + size)
            start += size

    def find(kind, scope):
        return next((box for name, box in children(*scope) if name == kind), None)

    movie = find(b"moov", (0, stream.seek(0, os.SEEK_END)))
    if movie:
        for kind, track in children(*movie):
            media = find(b"mdia", track) if kind == b"trak" else None
            handler = find(b"hdlr", media) if media else None
            if not handler or handler[1] - handler[0] < 12:
                continue
            stream.seek(handler[0] + 8)
            if stream.read(4) != b"vide":
                continue
            for name in (b"minf", b"stbl", b"stsd"):
                media = find(name, media) if media else None
            if media and media[1] - media[0] >= 16:
                stream.seek(media[0] + 4)
                if int.from_bytes(stream.read(4), "big"):
                    stream.read(4)
                    return stream.read(4).decode("ascii", errors="replace")
    return None


def stopped(args):
    return args.stop_file is not None and args.stop_file.exists()


def stream(args, cap, first, fps, names, predict):
    import cv2

    pending = Queue(maxsize=1)
    finished = Event()
    counters = {"decoded": 1, "offered": 1, "dropped": 0, "timestamp": 0.0}
    failure = []
    begun = monotonic()
    period = 1 / args.sample_fps

    def play():
        next_sample, next_preview = period, 1 / 24
        try:
            while not finished.is_set() and not stopped(args):
                nominal = counters["decoded"] / fps
                if args.seconds is not None and nominal >= args.seconds:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                counters["decoded"] += 1
                raw = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                timestamp = raw if math.isfinite(raw) and raw > counters["timestamp"] else nominal
                if args.seconds is not None and timestamp >= args.seconds:
                    break
                while not stopped(args) and not finished.is_set() and begun + timestamp > monotonic():
                    finished.wait(min(.05, max(0, begun + timestamp - monotonic())))
                if finished.is_set() or stopped(args):
                    break
                counters["timestamp"] = timestamp
                if timestamp + 0.000001 >= next_sample:
                    counters["offered"] += 1
                    next_sample = timestamp + period
                    try:
                        pending.put_nowait((timestamp, frame))
                    except Full:
                        try:
                            pending.get_nowait()
                            counters["dropped"] += 1
                        except Empty:
                            pass
                        pending.put_nowait((timestamp, frame))
                if args.preview and timestamp + 0.000001 >= next_preview:
                    jpeg(args.preview / "source.jpg", frame)
                    next_preview = timestamp + 1 / 24
        except Exception as error:
            failure.append(error)
        finally:
            finished.set()

    reader = Thread(target=play, name="video-playback", daemon=True)
    elapsed = processed = detections = 0
    last_inference_elapsed = 0.0
    class_counts = Counter()
    last_timestamp = -1.0
    next_start = 0.0
    anomaly = None

    def update(kind):
        rate = (processed - 1) / max(last_inference_elapsed, 0.001) if processed >= 2 else None
        summary = {"classes": {names.get(ident, str(ident)): count for ident, count in class_counts.items()}}
        extra = {"anomaly_score": anomaly[0], "anomaly_threshold": anomaly[1]} if anomaly else {}
        emit(kind, source_fps=fps, limit=args.sample_fps, actual_fps=rate,
             processed=processed, detections=detections, timestamp=last_timestamp,
             decoded=counters["decoded"], dropped=counters["dropped"], offered=counters["offered"],
             source_seconds=counters["timestamp"], wall_seconds=elapsed,
             **(summary if kind == "video_result" else {}), **extra)

    def infer(timestamp, frame):
        nonlocal anomaly, processed, detections, last_timestamp
        if args.model == "anomaly":
            boxes, view, score, threshold = predict(frame)
            anomaly = (score, threshold)
        else:
            boxes, view = predict(frame), frame
        processed += 1
        detections += len(boxes)
        class_counts.update(ident for _, ident, _ in boxes)
        last_timestamp = timestamp
        if args.preview:
            jpeg(args.preview / "detected.jpg", view, boxes, names, timestamp, anomaly)

    emit("stage", value="正在验证视频")
    if stopped(args):
        return
    # Warm up on the real frame at t=0 before starting the playback clock.
    infer(0.0, first)
    begun = monotonic()
    next_start = begun + period
    update("video")
    reader.start()
    try:
        while not stopped(args) and (not finished.is_set() or not pending.empty()):
            while not stopped(args) and next_start > monotonic():
                sleep(min(.05, max(0, next_start - monotonic())))
            if stopped(args):
                break
            try:
                timestamp, frame = pending.get(timeout=0.10)
            except Empty:
                continue
            started = monotonic()
            next_start = started + period
            infer(timestamp, frame)
            elapsed = monotonic() - begun
            last_inference_elapsed = elapsed
            update("video")
    finally:
        finished.set()
        reader.join()
    if failure:
        raise failure[0]
    if not processed:
        raise ValueError("视频没有可解码并验证的帧")
    elapsed = monotonic() - begun
    update("video_result")
