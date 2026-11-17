# IVAD NVIDIA 源码

本分支提供 IVAD 的 NVIDIA CUDA RF-DETR Nano 训练、Windows 媒体适配和用于验证的 Qt 源码入口。项目使用 Python 3.12。依赖应装在项目专用环境中，模型需从经核实的来源独立准备。

- 源码启动可用 `python -m ivad_app --data-dir <独立数据目录>`。
- 固定 RF-DETR 版本与迁移证据见 [YOLO 到 RF-DETR](docs/NVIDIA_YOLO_TO_RF_DETR.md)；独立及集成的模型接口见 [训练后端契约](docs/P37_A_BACKEND_CONTRACT.md)。
- 旧 YOLO 代码和实验参数见 [历史归档](archive/yolo/README.md)。当前训练依赖 RF-DETR。
- [第三方声明](NOTICE.md)、[遥测清理](docs/TELEMETRY_REMOVAL.md)、[本地保留索引](docs/LOCAL_ASSET_INDEX.md)。
