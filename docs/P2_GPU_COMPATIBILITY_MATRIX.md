# P2 Beta NVIDIA 兼容性矩阵

核查日期：2026-10-14。仅 RTX 5070 Ti 有 P0 实机 CUDA／双模型证据。P2 Lite 不包含 GPU Worker、PyTorch、ORT 或权重，以下静态矩阵不表示发行包执行过 AI。

## 固定基线和状态定义

当前本机读取：Windows 11 26200；Python 3.12.14；torch 2.9.1+cu128；CUDA runtime 12.8；cuDNN 9.10.2；ORT GPU 1.24.4；RTX 5070 Ti CC 12.0，驱动 617.42。`torch.cuda.get_arch_list()`：sm_70、sm_75、sm_80、sm_86、sm_90、sm_100、sm_120。证据：`artifacts/p2-distribution/current-gpu-metadata.json`，原始 P0 证据不替换。

- STATICALLY COMPATIBLE：官方计算能力与构建架构有可说明的兼容路径，仍未实测。
- REQUIRES VALIDATION：具体机器／驱动／显存／算子／模型尚需真实测试。
- UNSUPPORTED：当前包明确拒绝相应能力。
- NOT TESTED：未执行该机器或后端的真实测试。
- PASS 仅用于原 RTX 5070 Ti 的既有 P0 测试范围，不能扩展为生产或跨机器 PASS。

## 矩阵

| 系列或具体产品 | NVIDIA 官方 CC | 当前 torch 构建路径 | 静态结论 | 实机状态 |
| --- | --- | --- | --- | --- |
| RTX 2060、2070、2080、2080 Ti | 7.5 | sm_75 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX 3050、3060、3070、3080、3090（官方列出的 Ti 变种亦同组） | 8.6 | sm_86 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX 4050、4060、4070、4080、4090 | 8.9 | sm_86 对同 major 更高 minor 的兼容；本构建没有独立 sm_89 项 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX 5070 Ti | 12.0 | sm_120 原生 | STATICALLY COMPATIBLE | 仅此卡 P0 CUDA、YOLO26n/YOLO11n PASS |
| RTX 5050、5060、5060 Ti、5070、5080、5090 | 12.0 | sm_120 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| Quadro RTX 3000、4000、5000、6000、8000 | 7.5 | sm_75 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX A2000、A3000、A4000、A5000、A6000 | 8.6 | sm_86 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX 2000/4000/4500/5000/6000 Ada（官方列出的 SFF 变种） | 8.9 | 同 major cubin 兼容路径 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| RTX PRO 2000/4000/4500/5000/5500/6000 Blackwell（官方表列型号） | 12.0 | sm_120 原生 | STATICALLY COMPATIBLE | NOT TESTED / REQUIRES VALIDATION |
| 不在官方表中明确匹配的笔记本／OEM／其他变种 | 不推测 | 逐型号检查 | REQUIRES VALIDATION | NOT TESTED |
| 任意硬件上的 P2 Lite AI 训练／推理 | 不适用 | 未捆绑 Worker | UNSUPPORTED | 始终拒绝，包括 CPU-only fallback |
| Intel GPU AI 后端 | 不使用 NVIDIA CC | 尚未实现 | UNSUPPORTED（本 Lite 的 AI 能力） | 独立历史 BLOCKED，非 NVIDIA 测试结论 |

计算能力来源：[NVIDIA 官方 GPU 表](https://developer.nvidia.com/cuda/gpus)。同 major／更高 minor 的 cubin 兼容规则参考 [NVIDIA CUDA 平台说明](https://docs.nvidia.com/cuda/cuda-programming-guide/01-introduction/cuda-platform.html)。系列名称仅作为导航，具体型号必须在官方表核对；不模拟改名验证。

## 驱动和运行库条件

CUDA 12.x 的 Windows minor compatibility 底线为 528.33，但存在新特性／PTX限制，不能把这一下限当成所有 RTX 50 和 CUDA 12.8 功能均可运行。CUDA 12.8 GA 的对应 Windows 驱动为 570.65；还必须满足具体显卡上市后的官方驱动支持。实际基线为 617.42，不降级、不自动更新驱动。参考 [CUDA 12.8 发布说明](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html) 和 [minor compatibility 限制](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html)。

ORT 1.24.4 CUDA 包属 CUDA 12.8／cuDNN 9 路径；CUDA EP 的 DLL 依赖与 cuDNN major 要匹配。原 P0 用 PyTorch 运行时与 DLL preload，并检查了真实节点 provider。仅枚举 CUDAExecutionProvider 不代表节点实际在 GPU 执行；CPUExecutionProvider 注册亦不等于发生过降级。另建 GPU Worker 时仍需严格禁用 CPU 节点 fallback 并保留 profile，不能凭张量测试宣称 YOLO 已通过。参考 [ORT 官方 CUDA EP](https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html)。

显存不存在本轮认证的统一最低值：模型、精度、输入尺寸、batch、优化器、CUDA/cuDNN工作区与其他程序都会影响占用。原 P0 只有 16GB 卡的指定测试，不能承诺 6GB／8GB 卡以相同训练参数工作。实际测试时记录总／空闲显存与 OOM；不足时拒绝或由用户调整 GPU 参数，绝不转 CPU AI。

## 硬编码与诊断

业务执行未硬编码 RTX 5070 Ti 名称、唯一 UUID 或设备编号；GPU选择来自当前探测设备。旧 P0 验证匹配会核对型号、UUID、驱动与运行库，是历史证据匹配，不限制新卡被探测为可用；新卡没有匹配证据必须显示未验证。当前 P2 Lite 无论设置中保存什么 Worker 路径均不会加载它。

Lite GUI 的“检测NVIDIA硬件（不验证AI）”只调用已安装驱动的 nvidia-smi；读取型号、显存、驱动和驱动能报告的计算能力。没有 nvidia-smi 时显示未验证，不修改驱动、不扫描其他磁盘、不下载 CUDA。Worker Installed=False，CUDA／模型测试 NOT TESTED。

本轮没有第二块真实 NVIDIA GPU，没有通过其他电脑或 VM 的 CUDA 测试。请填写随包兼容性反馈表，不得把静态行改写为 PASS。
