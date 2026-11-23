"""Ultralytics YOLOv8n adapter."""

from events import emit, metrics, progress


def detector(path):
    from ultralytics import YOLO
    from ultralytics.nn.tasks import yaml_model_load

    try:
        model = YOLO(str(path))
    except Exception as error:
        raise ValueError(f"无法读取 YOLOv8 检测权重：{error}") from error
    config = model.model.yaml
    reference = yaml_model_load("yolov8n.yaml")
    if model.task != "detect" or any(config.get(key) != reference[key] for key in ("backbone", "head")):
        raise ValueError("权重不是 YOLOv8 检测模型")
    return model


def predictor(args):
    model = detector(args.weights)
    device = {"cpu": "cpu", "cuda": "0", "xpu": "xpu:0"}[args.device]

    def predict(frame):
        result = model.predict(frame, imgsz=args.size, conf=args.confidence, device=device, verbose=False)[0]
        actual = model.predictor.device
        if actual.type != args.device:
            raise RuntimeError(f"YOLOv8 选择了 {actual}，请求设备为 {args.device}")
        data = result.boxes
        return list(zip(data.xyxy.cpu().tolist(), data.cls.int().cpu().tolist(), data.conf.cpu().tolist()))

    return model.names, predict


def train(args, dataset, output, classes, evidence):
    import math
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
    measured = {}
    batches = [0]

    def begin(trainer):
        actual = trainer.device
        if actual.type != args.device:
            raise RuntimeError(f"YOLOv8 选择了 {actual}，请求设备为 {args.device}")
        emit("stage", value="正在训练")

    def epoch(trainer):
        batches[0] = 0
        progress(trainer.epoch + 1, args.epochs, batches=len(trainer.train_loader))

    def batch(trainer):
        batches[0] += 1
        if batches[0] % 5 == 0 or batches[0] == len(trainer.train_loader):
            progress(trainer.epoch + 1, args.epochs, batches[0], len(trainer.train_loader))

    def validation(trainer):
        if trainer.tloss is not None:
            loss = math.fsum(trainer.label_loss_items(trainer.tloss).values())
            if math.isfinite(loss):
                measured["loss"] = loss
        measured.update(metrics(trainer.metrics or {}, {
            "map50": ("metrics/mAP50(B)",), "map": ("metrics/mAP50-95(B)",),
            "precision": ("metrics/precision(B)",), "recall": ("metrics/recall(B)",),
        }))
        emit("metrics", values=measured)

    model = detector(args.weights) if args.weights else YOLO("yolov8n.yaml")
    model.add_callback("on_train_start", begin)
    model.add_callback("on_train_epoch_start", epoch)
    model.add_callback("on_train_batch_end", batch)
    model.add_callback("on_fit_epoch_end", validation)
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
    return weights, measured
