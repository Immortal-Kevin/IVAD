# P2 Annotation & Camera Dataset Hotfix 回归验收

日期：2026-10-15；基线 c79d50d；Schema 0008 保持；PACKAGING_FREEZE = TRUE。

## 验收结果与阶段

软件功能与真实用户数据检查 PASS；历史测试截图保全有下述已披露例外，不能宣称全部历史证据原样保留。最终主回归 99 passed / 0 failed（71.64 秒）；200% GUI 2 passed / 0 failed；最终补充服务/GUI 专项 13 passed / 0 failed（15.50 秒），配置引用保护另 1 项通过。新增两个不同的提交后日志故障用例，加上 ROI 旋转/非法坐标两个不同用例，共 103 个不同用例，DPI 用例为重复验证，不重复计入独立用例数。

首轮主回归 98 passed / 1 failed：旧夹具将无框、无整帧故障类别的异常当作已完成，和本轮要求冲突；修正为有明确类别的合法整帧样本后完整复验通过。更早的新 GUI 测试暴露 waitUntil 返回 None 被当作成功的问题，已改用 bool；真实 GUI 流程最终通过。中间失败保留在原 XML，没有覆盖为全绿。

## 功能覆盖

| 项目 | 结果 |
|---|---|
| 正常无框保存后完成，提交前/保存失败不完成 | PASS |
| 真实 Qt 矩形、多边形保存后 ABNORMAL / 已标注 | PASS |
| 完成与审核分离，P3 准入及泄漏校验 | PASS |
| 单帧、批量软剔除及恢复，内容/修订保留 | PASS |
| 已冻结引用不破坏，manifest 字节不变 | PASS |
| 全部跳过弹窗及持久结果反馈 | PASS |
| 批次移出/移回，训练资格与剔除独立 | PASS |
| 摄像头筛选清勾选，隐藏 ID 不进操作 | PASS |
| 多摄像头默认拒绝，独立入口二次确认 | PASS，隔离 GUI 夹具验证默认拒绝及显式入口两次确认调用；确认返回由测试桩给出，不代表现场人工批准 |
| ROI 自动选择、同摄像头复用、视频优先/冲突提示 | PASS |
| 比例/旋转/几何保护，历史 ROI 保留 | PASS，比例/旋转元数据/非法坐标隔离夹具覆盖；不冒充现场旋转录像验收 |
| 正常库/故障查询与多对多模型配置接口 | PASS |
| 摄像头持久化、项目隔离、事务回滚、队列 | PASS |
| 真实项目副本 GUI 来源核对 | PASS，旧规则 4 张全部拒绝得到复现 |

## 真实项目保护

只读原库：`[本地路径]`，Project UUID `fc4276bc-6919-42c6-8e56-234a9b9bd3e2`。当前 Schema 0008，integrity_check=ok；本轮快照含 3 摄像头、251 帧、22 标注。该状态不同于前轮记录，采用本轮可信快照，不把用户后续操作误判为本轮修复结果。

一致性备份 `artifacts/annotation-camera-hotfix-20261015/real-project-readonly-backup.sqlite`，SHA256 `f0d164ca9163d6b6b2d947796f59ee6833aac542baefe295fcf06e7b43a73c1d`。真实原库 SHA256 `a32fdeb359e0060146a24a7ef61b3a1d9a33b98bf65e5b414fd98cda4a97d850`，最终复核一致。本轮所有会改变帧状态或标注的测试在独立测试库，现场 GUI 通过隔离副本展示，没有在原项目执行 CREATE/UPDATE/DELETE、审核、批量剔除、关联修复或迁移。

真实副本仅复制展示所需的两张图片，不复制或扫描数小时录像。截图中其余帧显示 Missing 是副本未复制全部图片所致，不能据此宣称真实项目图片缺失。没有把现场图中的故障位置当作已确认工业真值。

上轮旧保护清单 14,647 文件重算：14,646 一致，1 项是本轮开始前已变化的真实项目数据库；本轮自身快照到最终哈希一致。旧清单早于上轮摄像头修改和本轮用户新增内容，不能当作本轮前快照。

### 历史测试证据例外

回归执行旧 test_camera_integrity_v2_gui 时，其固定路径覆盖了上轮 `artifacts/camera-integrity-v2-20261015/two-cameras-edit.png` 和 `create-mode.png` 两张测试夹具截图。没有原字节备份，不能原样还原；它们不再能用作上轮原始截图。已明确告知用户，并修正测试支持 IVAD_CAMERA_EVIDENCE，默认输出 pytest 临时目录；本轮后续指定独立证据目录。旧报告文本、数据库备份、真实用户标注、模型和冻结工件未由该用例修改。详见 data-protection-final.json。不能隐去这项偏差。

## 原始证据与截图

目录：`artifacts/annotation-camera-hotfix-20261015/`。

- final-regression-fixed.xml：99 项最终主回归。
- gui-high-dpi-final.xml：200% 专项 2 项。
- final-targeted.xml：最终13项服务/GUI复核，含新日志故障、旋转及非法坐标用例；config-reference-final.xml：模型配置引用保护1项复核。
- real-readonly-before.json、real-copy-gui-validation.json、real-copy-old-exclusion-preview.json、data-protection-final.json。
- [正常保存](../artifacts/annotation-camera-hotfix-20261015/normal-saved-status.png)、[异常保存](../artifacts/annotation-camera-hotfix-20261015/box-saved-status.png)、[批量反馈与摄像头筛选](../artifacts/annotation-camera-hotfix-20261015/annotation-camera-filter.png)、[现场只读副本](../artifacts/annotation-camera-hotfix-20261015/real-copy-source-display.png)。另有对应 dpi2 图。

截图为实际 Qt 抓图，无合成界面。标准测试设置 QT_SCALE_FACTOR=1、QT_FONT_DPI=96；高 DPI 为 scale=2。左右工作区有原生滚动容器，较低逻辑高度通过滚动访问按钮。

## 文件与文档

业务/GUI：annotation_page.py、annotation_service.py、media_service.py、dataset_service.py、model_service.py、camera_service.py。新增 3 个测试文件，更新旧测试的两处过时夹具/断言及截图输出路径。未修改 CUDA Worker、训练执行代码、权重或环境。无 Migration。

报告：[批量操作](P2_BATCH_EXCLUSION_HOTFIX.md)、[完成状态](P2_ANNOTATION_STATUS_AUTOSYNC.md)、[ROI 关联](P2_CAMERA_ROI_ASSOCIATION.md)、[数据/模型关系](P2_CAMERA_MODEL_DATA_ARCHITECTURE.md)。同步更新 DECISIONS、ARCHITECTURE、当前进度和两份标注 Markdown 指南，没有重制 Word/PDF。

P3 既有功能兼容测试通过；此前 P3 已完成，没有新增未完成任务可恢复，故不重复训练或开发。停止待审，不进入 P4/P5/P6。PACKAGING_FREEZE = TRUE，未构建、更新或分发 EXE、Portable、安装包。
