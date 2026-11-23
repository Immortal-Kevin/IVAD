# Third-party notices

The Open Trainer uses the publicly documented IVAD IDS 1.0 wire format and follows the Annotator projection rules for reviewed frames. The IDS specification and original IVAD Annotator IDS implementation carry the IVAD contributors' Apache-2.0 notice. The open trainer implements its own read-only reader and has no dependency on the NVIDIA platform.

| Component | Version and license | Upstream source |
| --- | --- | --- |
| Ultralytics YOLO and YOLOv8 model definitions | 8.4.176, AGPL-3.0-only | [Ultralytics release source](https://github.com/ultralytics/ultralytics/tree/v8.4.176) |
| RF-DETR | 1.12.1, Apache-2.0 | [Roboflow RF-DETR source](https://github.com/roboflow/rf-detr/tree/1.12.1) |
| CPython (embedded x64 distribution) | 3.12.10, PSF and bundled-component terms | [CPython 3.12.10 source](https://www.python.org/downloads/release/python-31210/) |
| PyTorch / TorchVision CPU | 2.12.1 / 0.27.1, BSD-3-Clause and bundled-component terms | [PyTorch](https://github.com/pytorch/pytorch/tree/v2.12.1), [TorchVision](https://github.com/pytorch/vision/tree/v0.27.1) |
| OpenCV Python | Pinned in the runtime requirements file, Apache-2.0 and bundled-component terms | [OpenCV Python source and build tooling](https://github.com/opencv/opencv-python) |

The portable package includes the release source and build scripts, the Python license, distribution metadata, upstream URLs and license files from the wheels. See `RUNTIME-INVENTORY.txt`, `requirements-win-cpu.txt`, `runtime/LICENSE.txt`, and `licenses/runtime`. If needed, the published versioned source archives can also be selected via the matching releases on [PyPI](https://pypi.org/). The package omits the OpenCV FFmpeg video I/O plugin, an unrelated TorchMetrics image-similarity checkpoint, and a setuptools test archive. The trainer reads frame images already exported in IDS.

Optional Intel and NVIDIA runtime components are fetched directly from the official PyTorch indexes by the opt-in install script. They retain their upstream terms. The CPU ZIP carries no Intel or NVIDIA GPU runtime or pretrained weights.
