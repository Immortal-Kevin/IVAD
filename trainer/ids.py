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

from split import automatic_split

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
        require(labels and all(isinstance(label, str) and label.strip() for label in labels),
                "IDS has no valid fault classes")
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
        for entry in kinds["Frame"]:
            data = entry["data"]
            lookup(data["video_id"], "Video")
            require(data["asset_path"] in assets, "Frame image missing from IDS inventory")
            for field in ("width", "height"):
                require(type(data[field]) is int and data[field] > 0, "Invalid IDS frame dimensions")
            frame = Frame(UUID(entry["id"]).hex, data["asset_path"], str(UUID(data["video_id"])), data.get("pts_us"),
                          data["width"], data["height"], [])
            all_frames[frame.id] = frame
        for entry in kinds["Annotation"]:
            data = entry["data"]
            if data.get("deleted"):
                continue
            frame = all_frames[UUID(data["frame_id"]).hex]
            label = classes[UUID(data["fault_id"]).hex]
            frame.boxes.append((label, *annotation_box(data, frame)))

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
        if data.get("queue_deleted") or reviews.get(key) != "confirmed":
            excluded["unconfirmed or deleted"] += 1
        elif data["state"] == "normal":
            require(not frame.boxes, "Confirmed normal IDS frame contains targets")
            eligible.append(frame)
        elif data["state"] == "abnormal" and frame.boxes:
            eligible.append(frame)
        else:
            excluded["unknown or abnormal without targets"] += 1
    fault_map = [{"id": fault["id"], "name": fault["data"]["name"]} for fault in faults]
    states = Counter(entry["data"]["state"] for entry in kinds["Frame"])
    annotations = Counter(box[0] for frame in all_frames.values() for box in frame.boxes)
    for index, label in enumerate(fault_map):
        label["annotations"] = annotations[index]
    summary = {"target_sha256": digest, "images": len(all_frames), "assets": len(assets), "states": dict(states),
               "annotations": sum(len(frame.boxes) for frame in all_frames.values()),
               "classes": fault_map, "eligible": len(eligible), "excluded": dict(excluded)}
    return summary, eligible


def prepare(path, output, model, summary, frames, limit=None):
    import yaml

    from events import emit

    splits, manifest = automatic_split(frames, summary["target_sha256"], limit)
    mode = "同源视频留出验证" if manifest["validation"] else "无独立正例验证"
    output.mkdir(parents=True)
    manifest_path = output.parent / "split-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    lines = [f"自动拆分 · {mode}"]
    for index, (video, stats) in enumerate(manifest["videos"].items(), 1):
        for side, label in (("train", "训练"), ("valid", "验证"), ("embargo", "间隔留空")):
            row = stats[side]
            lines.append(f"视频 {index} {label}  {row['images']} 张 · 正例 {row['positive']} 张"
                         f"（{row['positive_groups']} 组） · 正常 {row['normal']} 张 · {row['boxes']} 框"
                         f"  [{video}]")
    if limit is not None:
        lines.append("短训实际读取 " + " / ".join(f"{side} {len(rows)} 张" for side, rows in splits.items()))
    valid = [stats["valid"] for stats in manifest["videos"].values()]
    validation_summary = (f"正例 {sum(row['positive_groups'] for row in valid)} 组 / "
                          f"{sum(row['positive'] for row in valid)} 张 / {sum(row['boxes'] for row in valid)} 框")
    emit("split", mode=mode, validation_summary=validation_summary,
         detail="\n".join(lines), path=str(manifest_path))
    print("\n".join(lines), flush=True)
    print(f"Split manifest: {manifest_path}", flush=True)
    cats = summary["classes"]
    names = [category["name"] for category in cats]
    yolo = model == "yolo"
    with ZipFile(path) as archive:
        _, digest = read_manifest(archive)
        require(digest == summary["target_sha256"], "IDS changed after validation")
        for split, items in splits.items():
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
        return config, manifest
    return output, manifest
