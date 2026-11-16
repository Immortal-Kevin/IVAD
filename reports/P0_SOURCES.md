# P0 官方来源与下载前记录

查看日期：2026-10-12（Asia/Shanghai）。仅开展本地 P0 兼容性实验；未解决生产商业许可。

- Intel 前置条件：https://www.intel.com/content/www/us/en/developer/articles/tool/pytorch-prerequisites-for-intel-gpu/2-13.html 。页面 Windows 驱动要求 32.0.101.8801 或更高；本机 32.0.101.9033。不安装系统 SDK，不使用 torch.compile。
- PyTorch XPU：https://docs.pytorch.org/docs/2.14/notes/get_start_xpu.html 。Windows 11 / Core Ultra Series 3 列于支持矩阵；官方 XPU wheel 索引 https://download.pytorch.org/whl/xpu 。支持声明不替代实测。
- OpenVINO：https://docs.openvino.ai/2026/about-openvino/release-notes-openvino/system-requirements.html 。列有 Windows 11、Intel Arc 和 Python 3.10–3.14；驱动不包含于 pip 安装包。框架版本表与当前 PyTorch wheel 不完全一致，因此转换兼容性须实测。
- Ultralytics 导出：https://docs.ultralytics.com/integrations/openvino 。显式 Intel GPU 或原生 OpenVINO GPU 编译；不使用 AUTO/HETERO。
- YOLO26：https://docs.ultralytics.com/models/yolo26 。本项目仍按已批准范围仅比较 YOLO26n / YOLO11n，不自行换成其他新模型。
- 权重官方发布：https://github.com/ultralytics/assets/releases/tag/v8.4.0 ，仅下载 yolo26n.pt、yolo11n.pt，下载后验证大小及 API 提供的 digest（若有），保存 SHA256；仅加载可信官方权重。
- 样例图：https://raw.githubusercontent.com/ultralytics/assets/main/im/bus.jpg ，官方公开测试图，不上传用户数据，不作为工业准确率依据。
- 许可：https://www.ultralytics.com/license 。官方列出 AGPL-3.0 / Enterprise；代码及模型商业闭源、厂内生产的授权未解决。当前不发布产品或生产模型。

实际安装版本、最终下载 URL 与 hash 以 reports/raw 的日志、依赖锁和 artifacts/p0/sources.json 为准，不把网页描述当成安装成功。
