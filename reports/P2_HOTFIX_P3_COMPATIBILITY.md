# P2_HOTFIX_P3_COMPATIBILITY

日期：2026-10-15。源码1.0.0-P3-Dev.2，Schema0007。PACKAGING_FREEZE = TRUE。证据目录：artifacts/p2-hotfix-p3-20261015。

**本轮Hotfix：PASS。P3已有成果保留，兼容性：PASS。**

## P3 当前状态与兼容性

返工前：275de69已经完成P3源码工程并PASS，包含简易/高级GUI训练、独立CUDA Worker、数据预检、YOLO26n/YOLO11n训练/验证/ORT、取消/恢复、模型仓库/人工审批/回滚。本轮暂停新增业务，未重建或重启P3，不重复训练。

已有冻结数据集可读，preflight train2/val2/test2；原有2条训练、1个模型及其指标/来源绑定保持；训练GUI可打开、GPU Worker探针实际识别RTX5070Ti并验证CUDA张量，CPU-only AI拒绝。没有重新生成P0基准或完整模型训练。P3业务源文件保持，数据库/媒体/人工标注服务仅为授权Hotfix增量修改。

标注“已标注”不写REVIEWED，不等同训练准入。已审核内容编辑保留原审核记录但新增复审标志，新版本必须明确复审；既有冻结快照继续按其冻结时审核真值工作，不能随当前编辑静默变化。

阶段结论分开：P2历史验收PASS不变；本轮P2 Hotfix PASS；P3既有源码工程PASS且兼容回归PASS。因P3已完成，无未完成原计划需要恢复，不扩展新P3功能。按指令末条停止等待用户审阅，不进入P4–P6。
## 迁移及保护

新增0007_p2_hotfix，0006之后只追加cameras.details与media_assets.lifecycle两列JSON，默认{}；无表重建、不重置数据库、不批量修改旧Annotation/DatasetVersion/TrainingRun/ModelVersion行。Frame.handling复用完成状态/复审提示；新动作才写入，不做旧审核状态批量替换。Camera启用默认兼容旧记录，编号/位置/设备为可选details字段；生命周期保留hidden/removed/history/revision/清理阶段。

原用户数据库与已有P3项目数据库在修改测试前用SQLite backup制作可验证备份（均0006），备份integrity ok；P3项目副本升级07后，所有旧列逐行相同，包含6标注/6修订、1冻结版本/6样本、2训练记录、1模型版本；模型文件hash和预检正常。另在原用户备份副本验证全部旧列不变，并用独立旧Camera夹具验证UUID/名称/修订/history不变。原用户数据库没有升级/写入。

最终保护14647文件、变化0，覆盖原用户资料、既有P0/P1/P2/P3测试工件、权重、日志、验收报告及旧dist；.venv-p1与.venv-nvidia pip清单一致，无安装、驱动、CUDA、全局Python或其他AI项目变更。训练Worker、训练/模型服务、训练GUI及Job Manager业务源码未改。旧P2/P3验收报告原样保留，不用本轮结果覆盖历史。
## 测试结果

- 主回归full-final.xml：131 passed / 0 failures / 0 errors，101.284秒。含原121项及本轮10项P2 Hotfix用例；其中原20项P3专项全部通过。旧GUI测试改为经“数据集管理”的真实审核入口，未删除原保存/恢复/导出断言。
- 主套之后新增旧Camera迁移单例：camera-migration.xml，1 passed；增强GUI COPY清理确认：import-cleanup-retry.xml，1 passed，原始合成源字节不变。两者不冒充一次132项完整主套。
- 最后列表绘制修正后针对性GUI回归gui-painter-final.xml：6 passed / 0 failed，13.86秒（主套已有用例子集，不重复计数）。
- 实际P3工件副本服务/GUI兼容：p3-compatibility.xml，1 passed / 0 failed，8.15秒；用户数据库备份副本迁移user-migration.xml，1 passed / 0 failed，0.77秒。
- 最终100%/200%显示：layout1080p.xml、layout200-event-verified.xml，各1 passed，分别DPR1/DPR2。100%实际1920×1080与1440×900窗口，高DPI为1440×900逻辑窗口。真实Qt截图在layout-100-1080p-verified、layout-200-event-verified。逐一展示未选/已选/悬停/禁用，核对像素变化；没有生成虚构软件界面。
- 初期失败保留：两个旧迁移测试假定新增列数不变（保留旧列逐项不变断言，并显式验证新列默认值/旧阶段迁移）；一项测试缺少monkeypatch夹具；隐藏后列表选择保留导致无法重新选中（实际GUI修复）；导入增强测试未等列表刷新；DPI驱动命名解析及QTest移动不派发viewport事件。没有把初期运行写为0失败。
- 悬停最终采用明确Qt MouseMove/Leave事件与真实widget像素核对；原生Windows物理鼠标/多屏切换未单独自动化验收。普通QTest鼠标移动未派发事件的失败日志保留，不伪装原生输入已通过。
## 限制与风险

- 不做级联物理删除。COPY清理仅对无下游依赖、项目media目录内且hash一致的副本；采用先隔离重命名、数据库记录、再清理，异常/强杀可能留下隔离文件或清理待核对状态，不保证跨文件/SQLite绝对原子恢复。REFERENCE源始终只读。
- 本轮不重新认证工业准确率、长期跨机、Intel、GPU OOM或完整训练；原P3许可/稳定性限制保留。原生自动化与Qt历史访问冲突根因仍未定位，本轮Qt回归未复现。
- 高DPI验证有明确逻辑尺寸，不承诺原有1040×660最小窗口在1080物理分辨率200%缩放下完全适配所有页面。
- PACKAGING_FREEZE = TRUE：没有构建/更新EXE、Portable、Setup、签名、依赖重打包或上传；旧包仍旧且不能打开0007数据库。用启动IVAD.cmd运行源码，首次打开旧项目自动先备份再迁移。Word/PDF不重制。
