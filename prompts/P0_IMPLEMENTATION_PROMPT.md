# IVAD Platform v1.0 — P0-NVIDIA 实机兼容性验证实施指令

> 本文件适用于 NVIDIA RTX 5070 Ti（Windows 11）首要开发主线。请在已阅读 `docs/SRS.md`、`docs/ARCHITECTURE.md`、`prompts/CODEX_MASTER_PROMPT.md` 后执行。仅 P0，无 GUI/P1 开发。

## 目标与边界
- 实测 RTX 5070 Ti 的 PyTorch CUDA 训练与 ONNX Runtime CUDA 推理，比较 YOLO26n 和 YOLO11n，选择 **NVIDIA 后端** 的默认候选模型。
- 其他 RTX 系列的兼容性属于架构目标，**不能用 5070 Ti 一机测试冒充全 RTX 认证**。
- 原 Intel Arc B390 P0 因网络下载阻断为 `BLOCKED`，保持历史原样。新增 P0-NVIDIA 报告。P0-NVIDIA 通过可申请推进 P1，但不得宣称 Intel 已验证；P1 仍须用户批准。
- AI 神经网络训练和推理必须在 GPU 上执行，不能静默 CPU fallback；CPU 用于解码、预处理、GUI 等非 AI 工作允许。

## A. 只读环境审计
1. 记录当前目录、Git 状态、Windows、CPU/GPU、显存、驱动版本、CUDA driver/runtime、Python ABI、硬盘空间、环境变量中可能影响 CUDA 的配置。
2. 检查本机已有 Python、CUDA、ComfyUI、YOLO 环境，但 **只读**；核查安装源官方兼容性及访问日期，无法核实时如实标注。
3. 检查网络与包下载情况；下载重试必须有超时上限，优先官方源/可信缓存，不禁用 TLS 校验。

## B. 环境隔离
1. 在 IVAD 项目目录创建独立的 NVIDIA 推理、训练 venv（可根据依赖兼容性合并，但不得污染已有环境）。记录 python.exe 完整路径、包名、版本及来源，提供锁定/复现方案。
2. 禁止未经批准升级显卡驱动、Windows、系统 CUDA Toolkit，禁止修改全局 PATH/Conda/Python 和用户其他 AI 项目。不得清理已有 .venv/缓存/模型。
3. 如果依赖缺失或下载失败，按 `BLOCKED` 记录，不要无限重试或通过不可信来源补包。

## C. GPU 基础测试（必须是真实执行）
1. 记录 `torch.cuda.is_available()` 和 GPU 名称，但不能仅以此断言 PASS。
2. 实际 CUDA Tensor 计算、模型前向、loss.backward()、optimizer.step()，核实参数变化、张量在 CUDA 上，保存和重新加载权重。
3. 测试 CUDA OOM 失败处理及显存测量能力；不得为了压测故意破坏系统稳定性。
4. ONNX Runtime 必须确认 `CUDAExecutionProvider` 被实际使用，避免注册 provider 成功但节点回退 CPU。必要时用 profiling/provider 检查；如果无法核实则标注 BLOCKED/NOT VERIFIED。

## D. YOLO26n 与 YOLO11n 对照
1. 使用官方或可校验可信的模型来源、相同数据及输入尺寸（默认 640），固定 batch、预热次数与重复次数，记录软件/权重版本、精度、模型哈希、数据来源。
2. 分别完成模型加载、CUDA PyTorch GPU 推理、导出 ONNX、ONNX Runtime CUDA GPU 推理、结果一致性验证。分开计时解码、预处理、推理、后处理，输出 p50/p95 延迟、FPS、显存峰值与异常日志。
3. 分别尝试小规模 GPU fine-tuning：最小前反向及更新、短训、生成权重、验证重新加载。若训练失败须区分模型/算子/框架/环境错误。
4. 不同 YOLO 架构可有不同输出形状与 NMS；禁止假设后处理完全一致。TensorRT 是可选研究项，不得阻塞核心任务。
5. 缺官方权重、下载或依赖受限时明确 `BLOCKED`；禁止伪造 FPS、mAP、GPU 结果。合成样本仅验证流程，不证明煤厂故障识别精度。

## E. 接口与未来兼容性审计
- 审核 ModelAdapter、ComputeBackend 契约是否能分别承载 NVIDIA CUDA / Intel XPU、OpenVINO；只提建议和最小文档修订，不开展 P1 实施。
- 必须区分模型在 NVIDIA 的 PASS 与 Intel 的 `NOT TESTED/BLOCKED`；主模型为 NVIDIA 初选，Intel 后续单独选择配置。
- 保留 GPU-only、隔离运行环境、统一 GUI、API-Ready、版本控制与人工审核发布原则。

## F. 报告与门槛
生成/更新：
- `reports/P0_NVIDIA_ENVIRONMENT.md`
- `reports/P0_NVIDIA_GPU_COMPATIBILITY.md`
- `reports/P0_NVIDIA_BENCHMARK.md`
- `reports/P0_NVIDIA_ACCEPTANCE.md`
- `scripts/p0_nvidia/README.md` 及可复现测试脚本/原始计时日志。

单项状态明确为 `PASS / FAIL / BLOCKED / NOT TESTED`。至少包括：真实 CUDA 前反向与权重更新、两候选模型推理、ORT CUDA provider GPU 执行、短训、环境安全检查、结果正确性及可复现实验。失败须附最小复现和诊断，不允许以“已安装”代替“已运行”。

**退出规则**：P0-NVIDIA 完成后提交中文报告并停止；只有用户明确批准才能进入 P1。P0-Intel 保持独立历史状态，后续恢复测试时另行批准。
