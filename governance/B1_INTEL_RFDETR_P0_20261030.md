# B.1 Intel RF-DETR P0 逐项审查补充

2026-10-30 用户明确要求按免费商业使用、内部研发、闭源部署及数据保密的实质义务复核，禁止以“未列白名单”作为唯一阻断依据。B.1 核心禁令与正式发行冻结未修改。

逐项条款、证据副本、hash、传递组件与隔离决定见 [实验 B.1 审查](../experiments/intel_rfdetr_p0/audit/B1_RESUME_REVIEW.md) 和 [许可证报告](../experiments/intel_rfdetr_p0/License_Audit.md)。

- Torch BSL-1.0（Boost）、Apache WITH LLVM exception、certifi/tqdm MPL，以及 Intel EULA 的内部研发许可均已实际审查，不再仅因白名单缺项阻断本地实验。
- 本地离线商业闭源可按各许可义务设计；Intel 材料不能用于所禁止的 SaaS/服务局用途，也不能任意再分发。第三方声明、对应源码获取和指定 Redistributables 范围不得遗漏。
- NumPy/SciPy wheel 内嵌 GCC runtime 的 GPL+exception 不能自动豁免产品随附禁令；OpenCV FFmpeg 未做产品逐构建验收。当前完整 Python 环境仅为独立研发工具，不被产品引用或随附；不是获批的 Trainer 发布闭包。
- 推理优先采用原生 OpenVINO 独立部署，Python 科学计算闭包留在研发端。P0 GPU 推理成功不替代 C++/.NET 主机与最小 DLL 分发材料验收。
- 本次无付费授权采购、公开、上传、签名或正式打包。无许可证删除、元数据伪造、业务标签重命名。

用户要求前台 Annotator 绝对优先，release_gate.ps1 会重建并启动 Annotator，故本次不运行它；仅进行隔离实验验证。不能引用本补充宣布主工程 Gate 或正式发行 READY。
