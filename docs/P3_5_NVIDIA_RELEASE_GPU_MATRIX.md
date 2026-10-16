# P3.5 NVIDIA 展示版兼容性预审

2026-10-16。**安装包未生成，以下不构成安装版兼容认证。**

|硬件/系统|源码历史验证|本轮安装包等级|
|---|---|---|
|RTX5070Ti / 当前Windows11|VERIFIED，仅历史P0–P3.5真实训练、模型注册和离线推理范围|NOT TESTED，没有Setup可启动|
|RTX20/30/40/其他50及RTX专业卡|其他实机NOT TESTED|NOT TESTED；未据5070Ti推断全部通过|
|Windows10 x64|NOT TESTED|NOT TESTED|
|Windows11其他机器/干净系统|NOT TESTED|NOT TESTED|
|Intel/非NVIDIA后端|不属于本次NVIDIA包目标，历史Intel独立验收未完成|不声明支持|

本轮只读设备核实：RTX5070Ti，Compute Capability12.0，驱动617.42；nvidia-smi总显存16303MiB；PyTorch2.9.1+cu128/CUDA12.8，设备属性总显存17066033152字节；torch编译列表sm_70/75/80/86/90/100/120。枚举/架构列表不能替代模型前向、后向、ORT节点及视频测试。

VERIFIED仅用于已实际完成的指定测试；SUPPORTED BY DEPENDENCIES需官方依赖/架构及最终发行清单证据，当前未对任何整机安装组合授予此结论；NOT TESTED不能写成UNSUPPORTED，UNSUPPORTED只用于有明确不兼容证据者。

本次没有重训、没有完整P0基准、没有安装版CUDA测试；历史真实训练/推理证据见reports/P0_NVIDIA_ACCEPTANCE.md、P3_TRAINING_RESULTS.md、P3_MODEL_VALIDATION.md。未来发行需保持GPU-only AI，无可用后端时仅GUI/诊断可用，不修改驱动或自动降级CPU。
