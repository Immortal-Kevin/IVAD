"""Generate an IDS example using drawn images."""

from hashlib import sha256
from io import BytesIO
import json
from pathlib import Path
import sys
from uuid import NAMESPACE_URL, uuid5
from zipfile import ZIP_DEFLATED, ZipFile

from PIL import Image, ImageDraw


def generate(destination):
    entities = []
    assets = {}

    def entity(key, kind, **data):
        identifier = str(uuid5(NAMESPACE_URL, "https://ivad.example/synthetic/" + key))
        entities.append(dict(id=identifier, kind=kind, revision=1, data=data))
        return identifier

    def asset(content, extension):
        name = f"assets/{sha256(content).hexdigest()}.{extension}"
        assets[name] = content
        return name

    site = entity("site", "Site", name="Synthetic site")
    project = entity("project", "Project", name="Synthetic example", site_id=site)
    equipment = entity("equipment", "Equipment", name="Drawn conveyor", project_id=project)
    fault = entity("fault", "Fault", name="Orange square", taxonomy_version=1)
    for group in range(2):
        camera = entity(f"camera-{group}", "Camera", name=f"Synthetic camera {group + 1}", equipment_id=equipment)
        frames = []
        for index in range(4):
            image = Image.new("RGB", (160, 128), (35 + 18 * group, 45, 55 + 11 * index))
            ImageDraw.Draw(image).rectangle((45 + 8 * index, 34, 79 + 8 * index, 68), fill=(250, 142, 40))
            frames.append(image)
        buffer = BytesIO()
        frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:], duration=500)
        video = entity(f"video-{group}", "Video", camera_id=camera, asset_path=asset(buffer.getvalue(), "gif"),
                       original_name=f"drawn-{group}.gif")
        for index, image in enumerate(frames):
            ident = f"{group}-{index}"
            buffer = BytesIO()
            image.save(buffer, format="PNG")
            frame = entity("frame-" + ident, "Frame", video_id=video, width=160, height=128,
                           asset_path=asset(buffer.getvalue(), "png"), pts_us=index * 500_000,
                           source_timestamp_100ns=index * 5_000_000, time_source="media_foundation_sample",
                           decode_index=index, sampling_interval_seconds=0.5, state="abnormal")
            entity("annotation-" + ident, "Annotation", frame_id=frame, fault_id=fault, shape="box",
                   points=[45 + 8 * index, 34, 80 + 8 * index, 69], coordinate_space="source_pixels")
            entity("review-" + ident, "Review", frame_id=frame, status="confirmed", reviewer="synthetic",
                   utc="2026-01-01T00:00:00Z")

    entries = [dict(path=path, sha256=sha256(data).hexdigest(), bytes=len(data)) for path, data in assets.items()]
    doc = json.dumps(dict(schema="ids/1.0", project_id=project, sequence=1, entities=entities,
                          assets=entries), separators=(",", ":")).encode()
    envelope = dict(format="ids-package/1.0", mode="full", base_sha256=None,
                    target_sha256=sha256(doc).hexdigest(), included_assets=list(assets))
    with ZipFile(destination, "w", ZIP_DEFLATED) as archive:
        archive.writestr("package.json", json.dumps(envelope))
        archive.writestr("document.json", doc)
        for path, content in assets.items():
            archive.writestr(path, content)


if __name__ == "__main__":
    generate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).with_name("synthetic.ids"))
