"""Background worker invoked by IVAD Open Trainer.exe."""

import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import traceback
from uuid import uuid4

from ids import inspect_package, prepare


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "train"])
    parser.add_argument("--ids", required=True, type=Path)
    parser.add_argument("--model", choices=["yolo", "rf"], default="yolo")
    parser.add_argument("--device", choices=["cpu", "xpu", "cuda"], default="cpu")
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--limit", type=int, help="Use at most this many images per split for short verification")
    return parser.parse_args()


def train(args, summary, frames):
    if args.output is None:
        raise ValueError("Select an output folder")
    if args.size < 64 or args.size % 32:
        raise ValueError("Image size must be a multiple of 32 and at least 64")
    if min(args.batch, args.epochs) < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("Batch, epochs and short-run limit must be positive")
    if args.weights:
        args.weights = args.weights.resolve(strict=True)
        suffixes = {".pt"} if args.model == "yolo" else {".pth"}
        if not args.weights.is_file() or args.weights.suffix.lower() not in suffixes:
            raise ValueError(f"Select a trusted local {', '.join(sorted(suffixes))} weight file")

    run = args.output.resolve() / f"{args.model}-{args.device}-{uuid4().hex[:12]}"
    run.mkdir(parents=True)
    print(f"OUTPUT {run}", flush=True)
    yolo_settings = run / "ultralytics-settings"
    yolo_settings.mkdir()
    os.environ["YOLO_CONFIG_DIR"] = str(yolo_settings)
    os.environ["YOLO_AUTOINSTALL"] = "false"
    os.environ["YOLO_OFFLINE"] = "true"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
    os.environ["WANDB_MODE"] = "disabled"
    os.environ["MPLCONFIGDIR"] = str(run / "matplotlib")
    os.environ["NO_COLOR"] = "1"
    import torch

    torch.set_num_threads(min(os.cpu_count() or 1, 8))
    if args.device != "cpu":
        backend = getattr(torch, args.device)
        if not backend.is_available():
            raise RuntimeError(f"{args.device.upper()} is unavailable with PyTorch {torch.__version__}. "
                               "Check the matching portable runtime and graphics driver.")
        print(f"Hardware: {backend.get_device_name(0)}", flush=True)
    print(f"Model: {args.model}; device: {args.device}; PyTorch: {torch.__version__}; "
          f"size: {args.size}; batch: {args.batch}; epochs: {args.epochs}", flush=True)
    from evidence import UpdateEvidence

    dataset = prepare(args.ids, run / "dataset", args.model, summary, frames, args.limit)
    adapter = importlib.import_module(args.model)
    evidence = UpdateEvidence(args.device)
    checkpoint = adapter.train(args, dataset, run, summary["classes"], evidence)
    if evidence.result is None:
        raise RuntimeError(f"No finite gradient and changed parameter observed on {args.device}")
    with checkpoint.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {"model": args.model, "device": args.device, "torch": torch.__version__,
              "checkpoint": str(checkpoint.relative_to(run)), "checkpoint_sha256": digest,
              "update": evidence.result, "ids": summary}
    (run / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"CHECKPOINT {checkpoint}\nSHA256 {digest}", flush=True)


def main():
    args = options()
    print("Checking IDS archive, assets, images and annotations...", flush=True)
    summary, frames = inspect_package(args.ids)
    print("IDS " + json.dumps(summary, ensure_ascii=False), flush=True)
    if args.action == "train":
        train(args, summary, frames)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        traceback.print_exc()
        sys.exit(1)
