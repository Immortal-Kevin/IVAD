# IVAD 第三方组件与内部专有授权政策（P3.6 工程草案）

日期：2026-10-16。状态：待用户及公司确认，不构成法律认证或发行批准。

## 产权与授权边界

IVAD 独立编写部分拟继续内部专有使用。实际权利主体、职务成果、委托开发及第三方贡献归属尚需公司核验；本文件不认定个人或公司当然拥有全部源码。仓库根 LICENSE 与既有版权头未更改。

使用 Apache-2.0 组件不要求自动把整个 IVAD 改为 Apache-2.0。该判断只适用于明确获许可的具体代码与权重；不能用于覆盖旧 Ultralytics、未知来源实现或其他第三方条款。

## RF-DETR 评估

固定评估 rfdetr 1.11.2 / 官方 tag 1.11.2，Commit `7433d5919d0f7e72cc6cb78663e0a731afd499e0`。仅 Nano Detection，禁止 Plus/XL/2XL 或未经核验权重。

官方该版本 README 将开源包和标记 Apache 的权重列为 Apache-2.0；Nano Detection 在模型表中明确标记。保留包内 LICENSE、源文件原有声明及依赖通知；对以后修改的第三方文件显著说明修改；遇到上游 NOTICE 时保留其适用内容。不利用商标或暗示原作者背书。Apache 的专利授权、终止、免责等以完整原文为准。

官方原文保存在 `legal/licenses/Apache-2.0.txt`，原始下载 SHA256 为 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`；Roboflow 自身带版权附录的 LICENSE 单独保留，不能用 ASF 模板取代组件版权声明。

## 历史 Ultralytics

旧训练/推理引擎、环境、YOLO 权重与 ONNX 全部保留用于历史复现；它们未因本次 RF 实验自动获得新的授权。没有 Enterprise 授权，也没有批准 AGPL 发行方案。独立进程本身不解决旧系统整体授权问题。

RF 验证目录和 `.venv-rfdetr` 独立运行，禁止调用旧引擎或使用旧权重初始化。正式 GUI 当前仍连接旧引擎，不得将实验隔离宣传为正式产品已经摆脱 AGPL。

## 内部部署与再分发

当前仅批准本机独立可行性实验。关联厂区部署、向其他法人提供软件或正式展示安装需重新核对实际交付组件与适用义务；不能简单认为“内部”必然免除全部义务。

发行前仍需：确认源码产权；完成 C/D/E 来源调查；审定 Qt/LGPL、FFmpeg 构建、NVIDIA 运行库及全部传递依赖；准备适用源代码/重链接/通知材料；锁定实际 payload；得到用户明确批准。`PACKAGING_FREEZE = TRUE`，不生成安装包。

依据：[RF-DETR 官方固定版本](https://github.com/roboflow/rf-detr/tree/7433d5919d0f7e72cc6cb78663e0a731afd499e0)、[Roboflow 许可说明](https://roboflow.com/licensing)、[Apache 官方许可](https://www.apache.org/licenses/LICENSE-2.0.txt)。
