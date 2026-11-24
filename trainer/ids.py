"""Read-only IVAD Annotator IDS 1.0 detection projection."""

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
from io import BytesIO
import json
import math
from pathlib import Path
import re
from uuid import UUID
from zipfile import ZipFile

from PIL import Image

from split import counts
from partitions import partition

ASSET_PATH = re.compile(r"assets/([0-9a-f]{64})\.[a-zA-Z0-9]{1,12}\Z")
MAX_METADATA = 16 * 1024**2


def require(condition, message):
    if not condition:
        raise ValueError(message)


def json_entry(archive, name):
    require(archive.getinfo(name).file_size <= MAX_METADATA, f"IDS metadata too large: {name}")
    raw = archive.read(name)
    return raw, json.loads(raw.decode("utf-8-sig"))


def read_manifest(archive):
    entries = archive.infolist()
    names = {entry.filename for entry in entries}
    require(len({name.casefold() for name in names}) == len(entries), "Duplicate IDS entries")
    require(len(entries) <= 100_000 and sum(e.file_size for e in entries) <= 20 * 1024**3,
            "IDS exceeds archive limits")
    _, envelope = json_entry(archive, "package.json")
    require(envelope["format"] == "ids-package/1.0", "Unsupported IDS package format")
    if envelope["mode"] == "incremental":
        raise ValueError("Incremental IDS requires base SHA-256 "
                         f"{envelope['base_sha256']}. Export a full package in Annotator.")
    require(envelope["mode"] == "full" and envelope.get("base_sha256") is None,
            "Unsupported IDS package mode")
    raw, document = json_entry(archive, "document.json")
    require(hashlib.sha256(raw).hexdigest() == envelope["target_sha256"],
            "IDS document SHA-256 mismatch")
    require(document["schema"] == "ids/1.0", "Unsupported IDS document schema")
    assets = {asset["path"]: asset for asset in document["assets"]}
    require(len(assets) == len(document["assets"]), "Duplicate IDS asset records")
    require(sorted(assets) == sorted(envelope["included_assets"]) and
            names == set(assets) | {"package.json", "document.json"}, "IDS asset inventory mismatch")
    for path, asset in assets.items():
        match = ASSET_PATH.fullmatch(path)
        require(match and match[1] == asset["sha256"], "Invalid content-addressed IDS asset")
        info = archive.getinfo(path)
        require(info.file_size == asset["bytes"] and (info.external_attr >> 28) != 10,
                "IDS asset size mismatch or symlink")
    return document, envelope["target_sha256"]


@dataclass
class Frame:
    id: str
    asset: str
    video: str
    pts: int
    width: int
    height: int
    boxes: list
    source_timestamp: int | None = None
    decode_index: int | None = None
    state: str = "normal"
    events: tuple = ()


def annotation_box(data, frame):
    points = data["points"]
    require(data["coordinate_space"] == "source_pixels" and
            all(type(value) in (float, int) and math.isfinite(value) for value in points),
            "Invalid IDS annotation coordinates")
    if data["shape"] == "box" and len(points) == 4:
        x1, y1, x2, y2 = points
    elif data["shape"] == "polygon" and len(points) >= 6 and len(points) % 2 == 0:
        xs, ys = points[::2], points[1::2]
        x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
    else:
        raise ValueError("Unsupported IDS detection geometry")
    require(0 <= x1 < x2 <= frame.width and 0 <= y1 < y2 <= frame.height,
            f"IDS annotation outside frame {frame.id}")
    return x1, y1, x2, y2


def inspect_package(path):
    with ZipFile(path) as archive:
        doc, digest = read_manifest(archive)
        entities = {}
        kinds = defaultdict(list)
        for entry in doc["entities"]:
            key = UUID(entry["id"]).hex
            require(key not in entities, "Duplicate IDS entity")
            entities[key] = entry
            kinds[entry["kind"]].append(entry)

        def lookup(key, kind):
            entity = entities.get(UUID(key).hex)
            require(entity and entity["kind"] == kind, f"Broken IDS {kind} reference")
            return entity

        lookup(doc["project_id"], "Project")
        faults = sorted(kinds["Fault"], key=lambda fault: fault["id"])
        labels = [fault["data"]["name"] for fault in faults]
        require(all(isinstance(label, str) and label.strip() for label in labels), "IDS has an invalid fault class")
        classes = {UUID(fault["id"]).hex: i for i, fault in enumerate(faults)}
        reviews = {}
        for entry in kinds["Review"]:
            data = entry["data"]
            frame = lookup(data["frame_id"], "Frame")
            key = UUID(frame["id"]).hex
            # Annotator stores review history in document order.
            reviews[key] = data["status"]

        assets = {asset["path"]: asset for asset in doc["assets"]}
        all_frames = {}
        event_ids = defaultdict(set)
        for entry in kinds["Event"]:
            for frame_id in entry["data"].get("frame_ids", []):
                event_ids[UUID(frame_id).hex].add(entry["id"])
        for entry in kinds["Frame"]:
            data = entry["data"]
            lookup(data["video_id"], "Video")
            require(data["asset_path"] in assets, "Frame image missing from IDS inventory")
            for field in ("width", "height"):
                require(type(data[field]) is int and data[field] > 0, "Invalid IDS frame dimensions")
            key = UUID(entry["id"]).hex
            if data.get("event_id"):
                event_ids[key].add(str(data["event_id"]))
            frame = Frame(key, data["asset_path"], str(UUID(data["video_id"])), data.get("pts_us"),
                          data["width"], data["height"], [], data.get("source_timestamp_100ns"), data.get("decode_index"),
                          data["state"])
            all_frames[frame.id] = frame
        for entry in kinds["Annotation"]:
            data = entry["data"]
            if data.get("deleted"):
                continue
            frame = all_frames[UUID(data["frame_id"]).hex]
            label = classes[UUID(data["fault_id"]).hex]
            frame.boxes.append((label, *annotation_box(data, frame)))
            if data.get("event_id"):
                event_ids[frame.id].add(str(data["event_id"]))

        images = defaultdict(list)
        for frame in all_frames.values():
            images[frame.asset].append(frame)
        for key, asset in assets.items():
            with archive.open(key) as stream:
                require(hashlib.file_digest(stream, "sha256").hexdigest() == asset["sha256"],
                        "IDS asset SHA-256 mismatch")
            if key in images:
                with archive.open(key) as stream, Image.open(stream) as image:
                    size = image.size
                    image.verify()
                require(all(size == (frame.width, frame.height) for frame in images[key]),
                        "Image dimensions differ from IDS metadata")

    eligible = []
    excluded = Counter()
    for entry in kinds["Frame"]:
        key = UUID(entry["id"]).hex
        frame, data = all_frames[key], entry["data"]
        frame.events = tuple(sorted(event_ids[key]))
        if data.get("queue_deleted") or reviews.get(key) != "confirmed":
            excluded["unconfirmed or deleted"] += 1
        elif data["state"] == "normal":
            require(not frame.boxes, "Confirmed normal IDS frame contains targets")
            eligible.append(frame)
        elif data["state"] == "abnormal":
            eligible.append(frame)
        else:
            excluded["unknown state"] += 1
    fault_map = [{"id": fault["id"], "name": fault["data"]["name"]} for fault in faults]
    states = Counter(entry["data"]["state"] for entry in kinds["Frame"])
    annotations = Counter(box[0] for frame in all_frames.values() for box in frame.boxes)
    totals = Counter(frame.video for frame in all_frames.values())
    by_video = defaultdict(list)
    for frame in eligible:
        by_video[frame.video].append(frame)
    videos = []
    for entry in kinds["Video"]:
        video = str(UUID(entry["id"]))
        stats = counts(by_video[video])
        videos.append({"id": video, "name": entry["data"].get("original_name") or video,
                       "images": totals[video], "positive": stats["positive"], "boxes": stats["boxes"]})
    for index, label in enumerate(fault_map):
        label["annotations"] = annotations[index]
    summary = {"target_sha256": digest, "images": len(all_frames), "assets": len(assets), "states": dict(states),
               "annotations": sum(len(frame.boxes) for frame in all_frames.values()),
               "classes": fault_map, "eligible": len(eligible), "excluded": dict(excluded),
               "videos": videos}
    return summary, eligible


def select_videos(summary, frames, requested):
    videos = {row["id"]: row["name"] for row in summary["videos"]}
    selected = videos.keys() if requested is None else set(requested)
    require(selected, "请至少选择一个源视频")
    require(selected <= videos.keys(), "所选源视频与当前 IDS 不匹配，请重新导入 IDS")
    return {key: name for key, name in videos.items() if key in selected}, [f for f in frames if f.video in selected]


def write_plan(run, summary, frames, videos, mode, model, early_stop, limit=None):
    from events import emit

    splits, manifest = partition(frames, videos, summary["target_sha256"], mode, limit)
    status = ("正常片段校准阈值" if mode == "anomaly" else
              "同源视频留出验证" if manifest["validation"] else "无正例验证")
    stop_status = ("不可用（无正例验证）" if not manifest["validation"] else
                   "仅支持 RF-DETR" if model != "rf" else "开启" if early_stop else "关闭")
    manifest_path = run / "split-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"纳入源视频：{'、'.join(videos.values())}", f"自动拆分 · {status}"]
    if mode == "detection":
        lines.append(f"自动早停 · {stop_status}")
    for index, (video, name) in enumerate(videos.items(), 1):
        stats = manifest["videos"][video]
        if not stats["ordering"]:
            lines.append(f"[{name}] 时间戳及帧序号不足，整段作为一个片段")
        elif stats["ordering"] == "decode_index":
            lines.append(f"[{name}] 使用帧序号分组，无法计算实际回放时长")
        for side, label in (("train", "Train"), ("valid", "Val"), ("test", "Test"), ("embargo", "排除")):
            row = stats[side]
            lines.append(f"视频 {index} [{name}] {label}  {row['images']} 张 · 正例 {row['positive']} 张"
                         f" · 正常 {row['normal']} 张 · 事件 {row['event_groups']} 组 · {row['boxes']} 框")
    if limit is not None:
        lines.append(f"短训实际读取 Train {len(splits['train'])} / Val {len(splits['valid'])} 张")
    if mode == "detection":
        for side, label in (("valid", "Val"), ("test", "Test")):
            if not any(f.boxes for f in splits[side]):
                lines.append(f"{label} 无正例 · mAP、召回率不可计算 · 正常片段可评估误报")
        lines.append("Test 在确认权重和阈值后单独评估")
    else:
        lines.append("仅 Train 拟合、仅 Val 定阈值，Test 用于事件命中和正常误报报告")
    validation_summary = " / ".join(f"{label} {len(splits[side])} 张" for side, label in
                                    (("train", "Train"), ("valid", "Val"), ("test", "Test")))
    emit("split", mode=status, validation_summary=validation_summary, early_stop_status=stop_status,
         detail="\n".join(lines), path=str(manifest_path))
    print("\n".join(lines), flush=True)
    print(f"Split manifest: {manifest_path}", flush=True)
    return splits, manifest


def prepare(path, output, model, summary, splits):
    import yaml

    output.mkdir(parents=True)
    cats = summary["classes"]
    names = [category["name"] for category in cats]
    yolo = model == "yolo"
    with ZipFile(path) as archive:
        _, digest = read_manifest(archive)
        require(digest == summary["target_sha256"], "IDS changed after validation")
        for split in ("train", "valid"):
            items = splits[split]
            images = output / ("images" if yolo else "") / split
            images.mkdir(parents=True)
            labels = output / "labels" / split
            if yolo:
                labels.mkdir(parents=True)
            categories = [{"id": i + 1, "name": name, "supercategory": "defect",
                           "ids_fault_id": cats[i]["id"]} for i, name in enumerate(names)]
            coco = {"info": {}, "licenses": [], "images": [], "annotations": [],
                    "categories": categories}
            for i, frame in enumerate(items, 1):
                file = frame.id + ".png"
                raw = archive.read(frame.asset)
                _, expected = frame.asset.split("/")
                require(hashlib.sha256(raw).hexdigest() == expected.split(".")[0],
                        "Frame asset changed after validation")
                with Image.open(BytesIO(raw)) as image:
                    image.convert("RGB").save(images / file)
                coco["images"].append(dict(id=i, file_name=file, width=frame.width, height=frame.height))
                lines = []
                for label, x1, y1, x2, y2 in frame.boxes:
                    width, height = x2 - x1, y2 - y1
                    if yolo:
                        coords = ((x1 + x2) / (2 * frame.width), (y1 + y2) / (2 * frame.height),
                                  width / frame.width, height / frame.height)
                        lines.append(f"{label} " + " ".join(f"{v:.9g}" for v in coords))
                    else:
                        coco["annotations"].append(dict(id=len(coco["annotations"]) + 1, image_id=i,
                            category_id=label + 1, bbox=[x1, y1, width, height], area=width * height,
                            iscrowd=0, segmentation=[]))
                if yolo:
                    (labels / (frame.id + ".txt")).write_text("\n".join(lines), encoding="utf-8")
            if not yolo:
                (images / "_annotations.coco.json").write_text(json.dumps(coco), encoding="utf-8")
    if yolo:
        config = output / "data.yaml"
        config.write_text(yaml.safe_dump({"path": output.as_posix(), "train": "images/train",
                         "val": "images/valid", "names": names}, allow_unicode=True), encoding="utf-8")
        return config
    return output
