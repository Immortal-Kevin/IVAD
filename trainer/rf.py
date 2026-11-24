"""RF-DETR Nano adapter using the upstream Lightning training components."""

from math import isfinite
from pathlib import Path

from early_stop import ValidationPatience
from events import emit, metrics, progress


def predictor(args):
    import torch
    from rfdetr import RFDETR, RFDETRNano
    from rfdetr.utilities.class_names import prediction_labels

    checkpoint = torch.load(args.weights, map_location="cpu", weights_only=False)
    if not isinstance(checkpoint, dict) or not isinstance(checkpoint.get("model"), dict):
        raise ValueError("权重不是 RF-DETR 原生检测 checkpoint")
    if "class_embed.weight" not in checkpoint["model"]:
        raise ValueError("RF-DETR 权重缺少检测分类头")
    del checkpoint
    model = RFDETR.from_checkpoint(args.weights, trust_checkpoint=True, device=args.device)
    if model.model_config.segmentation_head or model.model_config.use_grouppose_keypoints:
        raise ValueError("请选择 RF-DETR 检测权重")
    if not isinstance(model, RFDETRNano):
        raise ValueError(f"所选模型为 RF-DETR Nano，权重实际为 {type(model).__name__}。请选择 Nano 检测权重。")
    # Checkpoint deserialization starts on CPU even when the requested inference device differs.
    model.model.model.to(model.model.device)
    actual = next(model.model.model.parameters()).device
    if actual.type != args.device:
        raise RuntimeError(f"RF-DETR 选择了 {actual}，请求设备为 {args.device}")
    emit("weights", variant=type(model).__name__, resolution=model.model_config.resolution, device=str(actual))
    names = prediction_labels(model).class_id_to_name

    def predict(frame):
        result = model.predict(frame[:, :, ::-1].copy(), threshold=args.confidence,
                               shape=(args.size, args.size), include_source_image=False)
        # RF-DETR can return its no-object slot at low thresholds. Only IDs
        # from the checkpoint's foreground label map are valid detections.
        return [(box, ident, score) for box, ident, score in
                zip(result.xyxy.tolist(), result.class_id.tolist(), result.confidence.tolist())
                if ident in names]

    return names, predict


def train(args, dataset, output, classes, evidence, split):
    import torch
    from pytorch_lightning import Callback, seed_everything
    from pytorch_lightning.callbacks import Checkpoint
    from rfdetr.config import RFDETRNanoConfig, TrainConfig
    from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer

    validate = split["validation"]
    measured = {}
    patience = ValidationPatience() if validate and args.early_stop else None
    map_key = "val/mAP_50_95"
    destination = output / "weights-rfdetr"

    class Observe(Callback):
        epochs_completed = 0
        pending = None
        stopped = None

        def on_train_start(self, trainer, pl_module):
            loaded = {"train": data._dataset_train, "valid": data._dataset_val}
            for side, projection in loaded.items():
                expected = {frame + ".png" for frame in split["used"][side]}
                actual = [item["file_name"] for item in projection.coco.imgs.values()]
                expected_root = (dataset / side).resolve()
                if Path(projection.root).resolve() != expected_root or len(actual) != len(expected) or set(actual) != expected:
                    raise RuntimeError(f"RF-DETR {side} differs from the IDS split manifest")
            emit("dataset", train=len(split["used"]["train"]), valid=len(split["used"]["valid"]),
                 validation=validate, manifest="split-manifest.json")

        def on_train_epoch_start(self, trainer, pl_module):
            progress(trainer.current_epoch + 1, args.epochs, batches=trainer.num_training_batches)

        def on_train_epoch_end(self, trainer, pl_module):
            self.epochs_completed = trainer.current_epoch + 1

        def on_before_optimizer_step(self, trainer, pl_module, optimizer):
            evidence.before(optimizer)

        def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
            evidence.after()
            if batch_idx % 5 == 0 or batch_idx + 1 == trainer.num_training_batches:
                progress(trainer.current_epoch + 1, args.epochs, batch_idx + 1, trainer.num_training_batches)
                loss = float(outputs["loss"].detach())
                measured["loss"] = loss
                emit("metrics", values=measured)
                print(f"Epoch {trainer.current_epoch + 1}/{args.epochs}, step {trainer.global_step}, loss {loss:.5g}",
                      flush=True)

        def on_validation_epoch_start(self, trainer, pl_module):
            trainer.callback_metrics.pop(map_key, None)

        def on_validation_end(self, trainer, pl_module):
            raw = trainer.callback_metrics.get(map_key)
            score = None if raw is None else float(raw)
            if score is None or not isfinite(score) or not 0 <= score <= 1:
                # RF-DETR's best-checkpoint callback runs later and treats an absent metric as ineligible.
                trainer.callback_metrics.pop(map_key, None)
            for key in ("map", "map50", "recall"):
                measured.pop(key, None)
            measured.update(metrics(trainer.callback_metrics, {
                "map": (map_key,), "map50": ("val/mAP_50",),
                "recall": ("val/mAR", "val/AR_100"),
            }))
            emit("metrics", values=measured)
            if patience is None or trainer.sanity_checking:
                return
            status = patience.observe(trainer.current_epoch + 1, score)
            self.pending = status if status["reason"] else None
            print(f"自动早停 · 第 {status['epoch']} 轮 · 原始 mAP@50–95 {status['score'] or '缺失'} · "
                  f"最佳轮次 {status['best_epoch'] or '—'} · 耐心 {status['stale']}/{status['patience']} · "
                  f"连续零分 {status['zeros']}/{status['patience']}", flush=True)

    observer = Observe()

    class StopAfterCheckpoint(Checkpoint):
        def on_train_epoch_end(self, trainer, pl_module):
            if observer.pending is None:
                return
            # Lightning invokes checkpoint callbacks in order after the training epoch ends.
            saved = destination / f"checkpoint_{trainer.current_epoch}.ckpt"
            if not saved.is_file():
                raise RuntimeError(f"自动早停前未找到当轮权重：{saved.name}")
            observer.stopped = observer.pending
            print(f"自动早停 · {observer.stopped['reason']} · 已保存 {saved.name}", flush=True)
            trainer.should_stop = True

    seed_everything(42, workers=True)
    model_config = RFDETRNanoConfig(pretrain_weights=args.weights, resolution=args.size,
                                   num_classes=len(classes), device=args.device)
    config = TrainConfig(dataset_dir=dataset, output_dir=destination, epochs=args.epochs,
                         batch_size=args.batch, grad_accum_steps=1, num_workers=0, amp_dtype=None,
                         use_ema=False, multi_scale=False, scale_jitter=False, tensorboard=False,
                         progress_bar=None, checkpoint_interval=1, run_test=False,
                         eval_backend="faster_coco_eval", early_stopping=False, smooth_alpha=0,
                         class_names=[c["name"] for c in classes])
    accelerator = args.device
    strategy = {}
    if args.device == "xpu":
        from pytorch_lightning.strategies import SingleDeviceStrategy

        from rf_xpu import XPULightningAccelerator
        accelerator = XPULightningAccelerator()
        strategy["strategy"] = SingleDeviceStrategy(device=torch.device("xpu:0"))
    module = RFDETRModelModule(model_config, config, load_encoder_weights=False)
    data = RFDETRDataModule(model_config, config)
    if validate:
        strategy["extra_callbacks"] = [observer]
        if patience is not None:
            strategy["extra_callbacks"].append(StopAfterCheckpoint())
    else:
        strategy.update(callbacks=[observer], enable_checkpointing=False, limit_val_batches=0)
    runner = build_trainer(config, model_config, accelerator=accelerator, devices=1,
                           num_sanity_val_steps=0, **strategy)
    actual_device = runner.strategy.root_device
    if actual_device.type != args.device:
        raise RuntimeError(f"RF-DETR selected {actual_device} for requested {args.device}")
    print(f"RF-DETR training device: {actual_device}", flush=True)
    if args.device == "xpu":
        print("Lightning's GPU availability line refers to CUDA. This run uses Intel XPU.", flush=True)
    emit("stage", value="正在训练")
    runner.fit(module, data)
    last = destination / "checkpoint_last.pth"
    if validate:
        latest = destination / f"checkpoint_{observer.epochs_completed - 1}.ckpt"
    else:
        latest = last
        runner.save_checkpoint(latest, weights_only=True)
    saved = torch.load(latest, map_location="cpu", weights_only=False)
    native = {key: saved[key] for key in ("args", "model_name", "model_config", "rfdetr_version") if key in saved}
    native["model"] = {key.removeprefix("model."): value for key, value in saved["state_dict"].items()
                       if key.startswith("model.")}
    if not native["model"]:
        raise RuntimeError("RF-DETR last checkpoint has no trained model weights")
    torch.save(native, last)
    best = destination / "checkpoint_best_total.pth"
    weights = best if best.is_file() else last
    checkpoint = torch.load(weights, map_location="cpu", weights_only=False) if weights == best else native
    if not checkpoint.get("model"):
        raise RuntimeError("RF-DETR checkpoint has no trained model weights")
    completion = {"early_stop": observer.stopped, "epochs_completed": observer.epochs_completed,
                  "best_checkpoint": str(best.relative_to(output)) if weights == best else None,
                  "last_checkpoint": str(last.relative_to(output))}
    return weights, measured, completion
