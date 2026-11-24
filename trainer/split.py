"""Deterministic reporting and bounded short-training samples."""

from collections import defaultdict, deque
from itertools import zip_longest
from random import Random

SEED = 42


def counts(frames):
    positive = sum(bool(frame.boxes) for frame in frames)
    return {"images": len(frames), "positive": positive, "normal": sum(f.state == "normal" for f in frames),
            "boxes": sum(len(frame.boxes) for frame in frames)}



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
