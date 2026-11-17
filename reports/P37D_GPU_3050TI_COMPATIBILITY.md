# P3.7-D RTX3050Ti 4GB兼容性

日期：2026-10-19。**TARGET_3050TI=NOT TESTED；RF_3050TI_COMPATIBILITY_STATUS=NOT_TESTED。** 没有目标笔记本访问，Windows版本/驱动/磁盘/权限未知。i7-12700H、16GB RAM及4GB显存不能证明完整兼容。

## 本轮真实检查范围

`artifacts/p37d-20261019/developer-gpu-reference.json`：当前开发机Windows11 10.0.26200、RTX5070Ti、驱动617.42；既有独立RF环境Torch2.9.1+cu128、CUDA12.8。Torch导入2.511秒，编译架构列表包含sm_86及sm_120；实际设备计算能力12.0。CUDA小张量加法PASS，非CPU回退；没有加载RF模型，没有训练、梯度或优化器。

设备报告总显存17,066,033,152 bytes；上下文查询后可用15,767,437,312 bytes，小张量操作后15,706,619,904 bytes；Torch分配512 bytes、预留2,097,152 bytes。该可用显存差值含驱动上下文/其它活动，不能当RF模型开销，也不能线性外推目标4GB。没有测本轮模型前向、优化器峰值、系统RAM峰值或WDDM预算。

## 分层判定

| 能力 | RTX5070Ti开发环境 | 目标3050Ti / 候选包 |
|---|---|---|
| GUI启动 | 本轮源码原生回归PASS | NOT TESTED / 无候选 |
| Worker环境加载 | 既有RF Python可导入Torch；不是便携Worker | NOT TESTED |
| CUDA基本可用 | 本轮小张量PASS | NOT TESTED，必须在目标机实测驱动及所选wheel |
| 架构兼容 | 当前wheel含sm_86，提供可能兼容Ampere的线索 | 不能代替目标设备能力读取/实际核函数验证 |
| RF模型加载与前向 | 本轮未运行；P3.7-A历史证据保留为参考 | NOT TESTED |
| 显存足够 | 未测本轮训练峰值 | 未获证据，不准承诺Batch4或Batch1可用 |
| 允许启动训练 | 源码既有功能保留；没有本轮候选 | 目标未准入，不发带有“已兼容”标签的软件 |
| 视频/抽帧/标注CPU路径 | 源码14项PASS | 应独立于AI，仍待目标EXE验证 |

现行源码RF probe只给total_mib和小张量检查，没有完整新鲜可用显存、WDDM预算或4GB训练准入政策；现行默认Batch4也未针对目标验证。**本轮未修改该功能，不能声称已经在候选EXE实现4GB训练按钮禁用。** 这是交付阻断项，不靠文档替代代码门控。不得静默CPU AI回退。

## 恢复工程后的明确准入要求

1. 独立Worker不存在、公共权重不齐、驱动/架构不支持、总/可用显存信息缺失或4GB参数未经实测时，训练/AI推理按钮禁用；中文显示实际原因，例如“此4GB设备尚未通过RF-DETR显存验证，训练未启用；视频与人工标注仍可使用”。不要写成硬件绝对不支持。
2. 每次提交前重新读取设备UUID、驱动、compute capability、wheel的get_arch_list、cuda可用性和mem_get_info，并做最小CUDA检查；不得只使用长期缓存总显存。GUI检查、Worker加载、模型前向、显存、训练许可分项展示。
3. 内存估算须包含权重、激活、梯度、优化器状态、EMA、数据加载进程与Windows显示占用。16GB系统RAM不能补成16GB独立显存；WDDM共享内存不是训练可行保证。当前没有可靠峰值数据，不填估计数字冒充实测。
4. 如另有目标机测试条件，先离线视频流程和无CUDA路径，再经单独确认的小样本Batch1/低分辨率试验；不自动下载模型，不重复完整训练。OOM应退出并释放Worker，保留诊断且不阻断P0/P1。

目标测试需公司提供OS版本/SKU、现有驱动、可用磁盘、普通用户目录可写性及受控访问；不自动升级驱动或Windows配置。选定Torch/CUDA版本后核对准确驱动兼容要求，不把开发机617.42当目标最低要求。官方资料：[CUDA12.8发布说明](https://docs.nvidia.com/cuda/archive/12.8.0/cuda-toolkit-release-notes/index.html)、[get_arch_list](https://docs.pytorch.org/docs/main/generated/torch.cuda.get_arch_list.html)、[mem_get_info](https://docs.pytorch.org/docs/stable/generated/torch.cuda.memory.mem_get_info.html)。

最终携带NVIDIA DLL：N/A，无候选；逐DLL再分发仍BLOCKED，沿用P37L精确文件清单/EULA，不捆绑驱动。本轮没有得出需要购买AI Enterprise或其它商业许可的结论。
