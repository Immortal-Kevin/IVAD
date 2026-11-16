# P0 环境核查报告

日期：2026-10-12，Asia/Shanghai。范围：P0；用户已授权项目隔离编程、安装和测试，未授权 P1。

## 本机只读核查

| 项目 | 实际结果 |
|---|---|
| 工作目录 | C:/Users/kevin/Desktop/IVAD Project |
| 项目根目录 | C:/Users/kevin/Desktop/IVAD Project/IVAD_Platform_v1.0 |
| Git | 当前目录非 Git 仓库；项目原始文件清单无 .git；未创建 Git 仓库 |
| OS | Microsoft Windows 11 家庭版 中文版，Build 26200 |
| CPU | Intel Core Ultra X7 358H |
| GPU | Intel Arc B390 GPU |
| GPU PNP ID | PCI VEN_8086 / DEV_B080；完整值见 raw/environment.json |
| 驱动 | 32.0.101.9033，未修改 |
| 物理 RAM | 33,873,752,064 bytes（约 31.55 GiB，标称 32 GB） |
| OS 可见 RAM | 33,079,836 KiB；不等于 GPU 独占显存 |
| C 盘空闲 | 初查 181,180,182,528 bytes；后查 180,450,226,176 bytes；期间系统其他活动可能影响差值 |
| 默认 Python | D:/Python/Miniforge3/python.exe，Python 3.14.7；仅只读调用，未装包或修改 |
| 独立基础 Python | C:/Users/kevin/AppData/Local/Python/pythoncore-3.14-64/python.exe，3.14.7；py -0p 已核查 |
| 包管理器 | 默认 pip 指向 Miniforge；项目只用虚拟环境 python -m pip |

## 隔离与权限

两环境位于项目 `.venvs/intel_infer`、`.venvs/intel_train`。最初沙箱执行 venv 的 ensurepip 子进程出现 `Failed to find real location`，两个已安装 Python 路径都出现此症状；以获准的项目范围执行重试成功。它不是已证实的 Miniforge 损坏。

CIM 在沙箱失败；经只读权限核查后取得真实硬件和驱动。没有自动审批拒绝。未修改 PATH、注册表、Windows 配置、驱动或其他 Python/Conda/YOLO/ComfyUI 环境；未删除、覆盖或上传用户数据。

## 官方说明及候选版本

来源与查看日期见 P0_SOURCES.md。Intel 页面驱动基线低于本机版本，不能由此断言 GPU 可用。PyTorch XPU 和 OpenVINO 页面列出适用平台，但具体组合仍需实测。

下载解析得到的目标：OpenVINO 2026.4.1、NumPy 2.5.4、openvino-telemetry 2025.2.0；PyTorch 2.14.1+xpu、torchvision 0.29.1+xpu。这些是候选安装版本，**不是已安装运行库**。两环境实际 freeze 均仅有 pip 26.2.1，见 raw/intel_infer.lock.txt 与 raw/intel_train.lock.txt。尚无可用完整 AI 依赖锁。

另经官方 PyPI JSON 核查 Ultralytics 候选版本 8.4.175，Requires-Python >=3.8，许可字段 AGPL-3.0；保存于 raw/ultralytics_metadata.json。尚未安装，Python 版本声明不能替代其全部依赖兼容性测试。

## 下载阻断

常规 pip 能取得包元数据；OpenVINO 85 MB 和 torch 768.1 MB wheel 下载长时间无文件数据。一次固定版本、timeout=15 / retries=0 的 torch 重试仍无数据。OpenVINO 1KB HTTP Range 探查成功（206，1024 bytes），4MiB 分段重试未取得首段数据，已结束本轮创建的下载进程。不能确定根因是代理、服务端或链路，不据此修改系统网络设置。

GitHub release API 读取发生 IncompleteRead；权重及 bus.jpg 未成功取得，未加载任何 .pt。原始堆栈见 raw/download_assets.log。环境原始证据见 raw/environment.json、environment_extra.json、install_*.log、fetch_wheels.log、network_wheel_probe.log。

结论：硬件身份与项目隔离核查 PASS；AI 运行环境准备 BLOCKED。
