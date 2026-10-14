# P2 当前测试结果：紧急标注/样式修复

日期：2026-10-14（Asia/Shanghai）。基于 f0814ed 增量修复，仅 P2；无训练、推理、报警或 P3–P6 开发。

## 结果

| 测试 | 实际结果 |
|---|---|
| 最终完整 tests 套 | 91 passed，39.16s；full-final.xml / full-final.log |
| 追加MPEG guard后最终重点套 | 6 passed，4.54s；focused-final.xml / focused-final.log |
| 独立真实录像GUI | 1 passed，22.59s；real-final.xml / real-final.log |
| 全部下拉项100%/深浅调色板 | 1 passed，6.83s；style-all-100.xml |
| 全部下拉项200%/深浅调色板 | 1 passed，8.19s；style-all-200.xml |
| 45帧顺序解码逐像素对照 | 45/45一致，decode-sequential-comparison.json |
| 独立进程重开 | PASS，native-persistence.json；原生Next完成 |
| 项目/原视频/旧证据保护 | PASS，protection-after.json：12133文件，changed=[] |
| P0与GUI包版本 | PASS，environment-preservation.json，未安装/升级任何依赖 |

完整套91包括原86项与5项新增。最后新增MPEG禁止索引seek测试后重点6项均通过；所有最终唯一普通测试92项都执行过，但不能称“最终完整套92”，也不将重复/DPI/真实GUI测试简单相加虚增总数。最终生产源码在完整套前已固定，此后只增测试和报告。

覆盖视频COPY/REFERENCE导入、播放/定位、固定/变化抽帧、片段保存/取消/异常范围、标签/目标框/多边形/ROI、坐标/撤销重做、数据集快照导出、项目迁移/恢复、任务/日志、设备与Lite拒绝AI。故障流程夹具用于软件回归，不用于现场准确率结论。

## 失败及未解决事项

真实视频第一次范围抽帧0张；第二次粗索引回退得到45张但画面像素错误；两者均判FAIL并保留各自新项目/失败对照。最终MPEG顺序解码修复后通过，不清理失败批次或历史用户数据。

Windows测试进程仍打印“Windows fatal exception: code 0x8001010d”COM诊断和栈，随后用例全部完成、退出码0；与此前打包/指南阶段现象相同。未定位根因，不能将用例PASS当作长期稳定性PASS。实际独立Qt窗口正常显示/恢复，原生Previous复核因目标窗口不可用未完成；自动Qt前后全45张覆盖通过。

真实工业正常/堵煤位置没有现场人员人工确认；只测试类别与绘制操作，全部测试夹具DRAFT；42张未标UNKNOWN。跨电脑/混合DPI/小时级MPEG定位性能/4K等NOT TESTED。旧便携EXE不包含本轮修复，未重打包，原分发/许可及历史保护事故的BLOCKED报告保持原址不改。

## 保护与重现

输出仅 artifacts/p2-workflow-fix-20261014/ 和 E:/IVAD Project/示例项目/P2-WORKFLOW-425-434-*/；原用户项目数据库只读检查，既有1张抽帧、标注7修订、媒体7条不写入。源原录像前后SHA相同。报告更新前旧P2_TEST_RESULTS.md与P2_ACCEPTANCE.md完整复制到reports/history/P2_before_workflow_fix_20261014/，有SHA256.json。

回归环境变量IVAD_TEST_EVIDENCE_DIR、IVAD_P2_GUI_EVIDENCE_DIR、IVAD_P2_ADJUSTMENT_EVIDENCE_DIR显式指向本轮目录；初次完整套误用了IVAD_P1_EVIDENCE_DIR但现有安全默认写独立test-runs，没有回写旧证据。最新完整套已纠正三个变量。现有 P0/P1/P2 环境、驱动、CUDA、全局Python未修改，无新增schema。

工程“启动IVAD.cmd”重启加载新源码。开发者可运行tests/test_p2_workflow_fix.py；真实/DPI测试驱动位于本轮artifacts目录，仅显式运行，正常软件启动不运行测试、不会自动导入真实录像。详细源/PTS/每图哈希/任务ID/夹具坐标见real-results.json；隐私素材不纳入Git。
