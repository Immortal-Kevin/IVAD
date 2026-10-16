# 第三方组件通知与核查状态

日期：2026-10-16。工程审计，非法律认证/正式分发许可。`PACKAGING_FREEZE=TRUE`。

本文件覆盖本轮 RF 实验及仍保留的正式系统。版本以实际安装清单为准，不能用 RF-DETR 的 Apache 许可替代下面组件各自条款。完整许可证/版权文本的原样副本、文件哈希及安装元数据在本轮 dependency-audit；旧环境对应证据见 `artifacts/p35-compliance-plan-20261016/verified`。通知尚不是最终安装包 SBOM 或已完成的全套发行合规材料。

## 关键组件

| 组件/实际版本 | 官方地址 / 许可与版权依据 | 义务、限制与本轮结论 |
|---|---|---|
| RF-DETR 1.11.2、Nano Detection 官方权重 | https://github.com/roboflow/rf-detr/tree/7433d5919d0f7e72cc6cb78663e0a731afd499e0 ；Apache-2.0；Copyright 2025 Roboflow, Inc. | 保留 LICENSE/源文件版权及适用 NOTICE，修改第三方文件须声明；不暗示商标背书。wheel LICENSE 已原样保存至 legal/licenses/RF-DETR-1.11.2.LICENSE.txt。该 wheel 仅发现 LICENSE，未以“无单独 NOTICE”免除其余版权义务。Nano 权重来源及哈希见主报告；未安装 Plus |
| PyTorch 2.9.1+cu128 / TorchVision 0.24.1+cu128 | https://github.com/pytorch/pytorch/blob/v2.9.1/LICENSE 、https://github.com/pytorch/vision ；BSD-3-Clause 等；版权为 PyTorch/贡献者，完整名单以包 LICENSE 为准 | 保留版权、条款、免责与内含第三方许可；BSD 不能覆盖捆绑 CUDA/cuDNN 的专有再分发限制。原文已提取，最终 payload 仍需审查 |
| ONNX 1.20.1 / ONNX Runtime GPU 1.24.4 | https://github.com/onnx/onnx 、https://github.com/microsoft/onnxruntime/blob/v1.24.4/LICENSE ；ONNX Apache-2.0，ORT MIT；ONNX 贡献者/Microsoft 及贡献者 | 保留 LICENSE、ThirdPartyNotices 与对应版权；GPU Provider 依赖 NVIDIA 运行库另行核验。运行成功不等于再分发已批准 |
| PySide6 / Qt 6.8.3（原 GUI 环境） | https://doc.qt.io/qtforpython-6.8/licenses.html ；LGPLv3/GPLv3/商业许可，组件依实际模块而定；The Qt Company 及贡献者 | 未证明已有 Qt 商业授权。当前 wheel RECORD 中仅 Qt 商业许可文本不足以满足 LGPL 发行文件；需合法选择许可路径、核查模块、用户替换/重链接能力与适用源码提供。未在本轮 RF 环境安装 Qt |
| PyAV 15.1.0 及 FFmpeg avcodec61（原 GUI） | https://github.com/PyAV-Org/PyAV 、https://ffmpeg.org/legal.html ；PyAV BSD-3-Clause，实际 DLL 报 LGPLv3+；PyAV/FFmpeg 贡献者 | 旧 DLL 配置同时含 x264/x265，构建与链接来源仍待核实；不能仅凭 API 许可字符串宣称整体发行安全。保留既有证据，不替换原 DLL |
| Ultralytics 8.4.176、ultralytics-thop 2.2.2、ultralytics-platform 0.1.84（旧 Worker） | https://www.ultralytics.com/license ；AGPL-3.0/AGPL-3.0-only 等，Copyright Ultralytics 等以包原文为准 | 仍无 Enterprise 或已批准 AGPL 方案；旧模型/ONNX 不自动转 Apache。正式系统授权路径未解决；RF 实验不得依赖它们 |
| NVIDIA CUDA 12.8 / cuDNN（随 torch wheel，具体运行版本见 GPU 证据） | https://docs.nvidia.com/cuda/eula/ 、https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html ；NVIDIA 专有许可与第三方条款 | Copyright NVIDIA Corporation。仅复制 EULA/NOTICE 不表示全部 DLL 可再分发；需对照实际文件与获准 redistributables、用途、限制及通知逐项核验。未改系统 Toolkit/驱动，未来安装包门禁未解除 |
| Python 3.12.14（独立 venv 基础解释器） | https://docs.python.org/3.12/license.html ；PSF-2.0 及包含的第三方许可，Python Software Foundation 等 | 保留 Python LICENSE/适用 notices；本机运行时不是已准备好的官方 Windows 可分发解释器。3.12.14 官方为源码发布，不能编造对应 embed 包来源 |

## 传递依赖与版权

本轮实际共 **96 个安装包、154 份原样通知副本**；95 个运行依赖已记录归档 SHA256（pip 为独立环境自带管理工具）。逐项版本、官方元数据地址、版权摘要、许可与通知路径见 [完整依赖索引](RFDETR_DEPENDENCY_INVENTORY.md)。原样副本根目录为 `artifacts/p36-rfdetr-20261016/dependency-audit/p36-rfdetr/notices`。

本轮重要附加组件：Supervision 0.30.9（MIT）、Transformers 5.20.0（Apache-2.0）、PyTorch Lightning 2.6.6（Apache-2.0）、TorchMetrics 1.8.2（Apache-2.0）、PEFT 0.21.2（Apache）、Roboflow 1.7.1（Apache 分类及原文）、hotcoco 1.0.1（MIT）、faster-coco-eval 1.8.0 和 torch-hungarian 0.1.0rc0（metadata 空，已核对所带 Apache-2.0 全文）、ultrafast-pycocotools 0.1.13（BSD-2-Clause）、vernier 0.5.4（MIT OR Apache-2.0）。RC 匹配器由该固定 RF 版本显式依赖，并非安装额外 Plus；Windows 的匹配步骤实际会用 SciPy CPU，不是神经网络 CPU 降级。

ONNXsim 0.7.0 metadata 为 `MIT AND (Apache-2.0 OR BSD-2-Clause)`，Polygraphy 0.53.6 metadata 为 Apache-2.0，但两者 wheel RECORD 未提供可提取的完整通知文件：**正式发行材料待补齐**。不以 metadata 字段代替完整条款。

补充核查：从 PyPI 对应版本 sdist 校验 SHA256 后，已原样补采 ONNXsim 的 LICENSE、内含 ONNX optimizer/ONNX 的 Apache LICENSE 与 ONNX NOTICE，以及 Tokenizers 0.23.3 的 Apache LICENSE，存于 `legal/licenses/supplemental`；来源/哈希见该目录 `SOURCES.json`。ONNXsim wheel 的复合许可声明与源码所附条款覆盖仍需核对，不能因补采一个 LICENSE 就宣布全部义务完成。FlatBuffers 25.12.19、Polygraphy 0.53.6 无对应 PyPI sdist；FlatBuffers 候选官方 tag 文件返回 404；pycocotools 2.0.11 sdist 也未含独立 LICENSE/NOTICE。缺项、网络错误与原始来源均留档，没有绕过 TLS 或修改代理。

RF 环境还实际安装 PyAV **19.0.1**，其 FFmpeg libavcodec **63.1.102**，与原 GUI 的 15.1.0/avcodec61 是不同二进制。新 avcodec DLL 仍报告 `LGPL version 3 or later`，配置含 libx264/libx265，构建/链接权利问题仍需核实。新环境 OpenCV 为 `opencv-python-headless 5.0.0.93`，必须连同它自己的原生捆绑通知审查。原始配置已存 `native-codec-inventory.json`，没有替换旧 GUI DLL。

RF-DETR 内含 DINOv2、DETR 与 Hugging Face 派生实现，其源文件版权/引用不能删去。上游顶层 Apache 不应代替逐组件来源核查。重要安装依赖的实际版本、metadata 许可字段与原始通知路径在附录；完整版权以原文为准，不能把 metadata 为空视为没有版权。

Supervision、Transformers、Lightning、TorchMetrics、PEFT、COCO 评估器、NumPy/SciPy/Pillow、OpenCV、PyAV 等即使未直接由 IVAD import，也属于本实验依赖审查范围。所有实际 AGPL/GPL/未知字段须单列核验，不能按名字猜测；FFmpeg/图像编解码器/字体/NVIDIA 等原生捆绑项需要额外审查。

## 尚未满足的正式发行条件

1. IVAD 权利主体和 C/D/E 来源确认；旧 Ultralytics 正式替换或适用授权方案。
2. Qt LGPL 材料、替换/重链接验证与相应源码提供策略。
3. FFmpeg 两个以上不同构建的配置、链接和 codec 来源；不能将新旧二进制混为一谈。
4. NVIDIA 每个拟交付运行库的获准再分发依据与完整通知。
5. 最终 payload、源码/通知包、归档哈希、净机验收和公司授权确认。

这些缺项不由本轮本机独立实验自动补齐，也不触发收费购买、仓库开源或正式发行。
