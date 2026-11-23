"""RF-DETR Nano adapter using the upstream Lightning training components."""

from events import emit, metrics, progress


def predictor(args):
    import torch
    from rfdetr import RFDETR
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
    actual = next(model.model.model.parameters()).device
    if actual.type != args.device:
        raise RuntimeError(f"RF-DETR 选择了 {actual}，请求设备为 {args.device}")
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


def train(args, dataset, output, classes, evidence, validate):
    import torch
    from pytorch_lightning import Callback, seed_everything
    from rfdetr.config import RFDETRNanoConfig, TrainConfig
    from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer

    measured = {}

    class Observe(Callback):
        def on_train_epoch_start(self, trainer, pl_module):
            progress(trainer.current_epoch + 1, args.epochs, batches=trainer.num_training_batches)

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

        def on_validation_end(self, trainer, pl_module):
            measured.update(metrics(trainer.callback_metrics, {
                "map": ("val/mAP_50_95",), "map50": ("val/mAP_50",),
                "recall": ("val/mAR", "val/AR_100"),
            }))
            emit("metrics", values=measured)

    destination = output / "weights-rfdetr"
    seed_everything(42, workers=True)
    model_config = RFDETRNanoConfig(pretrain_weights=args.weights, resolution=args.size,
                                   num_classes=len(classes), device=args.device)
    config = TrainConfig(dataset_dir=dataset, output_dir=destination, epochs=args.epochs,
                         batch_size=args.batch, grad_accum_steps=1, num_workers=0, amp_dtype=None,
                         use_ema=False, multi_scale=False, scale_jitter=False, tensorboard=False,
                         progress_bar=None, checkpoint_interval=1, run_test=False,
                         eval_backend="faster_coco_eval", class_names=[c["name"] for c in classes])
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
        strategy["extra_callbacks"] = [Observe()]
    else:
        strategy.update(callbacks=[Observe()], enable_checkpointing=False, limit_val_batches=0)
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
    weights = destination / ("checkpoint_best_total.pth" if validate else "checkpoint_last.pth")
    if not validate:
        runner.save_checkpoint(weights, weights_only=True)
        checkpoint = torch.load(weights, map_location="cpu", weights_only=False)
        checkpoint["model"] = {key.removeprefix("model."): value for key, value in checkpoint["state_dict"].items()
                               if key.startswith("model.")}
        torch.save(checkpoint, weights)
    else:
        checkpoint = torch.load(weights, map_location="cpu", weights_only=False)
    if not checkpoint.get("model"):
        raise RuntimeError("RF-DETR checkpoint has no trained model weights")
    return weights, measured
