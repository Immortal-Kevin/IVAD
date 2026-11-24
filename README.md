# IVAD Open Trainer v0.2

IVAD Open Trainer trains object detectors from full IVAD Annotator IDS 1.0 packages on Windows 11 x64. It supports YOLOv8n and RF-DETR Nano.

## Run

1. Extract the entire portable ZIP and double-click **IVAD Open Trainer.exe**.
2. In **IDS 选取与导入**, select a project preset and import the full Annotator `.ids` export. A successful import binds the package to this local project and displays the actual class and image counts.
3. In **项目训练**, choose a model, device, image size, batch, epochs, and output folder. Start with CPU, 384 pixels and batch 1. Image size must be a multiple of 32.
4. To fine-tune, select a trusted local [YOLOv8n checkpoint](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt) or [RF-DETR Nano checkpoint](https://repo.roboflow.com/rfdetr/nano_coco/checkpoint_best_regular.pth). An empty weights field starts from random initialization. Use only checkpoints you trust, since native checkpoints can carry serialized Python objects.
5. Click **开始训练**. **取消训练** stops the background process and may leave a partial run. The monitor uses actual framework events to show epoch, batch and metrics. **模型导出** copies a successfully completed native `last.pt` or `checkpoint_best_total.pth`. Each successful run also writes a local `result.json` with metrics, the checkpoint hash and measured parameter update.
6. In **训练视频验证**, select the current project's generated checkpoint or a trusted local weight file. Choose a supported local video, device, input size, confidence threshold and maximum verification FPS. **保存项目预设** keeps the settings for that project. The playback preview and detection view update separately. The latest-frame queue holds at most one pending inference frame. Source FPS and measured inference FPS are reported separately.

Project bindings and presets are stored in `%LOCALAPPDATA%\IVAD Open Trainer\projects.json`. On first launch, the **刮板机机头** preset is ready for a local IDS binding. The video decoder uses Windows Media Foundation, with a Motion JPEG AVI fallback. Supported video formats depend on the codecs available in Windows.

Python and the CPU training dependencies are in the ZIP. Windows 11 supplies .NET Framework for the launcher. Microsoft C++ runtime libraries used by native wheels are an OS prerequisite. If they are missing, install the [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). The ZIP contains no pretrained checkpoints. The small `examples/synthetic.ids` fixture contains only generated images and local demonstration labels.

IDS is opened read-only. The trainer verifies the manifest checksum, asset list, asset checksums, image dimensions, annotation references and bounds. It uses confirmed normal frames as negatives and confirmed abnormal frames with active targets as positives. Detection boxes use the source coordinates, and polygons use their bounding rectangles. Stable fault IDs are recorded with the class list in each run. Automatic splitting holds out temporal groups within reliably ordered source videos and leaves a gap around each holdout. Each run records its assignments, exclusions and actual image lists in `split-manifest.json`. If no positive group can be held out, the trainer saves the final checkpoint without validation mAP. Held-out normals can still be evaluated for false alarms. Same-source holdouts are useful for checking a run. Use separate capture sessions to assess generalization. Incremental packages are pending. The import error reports the missing base fingerprint and directs you to an Annotator full export.

## Train, validation and test

Choose the source videos on the IDS page, then choose the mode on the training page. The trainer records three disjoint temporal holdouts in `split-manifest.json` before fitting. Box detection trains YOLOv8n or RF-DETR on Train. Use the video page to evaluate Val while tuning, then evaluate Test after the checkpoint and confidence threshold are fixed. A holdout without positive annotations can report false positives but cannot report mAP or recall.

Normal-sample anomaly detection fits a local OpenCV/NumPy appearance model on confirmed-normal Train frames. It calibrates the threshold on separate confirmed-normal Val frames and then plays back Test to count known event hits and false-alarm episodes on normal clips. Set the ROI as normalized left, top, right, bottom coordinates, or keep the default full frame. The native `.npz` model stores the fixed ROI and threshold for video playback with scores, heatmaps and suspected anomaly boxes. Replay time reflects sampled IDS frame coverage rather than the full source-video runtime.

## GPU runtimes

The CPU ZIP can be extended from PowerShell in its extracted folder. These commands install the pinned upstream device runtime locally beside the EXE.

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\install-gpu.ps1 -Backend xpu
powershell -ExecutionPolicy Bypass -File .\scripts\install-gpu.ps1 -Backend cuda
```

Select the matching device in the EXE. An unavailable device produces an error. The CUDA profile uses PyTorch CUDA 13.0. For supported CUDA devices with limited memory, start with batch 1 and a low resolution. CUDA compatibility depends on the wheel, driver and GPU compute capability.

## Build from source

On Windows 11 x64, use Git, Windows PowerShell or PowerShell 7, and a builder Python with pip 22.3 or newer. From a clean checkout, run:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\build.ps1
```

The script verifies the official CPython embedded archive, installs the version-pinned runtime, compiles the .NET Framework WinForms launcher with the Windows C# compiler and creates the ZIP and SHA-256 under `dist`. The ZIP includes the release source and its commit ID. No builder Python installation is needed on the target. The optional `-PreparedRuntime` argument accepts a matching locally prepared runtime for rebuilds.

For automated checks, call the same EXE with arguments and wait for its exit code. The optional `--limit` caps the number of images per split after validating the complete IDS.

```text
"IVAD Open Trainer.exe" inspect --ids "examples/synthetic.ids"
"IVAD Open Trainer.exe" train --ids "examples/synthetic.ids" --model rf --device cpu --size 128 --batch 1 --epochs 1 --output "runs" --limit 2
"IVAD Open Trainer.exe" video --model yolo --device cpu --weights "runs/detector.pt" --video "test.mp4" --size 384 --confidence 0.25 --sample-fps 5
```

## Licenses

The Open Trainer is distributed under AGPL-3.0-only. See [LICENSE](LICENSE) and [THIRD-PARTY.md](THIRD-PARTY.md).
