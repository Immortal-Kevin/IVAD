# NVIDIA 从 Ultralytics YOLO 迁移到 RF-DETR Nano

本文于 2026-11-18 整理。时间线中的原始提交、旧报告、训练目录和工件均保留。GitHub 分支使用脱敏历史副本，原始提交 ID 以本文及归档映射为准。

## 早期 YOLO 验证

P3 在 NVIDIA CUDA 上用 YOLO11n 和 YOLO26n 验证了人工标注、冻结数据集、训练与检查点、模型登记、同一输入下的权重重载及 ONNX 导出。P3.5 用历史模型验证了真实录像离线预处理、GPU 检测和缓存回放。原项目登记了 3 次成功 YOLO 训练和 3 个对应模型。冻结数据集包含 200 图、402 个框和 16 张无框负样本，全部来自一个来源组。验证集指标仅用于工程验证，独立产线泛化仍待核实。详见 [P3 模型验证](../reports/P3_MODEL_VALIDATION.md) 与 [旧训练归档](../reports/P37_LEGACY_TRAINING_ARCHIVE.md)。

## 暂停理由及替代选择

项目要求闭源交付，商业模型授权预算为零。Ultralytics 官方说明将允许按 AGPL-3.0 开源项目的用法与需要 Enterprise 授权的专有集成区分，并明确列出自训练或微调 YOLO 模型用于专有产品的情形。2026-10-16 打包审计记录当时既无 Enterprise 授权，也无获批的 AGPL 发行方案，因此团队暂停 Ultralytics 交付路线并保留历史实验。旧权重、导出及依赖只作历史归档，当前 NVIDIA 训练入口仍使用 RF-DETR。 [Ultralytics 授权说明](https://www.ultralytics.com/license) · [原发行授权审计](../reports/P3_5_RELEASE_LICENSE_AUDIT.md)

本项目固定 Roboflow `rfdetr==1.11.2`，上游 tag `1.11.2` 对应 `7433d5919d0f7e72cc6cb78663e0a731afd499e0`。发布 wheel 的 SHA-256 为 `2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a`。Roboflow 将该基础包及 Nano Detection 的官方权重列为 Apache-2.0。选用的 COCO 权重有 366,287,238 字节，其 MD5 为 `fb6504cce7fbdc783f7a46991f07639f`，本机 SHA-256 为 `d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d`。Nano 采用 384×384 的检测路径，已在独立解释器中验证真实 CUDA 微调、重载及 ONNX 导出。现有冻结人工框标注可直接转换为 COCO。发行仍需保留适用的版权和许可声明，并继续核实其余原生组件和项目资产的授权。 [Roboflow 模型授权](https://roboflow.com/model-licenses/rf-detr) · [固定版本源码](https://github.com/roboflow/rf-detr/tree/7433d5919d0f7e72cc6cb78663e0a731afd499e0) · [PyPI 发行](https://pypi.org/project/rfdetr/1.11.2/) · [官方 Nano COCO 权重](https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth) · [原可行性记录](../reports/P36_RFDETR_FEASIBILITY.md)

## 迁移与回退时间线

| 日期 | 原始提交 | 变更、回退原因与证据 |
| --- | --- | --- |
| 2026-10-15 | `275de69` | 接入隔离 CUDA 训练和模型 Registry。历史 run 与 ModelVersion 可由原库、权重和 [旧训练归档](../reports/P37_LEGACY_TRAINING_ARCHIVE.md) 对照。 |
| 2026-10-16 | `77b3225`、`9414e3c`、`48f9127` | 离线演示验证 CUDA 和 ONNX，之后因原报告所述授权限制阻断打包，并保留第三方依赖审计。 |
| 2026-10-16 | `b157e3e` | P3.6 隔离 Nano 实验实际完成 1 epoch 短训及 12 epoch 受控训练。早期 12 epoch 尝试因模型构造前未固定种子安全取消，取消 checkpoint 和日志保留。工程验证的原始指标与评估口径见可行性报告。 |
| 2026-10-16 | `1f1db7d` | Nano 训练接入独立 CUDA worker 与训练路由。数据集由冻结人工标注生成 COCO，保留原 train/val 划分。 |
| 2026-10-19 | `b0d56b7`、`deff366`、`458e326` | 清退七个普通操作入口。Legacy 训练 worker、模型记录、只读导出与缓存回放证据保留。旧报告说明 Qt 原生问题及发版合规仍有阻断。 |
| 2026-10-19 | `8b064b5`、`1204369` | 保存内部演示阻断、Lite 独立验证与原始许可材料。随后的媒体替代从后者建回滚点，旧包保持原状。 |
| 2026-11-02 | `1ee870b` | Windows 原生媒体候选与 RF 离线候选通过阶段验证。回滚点 `rollback/pre-permissive-20261102` 指向 `1204369`，用于恢复整改前基线。真实 IDS 在当日报告中仍缺失。 |
| 2026-11-04 | `5182e6a`、`833e2b5` | 接入 Intel WPF 与 IDS，四个真实完整包、删除与恢复增量在原报告中有独立验证记录。为分阶段隔离保留 `rollback/pre-intel-h1h5-20261104`（`1ee870b`）和 `rollback/pre-distribution-p0-20261104`（`5182e6a`）。这些回滚引用仍可检出，实际执行产品回退的记录待核实。 [WPF 原验收记录](../reports/NVIDIA_WPF_ARCHITECTURE_20261104.md) |
| 2026-11-18 | 本归档新提交 | 核对旧清单、原库、训练和现场包的字节哈希。保留原工作树、Git 对象、refs、reflog、未提交内容、已有包和独立 Intel 历史。无新增训练及安装包构建。 |

## 清单核对

- [原 YOLO 清退报告](../reports/P37_LEGACY_YOLO_RETIREMENT.md) 的旧训练和离线路径、只读登记、冻结数据、旧包与缓存均可在原始 Git 和本地备份定位。历史 YOLO GUI 行为有意退役。旧权重及导出在归档分支的资产路径下供审计。
- [原训练归档](../reports/P37_LEGACY_TRAINING_ARCHIVE.md) 的 3 个 YOLO 和 2 个 RF 权重均按登记 SHA-256 找到。归档索引记录具体运行、基座、数据集与导出的对应关系。YOLO 基座精确发布版本如无原始记录则待核实。
- 本机找到 Intel 交接清单中的 4 个真实完整包与 2 个真实增量包。同一文件名存在不同哈希时各自归档。合成包和派生包保存在本地证据里，真实 IDS 计数只纳入交接清单已验证的原件。
- GitHub 历史从包含第三方网页遥测令牌的原始提交开始生成脱敏副本。此前的提交 ID 保持原样，后续提交的原始 ID 与脱敏 ID 都保留在映射中。原始许可文本及网页证据仍保留在本地完整备份。
- 单独的删除清单若超出上述仓库清退报告、原始报告与可搜索的运行目录，其原路径待核实。原介质已失效的旧绝对路径及核对结果见本地恢复清单。完整软件再分发权利与个别工件上游来源仍待核实。
