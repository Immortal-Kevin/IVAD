"""Group-preserving IDS train, validation and test partitions."""

from bisect import bisect_left
from collections import defaultdict
from dataclasses import dataclass
from statistics import median

from split import SEED, sample

SIDES = ("train", "valid", "test")


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


def partition(frames, videos, digest, mode, limit=None):
    sources = defaultdict(list)
    for frame in frames:
        sources[frame.video].append(frame)
    clips, clocks = {}, {}
    for video in videos:
        if sources[video]:
            clocks[video] = clock(sources[video])
            clips[video] = source_clips(sources[video], *clocks[video][1:3])
    all_clips = [clip for items in clips.values() for clip in items]
    if mode == "anomaly":
        for clip in all_clips:
            if clip.abnormal:
                clip.side = "test"
    else:
        positive = sorted((c for c in all_clips if c.boxes), key=lambda c: (-c.boxes, c.id))
        if not positive:
            raise ValueError("所选视频没有已确认的有效正例框")
        if len(positive) >= 2:
            positive[-1].side = "valid"
        if len(positive) >= 3:
            positive[-2].side = "test"
    for items in clips.values():
        place_normals(items)

    # If multiple source IDs refer to the same explicit event, use a common side.
    event_clips = defaultdict(list)
    for clip in all_clips:
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
    asset_sides = {}
    priority = ("test", "valid", "train") if mode == "anomaly" else SIDES
    for side in priority:
        for video, items in clips.items():
            field, values, gap, scale, step = clocks[video]
            for clip in (c for c in items if c.side == side):
                # If copied images occur in multiple clips, keep them in one set only.
                duplicate = any(asset_sides.get(f.asset, side) != side for f in clip.frames)
                others = sorted(values[f.id] for c in items if c.side != side
                                and (c.abnormal or priority.index(c.side) < priority.index(side)) for f in c.frames)
                explicit = {event for f in clip.frames for event in f.events}
                for frame in clip.frames:
                    bucket = side
                    if duplicate or (mode == "detection" and frame.state == "abnormal" and not frame.boxes):
                        bucket = "embargo"
                    elif others and not clip.abnormal:
                        t = values[frame.id]
                        i = bisect_left(others, t)
                        if any(abs(t - q) <= gap for q in others[max(0, i - 1):i + 1]):
                            bucket = "embargo"
                    assignment[bucket].append(frame)
                    if bucket != "embargo":
                        asset_sides[frame.asset] = side
                    events = (list(frame.events) or ([] if explicit else [clip.id])) if frame.state == "abnormal" else []
                    plan[bucket].append({"frame": frame.id, "asset": frame.asset, "video": video,
                                         "group": clip.id, "events": list(frame.events), "state": frame.state,
                                         "event_keys": events,
                                         "boxes": len(frame.boxes), "pts_us": frame.pts,
                                         "time_s": values[frame.id] * scale if scale is not None else None})

    for i, side in enumerate(SIDES):
        for other in SIDES[i + 1:]:
            for key in ("frame", "asset", "group"):
                if {p[key] for p in plan[side]} & {p[key] for p in plan[other]}:
                    raise RuntimeError(f"{side}/{other} 共用 {key}")
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
        reports[video] = report
    manifest = {"method": "temporal_three_way_v1", "mode": mode, "seed": SEED, "document_sha256": digest,
                "selected_videos": videos, "videos": reports, "planned": plan,
                "used": {k: [f.id for f in rows] for k, rows in used.items()},
                "validation": mode == "detection" and any(f.boxes for f in used["valid"])}
    return used, manifest
