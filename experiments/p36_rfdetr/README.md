# P3.6 独立 RF-DETR Nano 实验

这是可行性原型，不是正式 IVAD 后端。禁止直接在 GUI/Registry 注册；`PACKAGING_FREEZE=TRUE`。

## 运行边界

使用仓库 `.venv-rfdetr/Scripts/python.exe -I -X utf8` 执行本目录脚本。不得改用 `.venv-nvidia`，不得安装 Ultralytics/Plus；`assert_isolated` 检查该边界。CPU 仅用于图片解码、数据预处理、匈牙利匹配/指标和序列化，神经网络训练与推理必须 CUDA，失败不降级。

命令示例（由开发者执行，路径应使用本轮唯一输出目录）：

```text
python -I -X utf8 experiments/p36_rfdetr/export_coco.py <冻结manifest> <独立COCO副本目录>
python -I -X utf8 experiments/p36_rfdetr/probe.py <官方Nano权重> <测试图> <新输出目录>
python -I -X utf8 experiments/p36_rfdetr/train.py <实验request.json>
python -I -X utf8 experiments/p36_rfdetr/evaluate.py <最佳权重> <COCO副本目录> <新输出目录>
python -I -X utf8 experiments/p36_rfdetr/export_onnx.py <最佳权重> <新输出目录>
```

本轮实际命令参数、pip 来源/归档哈希与锁定版本保存于 `artifacts/p36-rfdetr-20261016`，验收以报告和原始日志为准。示例 `python` 必须替换为上面的独立环境绝对路径，不能使用全局 Python。

## 最小 Backend Adapter 契约

| 能力 | 原型入口 | 边界 |
|---|---|---|
| 身份、后端与设备 | NanoAdapter.backend，实验权重 SHA256 | 实验身份独立，显式 CUDA，不用正式模型 UUID 冒名 |
| 加载/恢复 | NanoAdapter(weights)、restore(checkpoint) | 官方 RF-DETR API，原文件只读；不使用 YOLO PT/ONNX |
| 数据验证 | validate_dataset；export_coco | 保留原类别 ID/UUID、正常样本及来源；拒绝多边形偷转框 |
| 训练/日志/状态 | train.py；TrainingJob.start/status | 独立请求、子进程、日志、experiment-result.json；不写业务数据库 |
| 取消 | TrainingJob.cancel | 写请求旁的 .cancel.request；也识别输出目录cancel.request，在 batch 边界保存 cancelled.ckpt 并终止；不是任意时刻硬杀。启动前及训练中取消均实际验证 |
| 保存/恢复 | 官方 epoch/checkpoint/best 权重及 restore | RF 专有实验目录，与历史模型版本隔离 |
| 图片/批量推理 | NanoAdapter.predict(image 或 image list) | 输出真实 supervision.Detections，不合成预测；正常/异常双图批量已实际验证 |
| 通用输出 | convert | 原图像素 xyxy、class_id/name、confidence、frame/camera/media/time/model 标识；空输出合法 |
| 导出 | export/export_onnx.py | 官方导出、checker、实际 ORT 节点证据；不因 Provider 可见就报告 GPU PASS |
| 错误 | 异常、子进程退出码与 JSON | 保存失败不登记模型，不伪报成功 |

RF-DETR 使用其自身查询预测/后处理，不能套用旧 YOLO 原始张量/NMS 解码。官方 COCO 预训练类别 ID 是稀疏 COCO ID；微调后的类别按独立数据集映射，二者必须区分。

结果转换显式区分背景槽与未知类别，过滤并记录零面积预测，对有效预测框裁至原图边界并保留raw_xyxy。真值转换仍严格拒绝越界/无效框，不能把预测后处理规则用于修改人工真值。

## P3/P3.5 兼容设计（未接入）

数据层可继续采用冻结 manifest 与原始人工像素标注。单摄像头多故障可用多类别模型或多个独立模型版本，需用户确认产品策略。追加图片必须创建新草稿/冻结版本与新实验，不能改历史冻结版本。实验/候选/生产状态与回滚可使用未来通用 Registry 元数据，但本轮不写入任何正式状态。

独立结果含视频相对 time_us、Frame/Camera/Media 身份、类别、置信度、原像素框与实验权重身份。此格式有独立 schema，不能伪装为既有 `ivad-offline-demo-v1` 已验证缓存。

现有 schema2 缓存身份明确包含 `p35-pil-rgb-ultralytics-v1`、imgsz640、Ultralytics NMS、Worker/服务/解码器/环境哈希。正式接入需新增 backend/architecture/preprocess/postprocess/class-map/weight-hash 的缓存身份与适配，不得复用旧 YOLO 检测缓存作为 RF 预测。预测语义能映射不等于旧缓存可直接使用。

P4 的 ROI 过滤、连续帧持续时间、多模型和 RTSP 输入可消费通用预测，但还需要调度、时钟、丢帧、规则及报警验收。本轮不实现这些功能。
