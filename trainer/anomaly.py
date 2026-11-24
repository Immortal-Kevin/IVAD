"""Normal-only spatial appearance modelling and held-out IDS playback."""

from collections import defaultdict
import json
from pathlib import Path
from zipfile import ZipFile

import cv2
import numpy as np

from events import emit
from ids import read_manifest


def roi_values(values):
    x1, y1, x2, y2 = map(float, values)
    if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
        raise ValueError("ROI 使用 0 到 1 的左、上、右、下坐标，右下角必须大于左上角")
    return x1, y1, x2, y2


def roi_bounds(image, roi):
    h, w = image.shape[:2]
    x1, y1, x2, y2 = roi
    left, top, right, bottom = int(x1 * w), int(y1 * h), round(x2 * w), round(y2 * h)
    if right - left < 8 or bottom - top < 8:
        raise ValueError("指定 ROI 小于 8×8 像素")
    return left, top, right, bottom


def features(image, roi):
    x1, y1, x2, y2 = roi_bounds(image, roi)
    crop = cv2.resize(image[y1:y2, x1:x2], (96, 64), interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    mean = cv2.GaussianBlur(gray, (0, 0), 3)
    variance = cv2.GaussianBlur(gray * gray, (0, 0), 3) - mean * mean
    contrast = np.clip((gray - mean) / np.sqrt(np.maximum(variance, .0025)), -3, 3)
    gx = cv2.Sobel(contrast, cv2.CV_32F, 1, 0) / 8
    gy = cv2.Sobel(contrast, cv2.CV_32F, 0, 1) / 8
    return float(gray.mean()), np.stack((contrast, gx, gy), axis=-1)


def score_map(image, roi, centers, spreads):
    _, feature = features(image, roi)
    errors = np.mean(np.abs((feature - centers) / spreads), axis=-1)
    scores = np.quantile(errors, .99, axis=(1, 2))
    best = np.argmin(scores)
    return float(scores[best]), errors[best]


def read_image(archive, asset):
    image = cv2.imdecode(np.frombuffer(archive.read(asset), np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError(f"无法解码 IDS 图像 {asset}")
    return image


def fit(args, run, splits, manifest):
    train, valid = splits["train"], splits["valid"]
    if not train or not valid or any(f.state != "normal" for f in train + valid):
        raise ValueError("正常模式需要互相独立且已确认正常的 Train 和 Val 片段")
    roi = roi_values(args.roi)
    with ZipFile(args.ids) as archive:
        _, fingerprint = read_manifest(archive)
        if fingerprint != manifest["document_sha256"]:
            raise ValueError("IDS 在校验后发生变化")
        emit("stage", value="正在拟合已确认正常的 Train 片段")
        samples = [features(read_image(archive, frame.asset), roi) for frame in train]
        light, data = zip(*samples)
        data = np.stack(data)
        bins = np.array_split(np.argsort(light, kind="stable"), max(1, min(3, len(data) // 24)))
        centers = np.stack([data[indices].mean(axis=0) for indices in bins])
        spreads = np.maximum(np.stack([data[indices].std(axis=0) for indices in bins]), .12)
        del data, samples
        emit("stage", value="正在用独立正常 Val 片段校准阈值")
        calibration = [score_map(read_image(archive, frame.asset), roi, centers, spreads)[0] for frame in valid]
        threshold = float(np.quantile(calibration, .99, method="higher"))
        model = run / "normal-model.npz"
        np.savez_compressed(model, centers=centers, spreads=spreads, threshold=threshold, roi=roi)
        emit("stage", value="阈值已固定，正在回放独立 Test 片段")
        report = replay(archive, manifest, roi, centers, spreads, threshold)
    result = {"mode": "anomaly", "checkpoint": model.name, "threshold": threshold,
              "calibration_frames": len(calibration), "training_frames": len(train), "roi": roi,
              "split_manifest": "split-manifest.json", "test": report}
    (run / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"固定阈值 {threshold:.6g}", flush=True)
    for video, row in report.items():
        print(f"[{manifest['selected_videos'][video]}] "
              f"事件命中 {row['events_hit']}/{row['events_total']} · 正常片段误报 {row['false_alarms']} 次 · "
              f"有效回放 {row['effective_seconds']} 秒", flush=True)
    if not any(r["events_total"] for r in report.values()):
        print("拉偏未验证", flush=True)
    emit("checkpoint", path=str(model), model="anomaly", metrics={})


def replay(archive, manifest, roi, centers, spreads, threshold):
    groups = defaultdict(list)
    for row in manifest["planned"]["test"]:
        groups[row["group"]].append(row)
    report = {}
    for video, stats in manifest["videos"].items():
        cadence = stats["cadence_s"]
        normal_scores, abnormal_scores = [], []
        events, hit = set(), set()
        false_alarms = normal_flagged = normal_clips = 0
        seconds = normal_seconds = 0.0
        for rows in (items for items in groups.values() if items[0]["video"] == video):
            event = any(r["state"] == "abnormal" for r in rows)
            normal_clips += not event
            previous = False
            prev_time = None
            for row in rows:
                timestamp = row["time_s"]
                score, _ = score_map(read_image(archive, row["asset"]), roi, centers, spreads)
                flagged = score > threshold
                duration = (cadence if prev_time is None else min(cadence, timestamp - prev_time)) if cadence else 0
                if cadence and prev_time is not None and timestamp - prev_time > 1.5 * cadence:
                    previous = False
                seconds += duration
                if row["state"] == "abnormal":
                    abnormal_scores.append(score)
                    events.update(row["event_keys"])
                    if flagged:
                        hit.update(row["event_keys"])
                elif not event:
                    normal_scores.append(score)
                    normal_seconds += duration
                    false_alarms += flagged and not previous
                    normal_flagged += flagged
                    previous = flagged
                prev_time = timestamp
        report[video] = {"events_hit": len(hit), "events_total": len(events), "false_alarms": false_alarms,
                         "normal_clips": normal_clips, "normal_frames": len(normal_scores),
                         "normal_frames_flagged": normal_flagged, "abnormal_frames": len(abnormal_scores),
                         "effective_seconds": round(seconds, 3) if cadence else None,
                         "normal_seconds": round(normal_seconds, 3) if cadence else None,
                         "median_normal_score": float(np.median(normal_scores)) if normal_scores else None,
                         "median_abnormal_score": float(np.median(abnormal_scores)) if abnormal_scores else None}
    return report


def predictor(args):
    with np.load(args.weights, allow_pickle=False) as weights:
        centers, spreads = weights["centers"], weights["spreads"]
        roi, threshold = roi_values(weights["roi"]), float(weights["threshold"])

    def predict(image):
        score, heat = score_map(image, roi, centers, spreads)
        x1, y1, x2, y2 = roi_bounds(image, roi)
        view = image.copy()
        scaled = np.uint8(np.clip(heat / max(threshold, 1e-6) * 160, 0, 255))
        colors = cv2.applyColorMap(cv2.resize(scaled, (x2 - x1, y2 - y1)), cv2.COLORMAP_TURBO)
        crop = view[y1:y2, x1:x2]
        cv2.addWeighted(crop, .58, colors, .42, 0, dst=crop)
        boxes = []
        if score > threshold:
            mask = np.uint8(heat > threshold)
            count, _, stats, _ = cv2.connectedComponentsWithStats(mask, connectivity=8)
            for x, y, w, h, area in stats[1:count]:
                if area >= 2:
                    sx, sy = (x2 - x1) / heat.shape[1], (y2 - y1) / heat.shape[0]
                    boxes.append(((x1+x*sx, y1+y*sy, x1+(x+w)*sx, y1+(y+h)*sy), 0, score))
            if not boxes:
                y, x = np.unravel_index(np.argmax(heat), heat.shape)
                sx, sy = (x2 - x1) / heat.shape[1], (y2 - y1) / heat.shape[0]
                boxes.append(((x1+x*sx, y1+y*sy, x1+(x+1)*sx, y1+(y+1)*sy), 0, score))
        return boxes, view, score, threshold

    return {0: "疑似异常"}, predict
