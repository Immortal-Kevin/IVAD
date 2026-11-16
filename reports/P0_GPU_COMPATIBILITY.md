# P0 GPU 兼容性报告（续行）

日期：2026-10-12。**OpenVINO 基础 GPU PASS；XPU 基础测试 BLOCKED；模型计算仍 NOT TESTED。**

| 验证层 | 状态 | 真实证据 |
|---|---|---|
| B390 硬件身份 | PASS | 首轮 CIM，驱动32.0.101.9033 |
| OpenVINO 安装 / pip check | PASS | 三个固定版本官方 hash 验证后离线安装；No broken requirements |
| OpenVINO GPU 枚举 | PASS | CPU/GPU/NPU；GPU名称 Intel(R) Arc(TM) B390 GPU (iGPU) |
| OpenVINO 实际 GPU 运算 | PASS | 显式GPU编译；EXECUTION_DEVICES=[GPU.0]；输出 [0,1,3,5] 与预期一致 |
| PyTorch XPU 安装 | BLOCKED | torch等大文件仍未完整取得，暂停安装 |
| XPU 前向/反向/参数更新 | BLOCKED | 已重新执行探针，import torch 报 ModuleNotFoundError；未触达计算段 |
| YOLO26n/YOLO11n GPU 推理及训练 | NOT TESTED | XPU/完整模型环境尚未就绪 |
| NVIDIA | NOT TESTED | 未切换其他GPU |

OpenVINO实际运行库版本：2026.4.1-22982-e213a147257-releases/2026/4。显式GPU编译并核查执行设备，未使用 AUTO/HETERO 或 CPU fallback。这里通过的是简单计算图，不代表 YOLO 算子或工业场景已经通过。

原始结果：raw/openvino_probe_resume.json、openvino_gpu_resume.log、infer_offline_install.log；XPU原始错误：raw/xpu_probe_resume.json。首轮缺包失败日志仍保留。

复现（项目根目录）：

```powershell
& .venvs/intel_infer/Scripts/python.exe scripts/p0/gpu_probe.py openvino --output reports/raw/openvino_probe_resume.json
& .venvs/intel_train/Scripts/python.exe scripts/p0/gpu_probe.py xpu --output reports/raw/xpu_probe_resume.json
```

目前故障定位为下载/运行库准备层，未对硬件XPU、PyTorch模型算子、Ultralytics训练集成作不兼容判断。禁止用CPU或另一显卡填补未测项。恢复完整XPU依赖后再运行前后向及更新门禁，通过后才继续两模型。

## 2026-10-14 VPN直连续行

Tailscale出口节点已启用，官方下载目标实际选择Tailscale路由。仅对下载进程禁用代理/绑定WLAN以及socket接口选择均未恢复连接；最后一种方式被WinError10013拒绝。未修改系统路由、VPN、代理、TLS或驱动；依赖下载尚未恢复，没有新增GPU/模型测试PASS。
详见P0_VPN_DIRECT_20261014.md及原始日志。等待用户手动停用出口节点，或单独授权临时停用并恢复，之后先做有界直连对照，再继续P0。不进入P1。
