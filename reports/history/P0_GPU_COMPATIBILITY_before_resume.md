# P0 GPU 兼容性报告

日期：2026-10-12。结论：**BLOCKED（依赖下载层）**，没有证据认定 B390 计算不兼容，也没有 GPU PASS。

| 验证层 | 状态 | 实际证据 |
|---|---|---|
| Windows 硬件身份 | PASS | CIM 确认为 Arc B390，驱动 32.0.101.9033 |
| OpenVINO 安装 | BLOCKED | wheel 下载无进展；numpy/openvino 未装入隔离环境 |
| OpenVINO GPU 枚举及实际计算 | BLOCKED | 已运行探针；import numpy 报 ModuleNotFoundError，未触达 GPU |
| PyTorch XPU 安装 | BLOCKED | 官方 XPU wheel 下载无进展；torch 未安装 |
| XPU 张量、前向、反向、更新 | BLOCKED | 已运行探针；import torch 报 ModuleNotFoundError，未触达 GPU |
| YOLO26n/YOLO11n 模型算子 | NOT TESTED | 运行库及可信权重未就绪 |
| Ultralytics XPU 训练集成 | NOT TESTED | 尚未安装框架或执行模型训练 |
| OpenVINO 模型导出与 GPU 加载 | NOT TESTED | 基础门禁被阻断 |
| NVIDIA | NOT TESTED | 不在本轮实机验证范围 |

## 最小复现

从项目根目录执行：

```powershell
& .venvs/intel_infer/Scripts/python.exe scripts/p0/gpu_probe.py openvino --output reports/raw/openvino_probe.json
& .venvs/intel_train/Scripts/python.exe scripts/p0/gpu_probe.py xpu --output reports/raw/xpu_probe.json
```

`gpu_probe.py` OpenVINO 路径要求 B390，显式 compile_model(..., 'GPU')，核查 EXECUTION_DEVICES 全部为 GPU，验证计算输出。XPU 路径要求 B390，模型/输入/loss/梯度在 xpu，执行 backward 与 optimizer.step，核查参数实际变化。代码不设置 CPU fallback。**这些计算段本轮未运行到，不能据脚本内容记为测试通过。**

原始错误：OpenVINO 路径 `ModuleNotFoundError: No module named 'numpy'`；XPU 路径 `ModuleNotFoundError: No module named 'torch'`。完整堆栈见 raw/openvino_probe.json、raw/xpu_probe.json。

故障归类：下载/运行库准备层阻断；硬件 XPU、PyTorch 算子、YOLO 算子、Ultralytics 集成均尚无否定结论。没有采用 CPU、模拟 GPU 或其他显卡替代。
