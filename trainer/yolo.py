"""Ultralytics YOLOv8n adapter."""


def train(args, dataset, output, classes, evidence):
    from unittest.mock import patch

    import torch
    from ultralytics import YOLO
    from ultralytics.data import utils as data_utils
    from ultralytics.models.yolo.detect import DetectionTrainer

    class ObservedTrainer(DetectionTrainer):
        def optimizer_step(self):
            evidence.before(self.optimizer)
            super().optimizer_step()
            evidence.after()

    device = {"cpu": "cpu", "cuda": "0", "xpu": "xpu:0"}[args.device]
    model = YOLO(str(args.weights) if args.weights else "yolov8n.yaml")
    # The dataset check requests a plotting font even with plots disabled.
    with patch.object(data_utils, "check_font", return_value=None):
        model.train(trainer=ObservedTrainer, data=str(dataset), project=str(output), name="weights-yolo",
                    exist_ok=True, device=device, epochs=args.epochs, imgsz=args.size, batch=args.batch,
                    workers=0, amp=False, plots=False, mosaic=0.0, pretrained=bool(args.weights),
                    warmup_epochs=0, nbs=args.batch, deterministic=False, verbose=True)
    weights = output / "weights-yolo" / "weights" / "last.pt"
    checkpoint = torch.load(weights, map_location="cpu", weights_only=False)
    if checkpoint.get("model") is None:
        raise RuntimeError("YOLO checkpoint has no trained model")
    return weights
