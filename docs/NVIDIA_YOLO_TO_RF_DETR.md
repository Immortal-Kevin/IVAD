# NVIDIA 从 Ultralytics YOLO 迁移到 RF-DETR Nano

本文于 2026-11-18 根据原提交和原验收记录整理。[公开提交映射](PUBLIC_COMMIT_MAP.tsv) 记录原 SHA 与发布 SHA。原清退报告是 `reports/P37_LEGACY_YOLO_RETIREMENT.md`（原提交 `b0d56b7`）；完整报告及现场证据保存在本机。

P3 用 YOLO11n 和 YOLO26n 验证了人工标注到冻结数据集、CUDA 训练、模型登记、权重重载和 ONNX 导出这条链路。P3.5 接着在真实录像上验证离线预处理、GPU 推理和缓存回放。三个历史 YOLO 训练配置可在 [实验归档](../archive/yolo/experiment-configs.json) 对照。数据来自单一来源组，独立现场泛化待核实。

项目要求闭源交付，商业模型授权预算为零。Ultralytics 官方将 AGPL-3.0 和供专有集成使用的 Enterprise 授权区分开来。2026-10-16 的原发行审计记录了 Enterprise 授权和经批准的 AGPL 发行方案均缺失，团队暂停该交付路线。旧实验只用于追溯，当前训练通过 RF-DETR 路由。 [Ultralytics 官方授权说明](https://www.ultralytics.com/license)

RF-DETR 固定为 `rfdetr==1.11.2`，上游 tag `1.11.2` 指向 `7433d5919d0f7e72cc6cb78663e0a731afd499e0`。固定版和 Roboflow 授权说明均将 Nano Detection 与官方 COCO 权重列为 Apache-2.0。官方 Nano COCO 权重的 SHA-256 是 `d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d`。本机在 384×384 检测路径上验证了 CUDA 微调、重载及 ONNX 导出。原冻结人工框标注可直接转成 COCO。其他组件和工业数据仍按其各自权利来审查。 [Roboflow 模型授权](https://roboflow.com/model-licenses/rf-detr) · [固定版本](https://github.com/roboflow/rf-detr/tree/7433d5919d0f7e72cc6cb78663e0a731afd499e0) · [PyPI](https://pypi.org/project/rfdetr/1.11.2/)

| 日期 | 原提交 | 原始变更、回退或恢复证据 |
| --- | --- | --- |
| 2026-10-15 | `275de69` | CUDA 训练和模型登记。留存三个旧训练参数组、基座 SHA 与原权重。 |
| 2026-10-16 | `77b3225`、`9414e3c`、`48f9127` | 验证离线 CUDA 和 ONNX；发行审计为打包保留阻断，第三方依赖审计独立保存。 |
| 2026-10-16 | `b157e3e` | 进行 Nano 隔离训练。初版长训因构造前未固定种子而取消。取消检查点、短训和修正后的 12 epoch 实验均保存在原输出。 |
| 2026-10-16 | `1f1db7d` | 独立 RF-DETR CUDA worker 接入训练路由；从冻结标注生成 COCO。 |
| 2026-10-19 | `b0d56b7`、`deff366`、`458e326` | 旧清退报告列出 7 个普通入口的移除。旧缓存和权重继续归档；Qt 原生问题和发行合规留待核实。 |
| 2026-10-19 至 11-04 | `1204369`、`1ee870b`、`5182e6a`、`833e2b5` | 媒体替代、Intel 集成和数据保护分阶段进行；原分支指向的回退点依次为 `1204369`、`1ee870b`、`5182e6a`，用于恢复各阶段之前的基线。实际执行生产回退的记录待核实。 |
| 2026-11-18 | 本发布分支 | 对照清退记录、模型登记和原工件哈希；整理公开副本和本地清单。 |

4 个真实 IDS 完整包和 2 个增量包已在原交接清单及备份内按 SHA-256 核对。旧环境、工业权重、真实 IDS、原报告与现场记录的处理见 [保留索引](LOCAL_ASSET_INDEX.md)。
