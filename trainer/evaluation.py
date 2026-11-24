"""Explicit evaluation of a frozen detector on one IDS holdout."""

from collections import defaultdict
from copy import copy
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
        yield score, frame, best >= iou


def summarize(labels, predictions, threshold):
    ap, ap50, recalls = [], [], []
    hits = set()
    for label, truth in labels.items():
        total = sum(map(len, truth.values()))
        candidates = sorted(predictions[label], key=lambda item: -item[0])
        for iou in np.linspace(.5, .95, 10):
            paired = list(matches(candidates, truth, iou))
            tp = np.cumsum([ok for _, _, ok in paired])
            recall = tp / total
            precision = tp / np.arange(1, len(tp) + 1)
            value = float(np.mean([precision[recall >= r].max(initial=0) for r in np.linspace(0, 1, 101)]))
            ap.append(value)
            if iou == .5:
                ap50.append(value)
                matched = [frame for score, frame, ok in paired if score >= threshold and ok]
                hits.update(matched)
                recalls.append(len(matched) / total)
    return {"map50": float(np.mean(ap50)) if ap50 else None, "map": float(np.mean(ap)) if ap else None,
            "recall": float(np.mean(recalls)) if recalls else None, "positive_hits": len(hits)}


def evaluate(args):
    from worker import validate_size

    if args.model == "anomaly" or args.manifest is None or args.ids is None or not 0 < args.confidence <= 1:
        raise ValueError("请选择检测权重、IDS、拆分清单和有效置信度阈值")
    validate_size(args)
    stored = json.loads(args.manifest.read_text(encoding="utf-8"))
    summary, frames = inspect_package(args.ids)
    videos, frames = select_videos(summary, frames, stored["selected_videos"])
    strategy = stored.get("split_strategy", "events")
    if stored.get("method") == "frame_stratified_three_way_v1":
        strategy = "frames_legacy"
    _, rebuilt = partition(frames, videos, summary["target_sha256"], "detection",
                           test_only=stored.get("test_only_videos", ()), timelines=source_timelines(summary),
                           strategy=strategy, reuse=stored.get("allow_diagnostic_reuse", False))
    if (stored.get("mode") != "detection" or stored["document_sha256"] != summary["target_sha256"]
            or rebuilt["planned"] != stored["planned"]):
        raise ValueError("IDS 与检测拆分清单不匹配")
    return evaluate_frozen(args, summary, frames, videos, rebuilt)


def evaluate_frozen(args, summary, frames, videos, split):
    from worker import configure, device, weights_path

    args = copy(args)
    args.weights = weights_path(args.weights, args.model)
    with args.weights.open("rb") as file:
        fingerprint = hashlib.file_digest(file, "sha256").hexdigest()
    lookup = {f.id: f for f in frames}
    rows = split["planned"][args.evaluation_set]
    if not rows:
        raise ValueError("所选留出集合没有样本")
    threshold = args.confidence
    args.confidence = min(.001, threshold)
    reused = sum("reused_from" in row for row in rows)
    bucket_name = "训练内诊断" if reused else "同源帧评估" if split["split_strategy"] == "frames" else "按事件留出评估"
    labels, predictions = defaultdict(lambda: defaultdict(list)), defaultdict(list)
    buckets = {video: {"name": name, "images": 0, "positive_images": 0, "reused": 0,
                       "normal_frames": 0, "normal_frames_flagged": 0, "false_positive_boxes": 0}
               for video, name in videos.items()}
    ids_by_source = defaultdict(set)
    with TemporaryDirectory(prefix="ivad-evaluate-") as temporary:
        configure(Path(temporary))
        device(args)
        names, predict = importlib.import_module(args.model).predictor(args)
        reverse = {row["name"]: i for i, row in enumerate(summary["classes"])}
        id_map = {i: reverse[name] for i, name in names.items() if name in reverse}
        with ZipFile(args.ids) as archive:
            emit("stage", value=f"权重和阈值已固定，正在计算 {args.evaluation_set} · {bucket_name}")
            for row in rows:
                frame = lookup[row["frame"]]
                totals = buckets[frame.video]
                ids_by_source[frame.video].add(frame.id)
                totals["images"] += 1
                totals["positive_images"] += bool(frame.boxes)
                totals["reused"] += "reused_from" in row
                detections = predict(read_image(archive, row["asset"]))
                for label, *box in frame.boxes:
                    labels[label][frame.id].append(box)
                for box, ident, score in detections:
                    if int(ident) in id_map:
                        predictions[id_map[int(ident)]].append((float(score), frame.id, box))
                if frame.state == "normal":
                    flags = sum(score >= threshold for _, _, score in detections)
                    totals["normal_frames"] += 1
                    totals["false_positive_boxes"] += flags
                    totals["normal_frames_flagged"] += flags > 0
    scores = summarize(labels, predictions, threshold)
    for video, totals in buckets.items():
        ids = ids_by_source[video]
        truth = {k: defaultdict(list, {f: b for f, b in items.items() if f in ids and b}) for k, items in labels.items()}
        truth = {k: items for k, items in truth.items() if items}
        candidates = {k: [p for p in items if p[1] in ids] for k, items in predictions.items()}
        source_scores = summarize(truth, defaultdict(list, candidates), threshold)
        totals["positive_hits"] = source_scores["positive_hits"]
        if reused:
            totals["diagnostic_metrics"] = source_scores
        else:
            totals.update(source_scores)
        if totals["images"]:
            print(f"{args.evaluation_set} [{totals['name']}] 正例命中 {totals['positive_hits']}/{totals['positive_images']}"
                  f" · 复用 {totals['reused']} 张 · {bucket_name}", flush=True)
    result = {"set": args.evaluation_set, "weights_sha256": fingerprint, "threshold": threshold,
              "images": len(rows), "mode_label": bucket_name, "diagnostic": bool(reused), "reused": reused,
              "sources": list(buckets.values()),
              **{k: sum(v[k] for v in buckets.values()) for k in ("normal_frames", "normal_frames_flagged", "false_positive_boxes")}}
    if reused:
        result["diagnostic_metrics"] = scores
    else:
        result.update(scores)
    output = args.manifest.parent / f"{args.evaluation_set}-evaluation-{uuid4().hex[:8]}.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("evaluation", path=str(output), **result)
    return result
