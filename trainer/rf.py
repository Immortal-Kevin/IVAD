"""RF-DETR Nano adapter using the upstream Lightning training components."""


def train(args, dataset, output, classes, evidence):
    import torch
    from pytorch_lightning import Callback, seed_everything
    from rfdetr.config import RFDETRNanoConfig, TrainConfig
    from rfdetr.training import RFDETRDataModule, RFDETRModelModule, build_trainer

    class Observe(Callback):
        def on_before_optimizer_step(self, trainer, pl_module, optimizer):
            evidence.before(optimizer)

        def on_train_batch_end(self, trainer, pl_module, outputs, batch, batch_idx):
            evidence.after()
            if batch_idx % 10 == 0:
                loss = outputs["loss"].detach().item()
                print(f"Epoch {trainer.current_epoch + 1}/{args.epochs}, step {trainer.global_step}, loss {loss:.5g}",
                      flush=True)

    destination = output / "weights-rfdetr"
    seed_everything(42, workers=True)
    model_config = RFDETRNanoConfig(pretrain_weights=args.weights, resolution=args.size,
                                   num_classes=len(classes), device=args.device)
    config = TrainConfig(dataset_dir=dataset, output_dir=destination, epochs=args.epochs,
                         batch_size=args.batch, grad_accum_steps=1, num_workers=0, amp_dtype=None,
                         use_ema=False, multi_scale=False, scale_jitter=False, tensorboard=False,
                         progress_bar=None, checkpoint_interval=1, run_test=False,
                         eval_backend="faster_coco_eval", class_names=[c["name"] for c in classes])
    accelerator = {"cpu": "cpu", "cuda": "cuda", "xpu": "xpu"}[args.device]
    if args.device == "xpu":
        from rf_xpu import XPULightningAccelerator
        accelerator = XPULightningAccelerator()
    module = RFDETRModelModule(model_config, config, load_encoder_weights=False)
    data = RFDETRDataModule(model_config, config)
    runner = build_trainer(config, model_config, accelerator=accelerator, devices=1,
                           extra_callbacks=[Observe()], num_sanity_val_steps=0)
    runner.fit(module, data)
    weights = destination / "checkpoint_best_total.pth"
    checkpoint = torch.load(weights, map_location="cpu", weights_only=False)
    if not checkpoint.get("model"):
        raise RuntimeError("RF-DETR checkpoint has no trained model weights")
    return weights
