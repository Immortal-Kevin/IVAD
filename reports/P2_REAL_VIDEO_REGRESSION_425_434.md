# P2 指定真实录像回归：425–434 秒

日期：2026-10-14（Asia/Shanghai）。基于 f0814ed 增量修复，仅 P2；无训练、推理、报警或 P3–P6 开发。

## 来源与保护

指定原录像：`E:\IVAD Project\测试1号\给煤机视频\1202 1204给煤机_20260323163801\1202 1204给煤机_20260210000014-20260211001514_6.mp4`

原文件 SHA256（测试前后相同）：`54da1f9dcf30af9b6fe6dc40bec906ab97c40a8a06f149757034f233e9d0c5a4`。原文件 536,870,992 bytes；仅读取，无修改、覆盖、删除或转码替换。

原用户项目：`E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2`。只读 SQLite 检查发现 7 条媒体、1 张已有候选图片、1 份标注文档/7 次修订、0 ROI；没有假定原项目已有45张，也没有清理任何历史图片/审核。

为保证历史数据逐字节不变，未直接在原 DB 写回。最终创建独立项目“测试1号—P2独立回归批次”，描述明确全部标注是软件测试夹具；只通过 REFERENCE 导入指定第6段录像，不测试或解码其他录像。

批次：`P2-WORKFLOW-425-434-1ff4fafcaa`

项目目录：`E:\IVAD Project\测试1号\P2-WORKFLOW-425-434-1ff4fafcaa\IVAD-7c86a12b-fb6a-405c-a364-2d9da431f69c`

本轮保护清单 12,133 个文件（指定源、原项目已有文件、旧 artifacts 与旧报告归档），校验变化数 0。保护读取只做哈希，不用于其他录像业务测试；未进入原视频源文件夹扫描其他录像。

## 抽帧与解码

真实 MediaPage GUI 设置：起点425.000、终点434.000、固定间隔、0.200秒/帧、上限100、PNG、原分辨率。按钮“确认范围并后台抽帧”通过现有任务系统执行。没有私下绕过控件设参数。Qt 自动化仅替换操作系统文件选择返回值及确认 Yes；实际导入、解码、任务、持久化、画布均为现有业务实现。

实际视频为 MPEG 容器/HEVC，1280×720，time_base=1/90000；nominal_fps未知，不据此推算。stream origin_us=81272186444。

| 项目 | 实测 |
|---|---|
| 采样区间 | [425000000,434000000) µs |
| 请求间隔 | 200000 µs |
| 实际帧数 | 45 |
| 实际相对时间范围 | 425.010000–433.836000 秒 |
| 原始绝对 PTS 范围 | 81697196444–81706022444 µs |
| 图片尺寸 | 全部1280×720 |
| PTS唯一 / SHA256 / media关联 | 全部PASS |
| 与起点顺序解码同PTS逐像素对照 | 45/45一致 |

未伪造或重复补帧；间隔取每个请求目标后第一张真实显示帧，受视频PTS及帧级偏差影响，不等于所有间隔都精确200ms。文件哈希可重复（静止画面合法），不据此删除真实不同PTS。

额外发现并修复两项 P2 问题：抽帧原 end-inclusive 改为半开区间；MPEG 索引即使 backward=True，也会请求425秒却落到434.475秒，或者落到不能正确重建HEVC参考画面的地点。MPEG/MPEGTS 改为从文件起点顺序解码到目标，其他容器检查实际第一帧PTS并回退 seek。播放器/抽帧/片段共用 reader；MPEG逐帧后退也采用安全顺序解码路径。源不转码、不改索引。

首次空抽帧尝试 FAIL（新项目保留）。随后粗索引回退尝试虽然45帧/操作通过，但45帧像素与顺序解码不符，判为FAIL，不作为验收样本；完整失败批次 `P2-WORKFLOW-425-434-3c714f14f9` 保留。最终上述1ff4fafcaa批次为修复后验收数据。失败JSON和对照在 real-coarse-seek-failed-results.json / decode-coarse-seek-failed-comparison.json，最终对照在 decode-sequential-comparison.json。

## 标注、导航和恢复

| 验证 | 结果与边界 |
|---|---|
| 无camera/无ROI，正常+无框保存/下一张 | PASS，第一张NORMAL/空objects/DRAFT |
| “落料口堵煤”类别+矩形框保存/下一张 | PASS，仅第二张明确TEST FIXTURE；位置只用于交互测试，不推断真实故障 |
| 无camera选择camera ROI作用域 | PASS，当前视频作用域回退/不可用项禁用，提示非阻断 |
| 创建视频ROI及正常保存 | PASS，第三张NORMAL/空目标；ROI单独保存，并在同视频图片共用 |
| 有ROI时异常目标保持 | PASS，原故障框坐标/类别未改变 |
| 第一张至最后一张，再倒序至前面 | 全部45张可打开，PASS |
| 撤销 / 重做 | 矩形目标删除/恢复一致，PASS |
| 关闭软件，新服务/主窗口重开 | 三份测试文档 payload/status/revision 完全相同，PASS |
| 独立OS进程重开 | 正常标签、空目标、三文档恢复 PASS；原生鼠标下一张确认第二张框/堵煤类别；原生上一张后续因目标窗口不可用未完成，但Qt倒序覆盖PASS |
| 视频-图片-标注关联 | ID/PTS/哈希检查PASS；无错误生成正常图目标框 |

最终真实 GUI 用例 1 passed in22.59s。最终重点套6通过、完整回归91通过，详见P2_TEST_RESULTS.md。

本轮没有对现场故障作人工确认。NORMAL/ABNORMAL是软件测试夹具，仅3张有测试文档且保持DRAFT；其余42张UNKNOWN、无目标，不批量判断堵煤。真实画面是否正常、实际堵煤区域和人工审核质量 **NOT TESTED / 待现场人员确认**。软件功能、标注操作、工业故障真值三个结论严格区分。

## 截图与证据

1. [GUI范围及参数](../artifacts/p2-workflow-fix-20261014/real-extraction-settings.png)。
2. [正常无框、无ROI保存](../artifacts/p2-workflow-fix-20261014/real-normal-no-roi.png)。
3. [“落料口堵煤”测试夹具框](../artifacts/p2-workflow-fix-20261014/real-abnormal-TEST-FIXTURE.png)。
4. [ROI与目标独立](../artifacts/p2-workflow-fix-20261014/real-roi-independent.png)。
5. [独立进程重开](../artifacts/p2-workflow-fix-20261014/native-process-reopened.png)。
6. [工具popup](../artifacts/p2-workflow-fix-20261014/popup-tool.png)、[整帧标签popup](../artifacts/p2-workflow-fix-20261014/popup-image_tag.png)、[来源popup](../artifacts/p2-workflow-fix-20261014/popup-source_filter.png)；其余菜单见样式报告。

截图来自真实Qt渲染，无AI生成界面；全部保持本地，不上传现场图像。真实GUI本体虽沿用Human Generated存储来源，整个项目描述和报告明确TEST FIXTURE，不作为人工审核训练真值。

## 限制与结论

本轮两项紧急修复的软件功能验收 PASS，可继续P2人工测试；不构成工业故障确认或P3授权。无migration，无新增依赖。MPEG顺序定位可能耗时，当前约425秒定位的完整解码对照约8秒；小时级/4K性能未测。测试日志仍有Windows COM 0x8001010d诊断，进程退出0且用例通过，未宣称根因解决。旧便携包未更新，原分发BLOCKED继续有效。
