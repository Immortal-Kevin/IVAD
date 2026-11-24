"""Read-only, frame-accurate clips for the manual scraper angle reviewer."""

import hashlib
import json
import math
from pathlib import Path
from tempfile import TemporaryDirectory

from events import emit
from video import open_video


def source_profile(path, digest, size):
    import cv2
    import numpy as np

    if path is None:
        return {}
    source = json.loads(path.read_text(encoding="utf-8-sig"))["sources"].get(digest)
    if not source or source["size"] != size:
        raise ValueError("当前原片不匹配测角配置的 SHA-256 或画面尺寸")
    result = {"reference": source.get("reference", [])}
    pairs = source.get("calibration")
    if pairs:
        pixels, plane = (np.asarray([p[key] for p in pairs], dtype=np.float64) for key in ("pixel", "plane"))
        if (len(pairs) < 4 or any(p.shape != (len(pairs), 2) or not np.isfinite(p).all()
                                  for p in (pixels, plane))):
            raise ValueError("透视校正需要至少四对有效的像素点和同单位平面坐标")
        matrix, _ = cv2.findHomography(pixels, plane)
        if matrix is None or not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix) != 3:
            raise ValueError("透视校正失败：平面控制点退化")
        reprojection = cv2.perspectiveTransform(plane[None], np.linalg.inv(matrix))[0]
        if not np.isfinite(reprojection).all() or np.max(np.linalg.norm(reprojection - pixels, axis=1)) > 3:
            raise ValueError("透视校正失败：控制点反投影误差超过 3 像素")
        result.update(pixel_to_plane=matrix.ravel().tolist(), plane_to_pixel=np.linalg.inv(matrix).ravel().tolist())
    return result


def load_clip(args):
    import cv2

    if args.preview is None or not math.isfinite(args.at) or args.at < 0:
        raise ValueError("请选择测角预览目录和有效的原片时间")
    args.preview.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix="ivad-angle-") as temporary, open_video(args.video, Path(temporary)) as source:
        cap, first, info = source
        fps = info["source_fps"]
        total = round(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        if total < 1:
            raise ValueError("原片没有可用的逐帧索引")
        width, height = info["width"], info["height"]
        calibration = {}
        if args.angle_profile:
            with Path(info["path"]).open("rb") as stream:
                digest = hashlib.file_digest(stream, "sha256").hexdigest()
            calibration = source_profile(args.angle_profile, digest, [width, height])
        start = min(round(args.at * fps), total - 1)
        if start and not cap.set(cv2.CAP_PROP_POS_FRAMES, start):
            raise RuntimeError("解码器无法定位到指定帧")
        times = []
        for i in range(start, min(total, start + math.ceil(fps * 3))):
            ok, frame = (True, first) if i == 0 else cap.read()
            if not ok:
                break
            pos = cap.get(cv2.CAP_PROP_POS_FRAMES)
            if i and math.isfinite(pos) and abs(pos - (i + 1)) > .5:
                raise RuntimeError("解码器返回的原片帧号与请求不符")
            raw = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000
            nominal = i / fps
            # Some MSMF drivers report the next frame time or zero after seeking.
            timestamp = raw if i and math.isfinite(raw) and abs(raw - nominal) < .5 / fps else nominal
            ok, encoded = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 96])
            if not ok:
                raise RuntimeError("无法生成逐帧回放预览")
            (args.preview / f"{i}.jpg").write_bytes(encoded.tobytes())
            times.append(timestamp)
        if not times:
            raise RuntimeError("未解码到测角帧")
        emit("angle_clip", start=start, total=total, fps=fps, times=times, width=width, height=height, **calibration)
