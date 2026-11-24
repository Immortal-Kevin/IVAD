"""Group-preserving IDS train, validation and test partitions."""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from random import Random
from statistics import median

from split import SEED, sample

SIDES = ("train", "valid", "test")


def asset_key(path):
    return path.rsplit("/", 1)[-1].split(".", 1)[0]


def stratify_frames(plan, assignment, test_only):
    """Reuse the event planner's holdout sizes, then sample unique detector images by class."""
    targets = {side: sum(row["video"] not in test_only for row in plan[side]) for side in ("valid", "test")}
    # Integer round-half-up of count / 5 (remainders 3 and 4 round up).
    positive_targets = {side: (count + 2) // 5 for side, count in targets.items()}
    selected = {side: [] for side in plan}
    images = {}
    prior_frames = set()
    pairs = sorted(((frame, row) for side in plan for frame, row in zip(assignment[side], plan[side])),
                   key=lambda pair: (pair[0].video not in test_only, pair[0].video, pair[0].id))
    for frame, row in pairs:
        if frame.id in prior_frames:
            raise ValueError("按帧分层发现重复帧 ID")
        prior_frames.add(frame.id)
        if frame.video not in test_only and frame.state == "abnormal" and not frame.boxes:
            selected["embargo"].append((frame, row))
            continue
        key = asset_key(frame.asset)
        if key in images:
            other, _ = images[key]
            if frame.video in test_only or other.video in test_only:
                raise ValueError("仅测试源含重复图像资产，无法安全整段加入 Test")
            if frame.state != other.state or sorted(frame.boxes) != sorted(other.boxes):
                raise ValueError("重复图像资产带有冲突的审核状态或标注")
            selected["embargo"].append((frame, row))
            continue
        images[key] = (frame, row)
    automatic = []
    for pair in images.values():
        (selected["test"] if pair[0].video in test_only else automatic).append(pair)
    positive = [pair for pair in automatic if pair[0].boxes]
    normal = [pair for pair in automatic if pair[0].state == "normal"]
    rng = Random(SEED)
    rng.shuffle(positive)
    rng.shuffle(normal)

    # Preserve class coverage and at least half the available positive images for training.
    covered, reserved, available = set(), [], []
    for pair in positive:
        classes = {box[0] for box in pair[0].boxes}
        if classes - covered:
            reserved.append(pair)
            covered.update(classes)
        else:
            available.append(pair)
    extra = max(0, (len(positive) + 1) // 2 - len(reserved))
    reserved.extend(available[:extra])
    available = iter(available[extra:])
    holdouts = {side: [] for side in targets}
    for i in range(max(positive_targets.values())):
        for side, count in positive_targets.items():
            if i < count:
                pair = next(available, None)
                if pair is not None:
                    holdouts[side].append(pair)
    n = iter(normal)
    for _ in range(max(targets.values())):
        for side, count in targets.items():
            if len(holdouts[side]) < count:
                pair = next(n, None)
                if pair is not None:
                    holdouts[side].append(pair)
    selected["train"].extend(reserved + list(available) + list(n))
    for side, rows in holdouts.items():
        selected[side].extend(rows)
        selected[side].sort(key=lambda pair: (pair[0].video, pair[1]["time_s"] is None,
                                              pair[1]["time_s"] or 0, pair[0].id))
    report = {side: {"target_images": targets[side], "target_positive": positive_targets[side],
                     "images": len(rows), "positive": sum(bool(f.boxes) for f, _ in rows),
                     "normal": sum(f.state == "normal" for f, _ in rows),
                     "boxes": sum(len(f.boxes) for f, _ in rows)} for side, rows in holdouts.items()}
    return ({side: [row for _, row in pairs] for side, pairs in selected.items()},
            {side: [frame for frame, _ in pairs] for side, pairs in selected.items()}, report)


@dataclass
class Clip:
    id: str
    frames: list
    side: str = "train"

    @property
    def abnormal(self):
        return any(frame.state == "abnormal" or frame.events for frame in self.frames)

    @property
    def boxes(self):
        return sum(len(frame.boxes) for frame in self.frames)


def clock(frames):
    for field, scale, minimum in (("pts", 1e-6, 5_000_000),
                                  ("source_timestamp", 1e-7, 50_000_000), ("decode_index", None, 0)):
        values = {f.id: getattr(f, field) for f in frames}
        if len(values) > 1 and all(type(t) is int and t >= 0 for t in values.values()) and len(set(values.values())) == len(values):
            times = sorted(values.values())
            step = median(b - a for a, b in zip(times, times[1:]))
            return field, values, max(minimum, 5 * step), scale, step
    return None, {}, None, None, None


def source_clips(frames, values, gap):
    video = frames[0].video
    if not values:
        return [Clip(f"{video}:1", sorted(frames, key=lambda f: f.id))]
    frames = sorted(frames, key=lambda f: values[f.id])
    spans = {}
    for i, frame in enumerate(frames):
        for event in frame.events:
            spans.setdefault(event, [i, i])[1] = i
    abnormal = [i for i, frame in enumerate(frames) if frame.state == "abnormal"]
    runs = spans.values()
    merged = []
    for start, end in sorted([*runs, *((i, i) for i in abnormal)]):
        if merged and values[frames[start].id] - values[frames[merged[-1][1]].id] <= 2 * gap:
            merged[-1][1] = max(end, merged[-1][1])
        else:
            merged.append([start, end])
    clips = []

    def add(start, end):
        if end > start:
            clips.append(Clip(f"{video}:{len(clips) + 1}", frames[start:end]))

    def normals(start, end):
        cut = start
        for i in range(start + 1, end):
            if i - cut >= 32 or values[frames[i].id] - values[frames[i - 1].id] > gap:
                add(cut, i)
                cut = i
        add(cut, end)

    start = 0
    for left, right in merged:
        normals(start, left)
        add(left, right + 1)
        start = right + 1
    normals(start, len(frames))
    return clips


def place_normals(clips):
    normal = [c for c in clips if not c.abnormal]
    if len(normal) < 2:
        return
    budget = max(1, round(sum(len(c.frames) for c in normal) * .15))
    for side in ("valid", "test"):
        available = [c for c in normal if c.side == "train"]
        if len(available) < 2:
            break
        candidates = []
        for start in range(len(available)):
            block = []
            size = 0
            for clip in available[start:]:
                if len(block) + 1 == len(available):
                    break
                block.append(clip)
                size += len(clip.frames)
                if size >= budget:
                    break
            candidates.append((abs(size - budget), start, block))
        for clip in min(candidates)[2]:
            clip.side = side


def check_source_overlap(plan, timelines):
    """Compare source times only when two records have common media provenance."""
    if not timelines:
        return
    ranges = defaultdict(dict)
    for side in SIDES:
        for row in plan[side]:
            video = row["video"]
            provenance = timelines.get(video)
            if not provenance:
                continue
            origin, offset = provenance
            key = (side, video, row["group"])
            t = row["pts_us"]
            if type(t) is not int or offset is None:
                ranges[origin][key] = None
            elif key not in ranges[origin]:
                ranges[origin][key] = (t + offset, t + offset)
            elif ranges[origin][key] is not None:
                lo, hi = ranges[origin][key]
                ranges[origin][key] = (min(lo, t + offset), max(hi, t + offset))
    for clips in ranges.values():
        if len({video for _, video, _ in clips}) < 2:
            continue
        items = list(clips.items())
        for i, ((side, video, _), interval) in enumerate(items):
            for (other, other_video, _), candidate in items[i + 1:]:
                if side == other or video == other_video:
                    continue
                if interval is None or candidate is None:
                    raise ValueError(f"同源视频 {video} 与 {other_video} 跨 {side}/{other}，缺少可核查的源时间区间")
                if max(interval[0], candidate[0]) <= min(interval[1], candidate[1]):
                    raise ValueError(f"同源视频 {video} 与 {other_video} 在 {side}/{other} 的时间区间重叠")


def partition(frames, videos, digest, mode, limit=None, test_only=(), timelines=None, strategy="events"):
    stratified = mode == "detection" and strategy == "frames"
    test_only = set(test_only)
    if test_only - videos.keys():
        raise ValueError("仅测试源必须是已勾选的 IDS 源视频")
    if not (videos.keys() - test_only):
        raise ValueError("只有仅测试源。请至少勾选一个参与自动拆分的源视频才能开始训练")
    sources = defaultdict(list)
    for frame in frames:
        sources[frame.video].append(frame)
    clips, clocks = {}, {}
    for video in videos:
        if sources[video]:
            clocks[video] = clock(sources[video])
            clips[video] = source_clips(sources[video], *clocks[video][1:3])
    automatic = [clip for video, items in clips.items() if video not in test_only for clip in items]
    if not automatic:
        raise ValueError("参与自动拆分的源没有可用的已审核帧")
    for video in test_only:
        for clip in clips.get(video, []):
            clip.side = "test"
    if mode == "anomaly":
        for clip in automatic:
            if clip.abnormal:
                clip.side = "test"
    else:
        positive = sorted((c for c in automatic if c.boxes), key=lambda c: (-c.boxes, c.id))
        if not positive:
            raise ValueError("所选视频没有已确认的有效正例框")
        if len(positive) >= 2:
            positive[-1].side = "valid"
        if len(positive) >= 3:
            positive[-2].side = "test"
    for video, items in clips.items():
        if video not in test_only:
            place_normals(items)

    # If multiple source IDs refer to the same explicit event, use a common side.
    event_clips = defaultdict(list)
    for clip in automatic:
        for key in {e for f in clip.frames for e in f.events}:
            event_clips[key].append(clip)
    while True:
        changed = False
        for linked in event_clips.values():
            side = min((c.side for c in linked), key=SIDES.index)
            for clip in linked:
                changed |= clip.side != side
                clip.side = side
        if not changed:
            break

    assignment = {side: [] for side in (*SIDES, "embargo")}
    plan = {side: [] for side in assignment}
    priority = ("test", "valid", "train") if mode == "anomaly" else SIDES
    for side in priority:
        for video, items in clips.items():
            field, values, gap, scale, step = clocks[video]
            for clip in (c for c in items if c.side == side):
                others = sorted(values[f.id] for c in items if c.side != side
                                and (c.abnormal or priority.index(c.side) < priority.index(side)) for f in c.frames)
                explicit = {event for f in clip.frames for event in f.events}
                for frame in clip.frames:
                    bucket = side
                    if video not in test_only and mode == "detection" and frame.state == "abnormal" and not frame.boxes:
                        bucket = "embargo"
                    elif others and not clip.abnormal:
                        t = values[frame.id]
                        i = bisect_left(others, t)
                        if any(abs(t - q) <= gap for q in others[max(0, i - 1):i + 1]):
                            bucket = "embargo"
                    assignment[bucket].append(frame)
                    events = (list(frame.events) or ([] if explicit else [clip.id])) if frame.state == "abnormal" else []
                    plan[bucket].append({"frame": frame.id, "asset": frame.asset, "video": video,
                                         "group": clip.id, "events": list(frame.events), "state": frame.state,
                                         "event_keys": events,
                                         "boxes": len(frame.boxes), "pts_us": frame.pts,
                                         "time_s": values[frame.id] * scale if scale is not None else None})

    holdouts = None
    if stratified:
        plan, assignment, holdouts = stratify_frames(plan, assignment, test_only)
    for i, side in enumerate(SIDES):
        for other in SIDES[i + 1:]:
            for key in (("frame", "asset") if stratified else ("frame", "asset", "group")):
                if {p[key] for p in plan[side]} & {p[key] for p in plan[other]}:
                    raise ValueError(f"{side}/{other} 存在跨集合重复{'图像资产' if key == 'asset' else '帧或片段组'}，已阻止拆分")
            hashes = {asset_key(p["asset"]) for p in plan[side]}
            if any(asset_key(p["asset"]) in hashes for p in plan[other]):
                raise ValueError(f"{side}/{other} 存在跨集合重复图像内容，已阻止拆分")
            if stratified:
                left = {e for p in plan[side] for e in p["events"]}
                right = {e for p in plan[other] for e in p["events"]}
                if left & right & {e for p in plan["test"] if p["video"] in test_only for e in p["events"]}:
                    raise ValueError("仅测试源与 Train 或 Val 共用明确标记的事件，已阻止拆分")
                continue
            if {e for p in plan[side] for e in p["events"]} & {e for p in plan[other] for e in p["events"]}:
                raise RuntimeError(f"{side}/{other} 共用事件，无法安全拆分")
            for video, (_, values, gap, _, _) in clocks.items():
                first = sorted(values[p["frame"]] for p in plan[side] if p["video"] == video and values)
                for p in plan[other]:
                    if p["video"] == video and values:
                        t = values[p["frame"]]
                        j = bisect_left(first, t)
                        if any(abs(t - q) <= gap for q in first[max(0, j - 1):j + 1]):
                            raise RuntimeError(f"{side}/{other} 无法保留时间间隔")

    check_source_overlap(plan, timelines)
    used = {side: sample(assignment[side], limit if mode == "detection" and side != "test" else None, side == "train")
            for side in SIDES}
    if mode == "detection" and not any(f.boxes for f in used["train"]):
        raise ValueError("拆分后没有可训练的有框正例")
    reports = {}
    for video in videos:
        field, _, gap, scale, step = clocks.get(video, (None, {}, None, None, None))
        report = {"ordering": field, "gap": gap, "cadence_s": step * scale if scale else None}
        for side in plan:
            rows = [p for p in plan[side] if p["video"] == video]
            report[side] = {"images": len(rows), "normal": sum(p["state"] == "normal" for p in rows),
                            "abnormal": sum(p["state"] == "abnormal" for p in rows),
                            "positive": sum(p["boxes"] > 0 for p in rows), "boxes": sum(p["boxes"] for p in rows),
                            "event_groups": len({e for p in rows for e in p["event_keys"]}),
                            "positive_groups": len({p["group"] for p in rows if p["boxes"]})}
        report["purpose"] = "test_only" if video in test_only else "automatic"
        report["destinations"] = [side for side in SIDES if report[side]["images"]]
        reports[video] = report
    manifest = {"method": "frame_stratified_three_way_v1" if stratified else "temporal_three_way_v2",
                "split_strategy": "frames" if stratified else "events",
                "mode": mode, "seed": SEED, "document_sha256": digest,
                "selected_videos": videos, "videos": reports, "planned": plan,
                "test_only_videos": sorted(test_only),
                "used": {k: [f.id for f in rows] for k, rows in used.items()},
                "validation": mode == "detection" and any(f.boxes for f in used["valid"])}
    if stratified:
        manifest["automatic_holdouts"] = holdouts
        manifest["test_only_counts"] = {"images": sum(p["video"] in test_only for p in plan["test"]),
                                        "positive": sum(p["video"] in test_only and p["boxes"] > 0 for p in plan["test"]),
                                        "boxes": sum(p["boxes"] for p in plan["test"] if p["video"] in test_only)}
    return used, manifest
