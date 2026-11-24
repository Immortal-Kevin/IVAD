"""Explicit evaluation of a frozen detector on one IDS holdout."""

from collections import defaultdict
import hashlib
import importlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from zipfile import ZipFile

import numpy as np

from anomaly import read_image
from events import emit
from ids import inspect_package, select_videos, source_timelines
from partitions import partition


def overlap(box, target):
    x, y, a, b = box
    u, v, c, d = target
    intersection = max(0, min(a, c) - max(x, u)) * max(0, min(b, d) - max(y, v))
    union = (a - x) * (b - y) + (c - u) * (d - v) - intersection
    return intersection / union if union > 0 else 0


def matches(detections, labels, iou):
    seen = defaultdict(set)
    for score, frame, box in detections:
        options = [(overlap(box, target), i) for i, target in enumerate(labels[frame]) if i not in seen[frame]]
        best, index = max(options, default=(0, -1))
        if best >= iou:
            seen[frame].add(index)
        yield score, best >= iou


def evaluate(args):
    from worker import configure, device, validate_size, weights_path

    if args.model == "anomaly" or args.manifest is None or args.ids is None or not 0 < args.confidence <= 1:
        raise ValueError("请选择检测权重、IDS、拆分清单和有效置信度阈值")
    validate_size(args)
    args.weights = weights_path(args.weights, args.model)
    with args.weights.open("rb") as file:
        fingerprint = hashlib.file_digest(file, "sha256").hexdigest()
    stored = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary, frames = inspect_package(args.ids)
    videos, frames = select_videos(summary, frames, stored["selected_videos"])
    lookup = {f.id: f for f in frames}
    _, rebuilt = partition(frames, videos, summary["target_sha256"], "detection",
                           test_only=stored.get("test_only_videos", ()), timelines=source_timelines(summary))
    if (stored.get("mode") != "detection" or stored["document_sha256"] != summary["target_sha256"]
            or rebuilt["planned"] != stored["planned"]):
        raise ValueError("IDS 与检测拆分清单不匹配")
    rows = rebuilt["planned"][args.evaluation_set]
    if not rows:
        raise ValueError("所选留出集合没有样本")
    threshold = args.confidence
    args.confidence = min(.001, threshold)
    labels, predictions = defaultdict(lambda: defaultdict(list)), defaultdict(list)
    normal_frames = false_positives = normal_flagged = 0
    with TemporaryDirectory(prefix="ivad-evaluate-") as temporary:
        configure(Path(temporary))
        device(args)
        names, predict = importlib.import_module(args.model).predictor(args)
        reverse = {row["name"]: i for i, row in enumerate(summary["classes"])}
        id_map = {i: reverse[name] for i, name in names.items() if name in reverse}
        with ZipFile(args.ids) as archive:
            emit("stage", value=f"权重和阈值已固定，正在评估留出 {args.evaluation_set}")
            for row in rows:
                frame = lookup[row["frame"]]
                detections = predict(read_image(archive, row["asset"]))
                for label, *box in frame.boxes:
                    labels[label][frame.id].append(box)
                for box, ident, score in detections:
                    if int(ident) in id_map:
                        predictions[id_map[int(ident)]].append((float(score), frame.id, box))
                if frame.state == "normal":
                    flags = sum(score >= threshold for _, _, score in detections)
                    normal_frames += 1
                    false_positives += flags
                    normal_flagged += flags > 0
    ap, recalls = [], []
    for label, truth in labels.items():
        total = sum(map(len, truth.values()))
        candidates = sorted(predictions[label], key=lambda item: -item[0])
        for iou in np.linspace(.5, .95, 10):
            paired = list(matches(candidates, truth, iou))
            tp = np.cumsum([ok for _, ok in paired])
            recall = tp / total
            precision = tp / np.arange(1, len(tp) + 1)
            ap.append(float(np.mean([precision[recall >= r].max(initial=0) for r in np.linspace(0, 1, 101)])))
            if iou == .5:
                recalls.append(sum(ok for score, ok in paired if score >= threshold) / total)
    result = {"set": args.evaluation_set, "weights_sha256": fingerprint, "threshold": threshold,
              "images": len(rows), "map": float(np.mean(ap)) if ap else None,
              "recall": float(np.mean(recalls)) if recalls else None, "normal_frames": normal_frames,
              "normal_frames_flagged": normal_flagged, "false_positive_boxes": false_positives}
    output = args.manifest.parent / f"{args.evaluation_set}-evaluation-{uuid4().hex[:8]}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("evaluation", path=str(output), **result)
