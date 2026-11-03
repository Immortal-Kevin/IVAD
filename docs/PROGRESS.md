# IVAD v1.1 开发进度（2026-10-26）

旧Intel P0未完整验收，历史报告不变成NVIDIA进度。用户v1.1授权已取代旧路线，Ultralytics退休；当前产品为Annotator、IDS、Full三个边界。

## 已完成

- 清理3个Ultralytics安装包和专用权重/代码/实验工件；记录逐文件hash。
- 追加移除不符合新政策的旧NumPy二进制、OpenCV/绘图/build实验副本；旧AI环境退休。
- 建立B.1政策、永久Release Gate、依赖/候选二进制和许可扫描，以及全部要求的治理文档。
- IDS1.0数据模型、验证、媒体hash、修订、完整/增量双向交换、基线冲突检测和失败回滚。
- 独立WPF开发版：项目/设备/摄像头、视频复制与Media Foundation抽帧、真实样本时间、矩形/多边形/ROI、状态/审核/修改记录、故障图库、IDS导入导出。
- x64开发编译；基础轮27项测试已扩展，最新计数见Release Gate。真实WPF启动与渲染继续验证；不声称真实鼠标操作通过。
- 本轮增加矩形选择/移动/四角调整/软删除，多边形与ROI顶点拖动、关联显示与最新审核恢复。
- 视频/hash/复制/保存校验/IDS交换移到后台；抽帧保留独立进程、支持范围/数量/进度/取消与失败重试；重复视频、重复PTS、重复增量包幂等。
- AVI/H.264 MP4/MOV/MKV/HEVC、真实VFR PTS及30分钟1080p合成视频、损坏/截断输入均已实测；包完整往返、同长度hash篡改、晚期提交回滚有真实测试。
- RF-DETR1.11.2[train]递归解析88个固定候选，Python3.12/Windows x64标签匹配与闭包约束复查；5个小wheel实际hash/许可证审查。无训练栈安装或权重下载。
- Full私有IDS→COCO矩形适配器和阻断式训练接口。

## 部分实现/未验证

GUI核心服务和实际子进程已测，真实鼠标完整操作仍NOT TESTED（computer-use启动被工具审批拒绝）。后台任务已实现，但真实GUI响应/取消/关闭手感没有鼠标验收证据。1080p长视频为1fps/30分钟合成素材，不能外推高码率25/30fps全天监控或所有编码变体。完整撤销重做、顶点增删/自交拓扑、缩放平移、类别迁移、逐字段冲突合并UI、训练分组拆分仍未完成。跨机、真实断网、安装升级卸载、崩溃断电恢复尚未验收。

## 状态

Annotator：NOT VERIFIED。Full/NVIDIA：BLOCKED。正式安装包、签名、公开与分发冻结持续有效。

详细证据：governance/RELEASE_READINESS.md、RELEASE_BLOCKERS.md、LEGACY_CLEANUP_REPORT.md；旧状态记录见docs/history/。

最新详细报告：reports/V1_1_ANNOTATOR_STABILIZATION_20261026.md；视频与GUI证据分别在同目录的V1_1_VIDEO_VALIDATION_20261026.md、V1_1_GUI_ACCEPTANCE_20261026.md。

## 2026-10-26 最新UI/人工验收修订

标准标题栏/退出、自适应三栏、主目录层级创建/检测/旧项目原地打开、导入与抽帧拆分、实际总数进度、图片工具栏/设备摄像头上下文、管理员结果显隐、保存审核后下一帧并保留故障/工具、统一IDS命名与防覆盖已实现。73项服务/真实媒体测试与21项WPF内部控件/合成布局检查通过。真实GUI读取仍被工具审批拒绝，NOT TESTED；分发冻结不变。

本轮报告reports/V1_1_UI_ACCEPTANCE_20261026.md及governance/evidence/ui-revision-delivery.json取代旧报告的当前计数。未推进训练端。

## 2026-10-26 双阶段UI/UX（最新）

完成视频与抽帧/标注与审核两个主Tab、精简左导航、独立项目与IDS页面、新配色与下拉/列表/按钮样式。抽帧参数与审核字段分离；低频功能折叠；固定保存下一帧、上一帧/下一帧、中文状态、原视频播放/暂停入口及抽帧预览。

73项服务/媒体、26项WPF内部控件/合成布局通过，工程Gate PASS；真实GUI/视频播放器兼容性仍NOT TESTED。未改IDS格式、许可证或分发冻结。当前报告reports/V1_1_DUAL_STAGE_UI_20261026.md，固定批次见governance/evidence/dual-stage-ui-delivery.json。

## 2026-10-26 连续标注操作条（最新）

预览右下集中保存并下一帧/标记正常/箭头导航/进度；Ctrl+S无冲突，统一自动正常/异常保存与成功后换帧。保留工具/类别，忙碌防重复，末帧轻提示，草稿不丢弃；列表短标签、顶部来源及已确认统计。显式未知等状态仍可在折叠区保存。

73项服务/媒体与37项WPF内部/合成布局PASS，工程Gate PASS；真实鼠标/物理Ctrl+S NOT TESTED。当前报告reports/V1_1_ANNOTATION_ACTIONS_20261026.md与固定证据governance/evidence/annotation-actions-delivery.json。分发冻结不变。

## 2026-10-26 一次性便携测试交付（最新）

完成Windows x64 Portable重新编译、明确.NET Framework4.8+外部运行条件、白名单12文件ZIP、实际许可证/二进制/隐私审计与独立TEMP部署测试。最终dist/IVAD-Annotator-v1.1-win-x64-portable.zip；A材料PASS，B本机内部/实际文件媒体13项PASS，C其他电脑NOT TESTED。真实GUI/物理快捷键仍被工具审批拒绝。打包后73+37工程Gate PASS。授权CONSUMED_FROZEN，没有自动公开/上传或推进Full。

修复自调用开发EXE名和日志路径假设。详情reports/V1_1_PORTABLE_DELIVERY_20261026.md。
