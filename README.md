# IVAD Open Trainer v0.1

IVAD Open Trainer trains object detectors from full IVAD Annotator IDS 1.0 packages on Windows 11 x64. It supports YOLOv8n and RF-DETR Nano.

## Run

1. Extract the entire portable ZIP and double-click **IVAD Open Trainer.exe**.
2. Select an Annotator full `.ids` package, then click **Import / validate IDS**. The log shows fault class IDs, image and annotation counts, and the eligible training data.
3. Choose a model, device, image size, batch, epochs, and output folder. Start with CPU, 384 pixels and batch 1. Image size must be a multiple of 32.
4. To fine-tune, select a trusted local [YOLOv8n checkpoint](https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt) or [RF-DETR Nano checkpoint](https://repo.roboflow.com/rfdetr/nano_coco/checkpoint_best_regular.pth). An empty weights field starts from random initialization. Use only checkpoints you trust, since native checkpoints can carry serialized Python objects.
5. Click **Start training**. **Cancel** stops the background process and may leave a partial run. **Open output** opens the latest run directory. Successful runs contain a native `last.pt` or `checkpoint_best_total.pth`, plus a `result.json` with the checkpoint hash and measured parameter update.

Python and the CPU training dependencies are in the ZIP. Windows 11 supplies .NET Framework for the launcher. Microsoft C++ runtime libraries used by native wheels are an OS prerequisite. If they are missing, install the [Microsoft Visual C++ x64 Redistributable](https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist). The ZIP contains no pretrained checkpoints. The small `examples/synthetic.ids` fixture contains only generated images and local demonstration labels.

IDS is opened read-only. The trainer verifies the manifest checksum, asset list, asset checksums, image dimensions, annotation references and bounds. It uses confirmed normal frames as negatives and confirmed abnormal frames with active targets as positives. Detection boxes use the source coordinates, and polygons use their bounding rectangles. Stable fault IDs are recorded with the class list in each run. The validation split prefers distinct videos, with a temporal holdout when the eligible data comes from a single video. Temporal validation within a source is suitable for checking a training run. Use genuinely separate capture sessions to assess generalization. Incremental packages are pending. The import error reports the missing base fingerprint and directs you to an Annotator full export.

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
```

## Licenses

The Open Trainer is distributed under AGPL-3.0-only. See [LICENSE](LICENSE) and [THIRD-PARTY.md](THIRD-PARTY.md).
