# IVAD 阶段报告来源索引

报告日期2026-10-16，管理层Word第1版。实际12页，11处图号、10张不同真实GUI截图。所有图片为Qt GUI原始捕获或保留真实像素的裁剪，没有重绘检测框、改变置信度或制造结果。

## 关键结论

|Word位置|结论|核查来源|
|---|---|---|
|第3页 P0|本机RTX5070Ti、YOLO26n/YOLO11n短训及CUDA/ONNX验证|reports/P0_NVIDIA_ACCEPTANCE.md、P0_NVIDIA_BENCHMARK.md；artifacts/p0|
|第3页 P1|统一工作空间、项目、任务、设备、设置、日志|reports/P1_ACCEPTANCE.md；本轮8项tests/test_gui.py回归|
|第4–5页 P2|复制/引用、片段、抽帧、人工标注及正常负样本|reports/P2_ACCEPTANCE.md、P2_CLIP_SAVE_FEATURE.md、P2_ANNOTATION_WORKFLOW_SIMPLIFICATION.md；当前源码与真实GUI|
|第6页 P3|两种模型真实工程训练、数据集版本与模型仓库|reports/P3_ACCEPTANCE.md、P3_TRAINING_RESULTS.md、P3_WORKFLOW_GUI_HOTFIX.md|
|第7页 P3.5|真实GPU离线推理、三Tab、缓存和导出|reports/P3_MODEL_VALIDATION.md、P3_5_OFFLINE_DEMO_ACCEPTANCE.md、P3_5_THREE_TAB_GUI_HOTFIX.md；当前GUI真实缓存|
|第9页 200张/402目标|冻结v1 summary images=200、objects=402；160/40/0|本轮before/project.backup.sqlite之dataset_versions；原冻结manifest路径datasets/5ea5cbb0-3e8e-4c45-a0bd-9ec7ae9e9782/v0001/manifest.json|
|第9页 实际训练|7a01bcad，20实际epochs，800优化器更新，GPU-only|training_runs.details.result.evidence；原training/7a01bcad-4b18-4cec-a0f7-1a31f94d6a32/运行工件|
|第9页 模型与指标|4a1c7df7 EXPERIMENTAL；P=.9289736349/R=.9211238469/mAP50=.9592655466/mAP50-95=.4268771256|training_runs.details.result.metrics与model_versions.details.metrics一致；报告四位小数。采用保存的模型最终验证口径，不采用最后一轮CSV口径|
|第9页 口径复核|最后epoch CSV为P=.92882/R=.91904/mAP50=.95927/mAP50-95=.42689|原run/results.csv已重新读取，20行；本轮training-source-verified.json含hash及最后行。与注册结果存在差异，未重跑验证以强制一致，不混称同一指标|
|第9–10页 LIMITED|同源录像、无独立Test/独立复核、相邻相似帧跨集合风险|冻结summary.admission与model_versions.details.dataset_admission；非独立工业准确率|
|第9页 CUDA与ONNX|实际GPU节点、原权重保护、输出对齐；前向约13–15ms不能当视频FPS|reports/P3_MODEL_VALIDATION.md及其原始ORT profile、gpu-validation-detections|
|第11页 路线|正式SRS仅定义P0–P6，P7–P10为未批准建议|docs/SRS.md第7节；docs/ARCHITECTURE.md；docs/ROADMAP.md；docs/DECISIONS.md|
|第12页 现场需求|下一阶段建议，不是承诺已交付|本轮用户补充建议与现有数据独立性/告警缺口，未启动P4|

## 截图索引

主截图项目为已验收的独立测试副本；未以业务Store打开真实项目。副本仅包含本例8525录像，其余历史媒体未复制，图3中其他行的MISSING/ERROR不代表对真实项目对应视频的本轮判定。截图体现既有两条模型记录；原项目新增第三训练/第三模型同时纳入只读保护，未因副本截图而回退它们。模型推理画面有背景低置信度预测，不能当作人工确认的工业故障。

- 图1：现有实验模型的离线视频回放，检测框为真实预测，尚未确认工业故障。
  - 原始：`artifacts\p35-final-20261016\gui100\focus-1920.png`
  - SHA256：`63ba9354244690687f939bc27377ee7306a360bd3cfcc5a18dc330e2f751480b`；裁剪：False。
- 图2：项目管理，项目与摄像头分区维护。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-projects.png`
  - SHA256：`20a6775634cde398c66e95e901382a4a6cb09d0398714d129e52b04b8b81f3e5`；裁剪：True。
- 图3：视频管理与抽帧，原始录像保持独立。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-media.png`
  - SHA256：`91ee37a985a53b4a8c227d9fc9afa0de1a3589618c627476ac5396f2331ce5e3`；裁剪：True。
- 图4：8525压滤机既有人工标注，仅展示，不新增或改写真值。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-annotation.png`
  - SHA256：`314d86e7840d116b887948f52d3727596255aaa0706c5ae5309c72b332ff6e6d`；裁剪：True。
- 图5：数据集图片筛查与管理。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-dataset.png`
  - SHA256：`6ca5c5b4b4cd8170f78c82f7fc3351515dbc0b0b330861cc607ba947dcb2b42e`；裁剪：True。
- 图6：训练记录7a01bcad已存在，截图未启动新训练。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-training.png`
  - SHA256：`b043c6ba15d52f24273c481c346633e5d3a304491c81e283a68ad4b0a38c5a6e`；裁剪：True。
- 图7：模型仓库及版本追溯。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-models.png`
  - SHA256：`d0e2a7f839b9374349dbcd4c8fed57ba7bff42919d907fb0411a91b681dc23a1`；裁剪：True。
- 图8：标准播放，保留模型/摄像头状态和实际阈值。
  - 原始：`artifacts\p35-final-20261016\gui100\standard-1920.png`
  - SHA256：`82317cbd6c33aff9337a78c90b673e6ac7cfc15ad0fe590dd05762c4c174eea8`；裁剪：False。
- 图9：专注播放，保持16比9，无拉伸或裁切。
  - 原始：`artifacts\p35-final-20261016\gui100\focus-1920.png`
  - SHA256：`63ba9354244690687f939bc27377ee7306a360bd3cfcc5a18dc330e2f751480b`；裁剪：False。
- 图10：总览页面。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-dashboard.png`
  - SHA256：`8ce3d31046222af3d2f1baf5ff679b95701880e71e99da7e762d8289871eeae8`；裁剪：True。
- 图11：设备与后端页面，当前案例使用RTX 5070 Ti。
  - 原始：`artifacts\p35-final-20261016\report-gui\module-devices.png`
  - SHA256：`ad7f4d1ba5c69420a54a033f102b47cb5b4809b4712eeace7ebc6bc871bb78a0`；裁剪：True。

## 文档与GUI质量检查

- 使用bundled Python/python-docx生成DOCX；Windows依赖包未提供bundled LibreOffice，本轮没有调用用户安装的LibreOffice。使用独立隐藏Microsoft Word COM更新Fields/TOC并导出PDF，bundled PDFium生成PNG。
- Word实际页数12，自动目录和页码已更新；12页全部视觉复核。最后只改第4/8页截图裁剪，再次复核这两页，其余页与已复核图像逐像素相同。最终PDF/PNG仅在artifacts/p35-final-20261016/release-render作为QA，不作为新增PDF交付。
- document-qa.json记录11图号/10张不同来源/10个内嵌图像、大小和渲染方式。中文字体、标题、目录页码、表格及图片比例正常，无孤立图片页/空白页/重叠。全屏软件截图缩印后的微小技术文字需Word放大查看，正文提供管理层说明，不以截图代替操作手册。
- 本轮播放器100/125/150%及窗口缩放、专注/Esc/逐帧/播放暂停/时间轴实际GUI通过；11不同针对性用例通过（含8基础GUI、1播放器综合、2已有任务状态用例），重复复验不累加。
- QMenu此前用户已人工确认；本轮不重改主题。历史QComboBox自动化XFAIL继续保留；未宣称全部主题或长期稳定性通过。
- 原项目全表、1578模型/数据集/训练工件相等；251帧与开始时数据库登记hash相符；原视频及12历史缓存文件与此前保护清单一致。protection.json含细项。
- 无模型重训、无完整P0重测、无新的AI视频预处理；回放复用既有真实GPU缓存。未改GPU环境、引擎、解码器或数据库；PACKAGING_FREEZE=TRUE，无应用打包。
