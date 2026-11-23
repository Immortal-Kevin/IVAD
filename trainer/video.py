"""Local Media Foundation playback and bounded detection sampling."""

import importlib
import math
import os
from collections import Counter
from pathlib import Path
from queue import Empty, Full, Queue
from tempfile import TemporaryDirectory
from threading import Event, Thread
from time import monotonic, sleep

from events import emit


def jpeg(path, frame, boxes=None, names=None, timestamp=0.0):
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
        for bounds, ident, score in boxes:
            x1, y1, x2, y2 = (round(value * scale) for value in bounds)
            label = f"{names.get(ident, str(ident))}  {score:.1%}"
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
    import cv2
    from worker import configure, device, validate_size, weights_path

    validate_size(args)
    if not 0 < args.confidence <= 1 or not 0 < args.sample_fps <= 60:
        raise ValueError("置信度须大于 0 且不超过 1，验证帧率须大于 0 且不超过 60")
    if args.seconds is not None and (not math.isfinite(args.seconds) or args.seconds <= 0):
        raise ValueError("验证时长必须大于零")
    if args.video is None or not args.video.is_file():
        raise FileNotFoundError("请选择存在的本地测试视频")
    args.weights = weights_path(args.weights, args.model)

    with TemporaryDirectory(prefix="ivad-video-") as temporary:
        configure(Path(temporary))
        device(args)
        emit("stage", value="正在加载检测权重")
        names, predict = importlib.import_module(args.model).predictor(args)
        if args.preview:
            args.preview.mkdir(parents=True, exist_ok=True)
        cap = cv2.VideoCapture(str(args.video.resolve()), cv2.CAP_MSMF)
        if not cap.isOpened():
            cap.release()
            cap = cv2.VideoCapture(str(args.video.resolve()), cv2.CAP_OPENCV_MJPEG)
        if not cap.isOpened():
            raise ValueError("Windows 无法打开此视频，请检查文件或使用受支持的 MP4 / AVI 编码")
        try:
            stream(args, cap, names, predict)
        finally:
            cap.release()


def stream(args, cap, names, predict):
    import cv2

    fps = float(cap.get(cv2.CAP_PROP_FPS))
    if not math.isfinite(fps) or fps <= 0:
        raise ValueError("无法读取源视频 FPS")
    pending = Queue(maxsize=1)
    finished = Event()
    counters = {"decoded": 0, "offered": 0, "dropped": 0, "timestamp": 0.0}
    failure = []
    begun = monotonic()
    period = 1 / args.sample_fps

    def play():
        next_sample = next_preview = 0.0
        try:
            while not finished.is_set():
                nominal = counters["decoded"] / fps
                if args.seconds is not None and nominal >= args.seconds:
                    break
                ok, frame = cap.read()
                if not ok:
                    break
                raw = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
                timestamp = raw if math.isfinite(raw) and raw > counters["timestamp"] else nominal
                if args.seconds is not None and timestamp >= args.seconds:
                    break
                if finished.wait(max(0, begun + timestamp - monotonic())):
                    break
                counters["decoded"] += 1
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
    first_start = None
    class_counts = Counter()
    last_timestamp = -1.0
    next_start = 0.0

    def update(kind):
        rate = (processed - 1) / max(elapsed - first_start, 0.001) if processed >= 2 else None
        summary = {"classes": {names.get(ident, str(ident)): count for ident, count in class_counts.items()}}
        emit(kind, source_fps=fps, limit=args.sample_fps, actual_fps=rate,
             processed=processed, detections=detections, timestamp=last_timestamp,
             decoded=counters["decoded"], dropped=counters["dropped"], offered=counters["offered"],
             source_seconds=counters["timestamp"], wall_seconds=elapsed,
             **(summary if kind == "video_result" else {}))

    emit("stage", value="正在验证视频")
    update("video")
    reader.start()
    try:
        while not finished.is_set() or not pending.empty():
            sleep(max(0, next_start - monotonic()))
            try:
                timestamp, frame = pending.get(timeout=0.10)
            except Empty:
                continue
            started = monotonic()
            if first_start is None:
                first_start = started - begun
            next_start = started + period
            boxes = predict(frame)
            processed += 1
            detections += len(boxes)
            class_counts.update(ident for _, ident, _ in boxes)
            last_timestamp = timestamp
            if args.preview:
                jpeg(args.preview / "detected.jpg", frame, boxes, names, timestamp)
            elapsed = monotonic() - begun
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
