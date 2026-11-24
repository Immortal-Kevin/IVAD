"""Deterministic, temporally embargoed holdouts for reviewed IDS frames."""

from bisect import bisect_left, bisect_right
from collections import defaultdict, deque
from itertools import accumulate, zip_longest
from random import Random
from statistics import median

SEED = 42


def counts(frames):
    positive = sum(bool(frame.boxes) for frame in frames)
    return {"images": len(frames), "positive": positive, "normal": len(frames) - positive,
            "boxes": sum(len(frame.boxes) for frame in frames)}


def video_groups(frames):
    for field, minimum_gap, maximum_duration in (
            ("pts", 5_000_000, 30_000_000),
            ("source_timestamp", 50_000_000, 300_000_000),
            ("decode_index", 0, 0)):
        times = [getattr(frame, field) for frame in frames]
        if (len(times) > 1 and all(type(value) is int and value >= 0 for value in times)
                and len(set(times)) == len(times)):
            break
    else:
        return sorted(frames, key=lambda f: f.id), [0, len(frames)], None, None, None
    frames = sorted(frames, key=lambda frame: getattr(frame, field))
    times = [getattr(frame, field) for frame in frames]
    deltas = [b - a for a, b in zip(times, times[1:])]
    cadence = int(median(deltas))
    gap = max(minimum_gap, 5 * cadence)
    min_frames = min(32, max(4, len(frames) // 5))
    duration = max(min_frames * cadence, min(maximum_duration, (times[-1] - times[0]) // 5))
    positives = [i for i, frame in enumerate(frames) if frame.boxes]
    blocked = {cut for a, b in zip(positives, positives[1:]) if times[b] - times[a] <= 3 * cadence
               for cut in range(a + 1, b + 1)}
    cuts = [0]
    for i in range(1, len(frames)):
        if i not in blocked and (deltas[i - 1] > gap or times[i] - times[cuts[-1]] >= duration):
            cuts.append(i)
    return frames, cuts + [len(frames)], field, times, gap


def holdouts(frames, cuts, times, gap):
    """Return the best positive, normal-only and relaxed positive windows."""
    if gap is None or len(cuts) <= 2:
        return None, None, None
    positives = list(accumulate((bool(f.boxes) for f in frames), initial=0))
    target = max(1, round(len(frames) / 5))
    target_pos = min(max(1, positives[-1] - 1), max(2, round(positives[-1] / 5)))
    preferred = [None, None, None]
    for group, start in enumerate(cuts[:-1]):
        near = bisect_left(cuts, start + target, lo=group + 1)
        for j in sorted({group + 1, max(group + 1, near - 1), min(near, len(cuts) - 1)}):
            stop = cuts[j]
            left = bisect_left(times, times[start] - gap)
            right = bisect_right(times, times[stop - 1] + gap)
            if left == 0 and right == len(frames):
                continue
            val_pos = positives[stop] - positives[start]
            train_pos = positives[left] + positives[-1] - positives[right]
            mixed = val_pos < stop - start
            # Keep training positives from this video where possible.
            kind = (0 if train_pos else 2) if val_pos else 1
            if kind == 1 and positives[-1] and not train_pos:
                continue
            rank = (not mixed, abs(val_pos - target_pos), abs(stop - start - target),
                    (start - left) + (right - stop), start, stop)
            if preferred[kind] is None or rank < preferred[kind][0]:
                preferred[kind] = (rank, (left, start, stop, right))
    return tuple(option[1] if option else None for option in preferred)


def sample(frames, limit, training):
    if limit is not None and len(frames) > limit:
        by_kind = [defaultdict(list), defaultdict(list)]
        for frame in frames:
            by_kind[not bool(frame.boxes)][frame.video].append(frame)
        # Interleave source videos within each class and interleave positive and normal rows.
        kinds = []
        for streams in by_kind:
            pending = deque(map(iter, streams.values()))
            interleaved = []
            while pending and len(interleaved) < limit:
                stream = pending.popleft()
                frame = next(stream, None)
                if frame is not None:
                    interleaved.append(frame)
                    pending.append(stream)
            kinds.append(interleaved)
        frames = [item for pair in zip_longest(*kinds) for item in pair if item is not None][:limit]
    else:
        frames = list(frames)
    if training:
        Random(SEED).shuffle(frames)
    return frames


def automatic_split(frames, document_sha256, limit):
    unique = {}
    for frame in sorted(frames, key=lambda f: (f.video, f.id)):
        prior = unique.setdefault(frame.asset, frame)
        if sorted(prior.boxes) != sorted(frame.boxes):
            raise ValueError("Identical frame images have conflicting reviewed annotations")
    if not any(frame.boxes for frame in unique.values()):
        raise ValueError("没有可用于检测训练的有效正例框")
    sources = defaultdict(list)
    for frame in unique.values():
        sources[frame.video].append(frame)

    planned = {}
    selected = {}
    for video, items in sources.items():
        ordered, cuts, field, times, gap = video_groups(items)
        positive, normal, relaxed = holdouts(ordered, cuts, times, gap)
        planned[video] = (ordered, cuts, field, gap, positive, relaxed)
        selected[video] = positive or normal

    if not any(plan[4] for plan in planned.values()):
        for video, (_, _, _, _, _, relaxed) in planned.items():
            if relaxed and any(other != video and any(f.boxes for f in items)
                               for other, items in sources.items()):
                selected[video] = relaxed
                # A normal-only holdout preserves at least one positive from its video.
                break
        else:
            selected = dict.fromkeys(planned)

    report = {}
    assignment = {"train": [], "valid": [], "embargo": []}
    groups = {}
    for video, (ordered, cuts, field, gap, _, _) in planned.items():
        window = selected[video]
        parts = {"train": [], "valid": [], "embargo": []}
        positive_groups = dict.fromkeys(parts, 0)
        for group, (start, stop) in enumerate(zip(cuts, cuts[1:]), 1):
            group_positive = set()
            for i in range(start, stop):
                frame = ordered[i]
                bucket = "train"
                if window:
                    left, lower, upper, right = window
                    if lower <= i < upper:
                        bucket = "valid"
                    elif left <= i < right:
                        bucket = "embargo"
                parts[bucket].append(frame)
                groups[frame.id] = f"{video}:{group}"
                if frame.boxes:
                    group_positive.add(bucket)
            for bucket in group_positive:
                positive_groups[bucket] += 1
        report[video] = {"ordering": field, "gap": gap,
                         **{bucket: {**counts(items), "positive_groups": positive_groups[bucket]}
                            for bucket, items in parts.items()}}
        for bucket, items in parts.items():
            assignment[bucket].extend(items)
    splits = {side: sample(assignment[side], limit, side == "train") for side in ("train", "valid")}
    train_groups = {groups[frame.id] for frame in assignment["train"]}
    valid_groups = {groups[frame.id] for frame in assignment["valid"]}
    if train_groups & valid_groups:
        raise RuntimeError("IDS split assigned a temporal group to both training and validation")
    used_by_video = {video: {side: [] for side in splits} for video in sources}
    for side, rows in splits.items():
        for frame in rows:
            used_by_video[frame.video][side].append(frame)
    used_report = {video: {side: {**counts(rows),
                                   "positive_groups": len({groups[f.id] for f in rows if f.boxes})}
                           for side, rows in parts.items()} for video, parts in used_by_video.items()}

    def entry(frame):
        return {"frame": frame.id, "video": frame.video, "pts_us": frame.pts,
                "source_timestamp_100ns": frame.source_timestamp, "decode_index": frame.decode_index,
                "group": groups[frame.id], "asset": frame.asset, "boxes": len(frame.boxes)}

    manifest = {
        "method": "automatic_temporal_groups_v2", "seed": SEED,
        "document_sha256": document_sha256, "validation": any(f.boxes for f in splits["valid"]),
        "limit_per_split": limit, "used_videos": used_report,
        "duplicate_assets_removed": len(frames) - len(unique), "videos": report,
        "planned": {side: [entry(frame) for frame in rows] for side, rows in assignment.items()},
        "used": {side: [frame.id for frame in rows] for side, rows in splits.items()},
    }
    return splits, manifest
