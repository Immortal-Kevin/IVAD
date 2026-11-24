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
from zipfile import BadZipFile

from ids import inspect_package, prepare, select_videos, write_plan
from events import emit


def options():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["inspect", "plan", "train", "video", "evaluate"])
    parser.add_argument("--ids", type=Path)
    parser.add_argument("--model", choices=["yolo", "rf", "anomaly"], default="yolo")
    parser.add_argument("--device", choices=["cpu", "xpu", "cuda"], default="cpu")
    parser.add_argument("--size", type=int, default=384)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=1)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--weights", type=Path)
    parser.add_argument("--video", type=Path)
    parser.add_argument("--confidence", type=float, default=0.25)
    parser.add_argument("--sample-fps", type=float, default=5)
    parser.add_argument("--seconds", type=float, help="Optional maximum source-video duration for verification")
    parser.add_argument("--preview", type=Path, help="Directory for two bounded preview JPEG files")
    parser.add_argument("--limit", type=int, help="Use at most this many images per split for short verification")
    parser.add_argument("--source-video", action="append", help="Retain this IDS video ID (repeat for multiple videos)")
    parser.add_argument("--early-stop", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--roi", nargs=4, type=float, default=(0, 0, 1, 1))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--evaluation-set", choices=["valid", "test"], default="test")
    return parser.parse_args()


def validate_size(args):
    if args.size < 64 or args.size % 32:
        raise ValueError("输入尺寸必须为不小于 64 的 32 的倍数")


def configure(run):
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


def device(args):
    import torch

    torch.set_num_threads(min(os.cpu_count() or 1, 8))
    if args.device != "cpu":
        backend = getattr(torch, args.device)
        if not backend.is_available():
            raise RuntimeError(f"{args.device.upper()} 无法使用（PyTorch {torch.__version__}）。请检查运行时和显卡驱动。")
        hardware = backend.get_device_name(0)
        actual = f"{args.device}:0"
    else:
        hardware, actual = "CPU", "cpu"
    emit("device", value=actual, hardware=hardware, runtime=torch.__version__)
    return torch


def train(args, plan_only=False):
    validate_size(args)
    if args.output is None:
        raise ValueError("请选择输出目录")
    if min(args.batch, args.epochs) < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("Batch Size、Epochs 和短训样本数必须大于零")
    args.weights = weights_path(args.weights, args.model) if args.weights else None
    run = args.output.resolve() / f"{args.model}-{args.device}-{uuid4().hex[:12]}"
    run.mkdir(parents=True)
    emit("stage", value="正在重新校验 IDS")
    summary, frames = load_ids(args)
    videos, frames = select_videos(summary, frames, args.source_video)
    emit("stage", value="正在准备训练数据")
    print(f"OUTPUT {run}", flush=True)
    mode = "anomaly" if args.model == "anomaly" else "detection"
    splits, split = write_plan(run, summary, frames, videos, mode, args.model, args.early_stop, args.limit)
    if plan_only:
        return
    if mode == "anomaly":
        from anomaly import fit
        emit("device", value="cpu", hardware="OpenCV / NumPy")
        fit(args, run, splits, split)
        return
    configure(run)
    torch = device(args)
    print(f"Model: {args.model}; device: {args.device}; PyTorch: {torch.__version__}; "
          f"size: {args.size}; batch: {args.batch}; epochs: {args.epochs}", flush=True)
    from evidence import UpdateEvidence

    dataset = prepare(args.ids, run / "dataset", args.model, summary, splits)
    adapter = importlib.import_module(args.model)
    evidence = UpdateEvidence(args.device)
    checkpoint, measured, completion = adapter.train(args, dataset, run, summary["classes"], evidence, split)
    if evidence.result is None:
        raise RuntimeError(f"No finite gradient and changed parameter observed on {args.device}")
    with checkpoint.open("rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    result = {"model": args.model, "device": args.device, "torch": torch.__version__,
              "checkpoint": str(checkpoint.relative_to(run)), "checkpoint_sha256": digest,
              "update": evidence.result, "ids": summary, "metrics": measured,
              "validation": split["validation"], "split_manifest": "split-manifest.json", **completion}
    (run / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    emit("checkpoint", path=str(checkpoint), model=args.model, metrics=measured, **completion)
    print(f"CHECKPOINT {checkpoint}\nSHA256 {digest}", flush=True)


def weights_path(path, model):
    suffix = {"yolo": ".pt", "rf": ".pth", "anomaly": ".npz"}[model]
    if path is None or not path.is_file() or path.suffix.lower() != suffix:
        raise ValueError(f"请选择与架构匹配的本地 {suffix} 权重文件")
    return path.resolve()


def load_ids(args):
    if args.ids is None or not args.ids.is_file():
        raise FileNotFoundError(f"IDS 文件不存在：{args.ids or '未选择文件'}")
    print("正在检查 IDS 清单、资产、图像和标注…", flush=True)
    try:
        summary, frames = inspect_package(args.ids)
    except BadZipFile as error:
        raise ValueError(f"IDS ZIP 损坏或格式不正确：{error}") from error
    emit("ids", summary=summary)
    return summary, frames


def main():
    args = options()
    if args.action in ("train", "plan"):
        train(args, plan_only=args.action == "plan")
    elif args.action == "evaluate":
        from evaluation import evaluate
        evaluate(args)
    elif args.action == "video":
        from video import verify
        verify(args)
    else:
        load_ids(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        emit("error", value=str(error) or type(error).__name__)
        traceback.print_exc()
        sys.exit(1)
