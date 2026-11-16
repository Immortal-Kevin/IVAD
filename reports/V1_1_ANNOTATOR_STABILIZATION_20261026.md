> 当前 UI/连续标注修订见 [本轮报告](V1_1_UI_ACCEPTANCE_20261026.md)。本文件保留此前阶段记录，计数不代表最新结果。

# IVAD v1.1 Annotator 稳定化轮验收报告

记录时间（UTC）：2026-10-26T05:51:09.995038+00:00。上轮基础依据为V1_1_IMPLEMENTATION_20261026.md；本报告覆盖其后的Annotator改进，不重复架构重构或旧路线清理。

## 结论与交付边界

- 工程回归：**61 PASS / 0 FAIL**；包含真实Windows编解码、真实后台子进程和文件系统IDS交换。
- 真实GUI全流程：**NOT TESTED**。computer-use启动开发版被工具审批拒绝；没有用模拟服务调用冒充。
- 最终完整IDS包：**PASS（服务/文件层）**；重复导入幂等，69个资产、128帧、全部元数据与hash一致。
- Release Gate工程检查：**PASS**；Annotator Windows分发状态：**NOT VERIFIED**。正式安装包、签名、上传、发布继续冻结。
- 本轮没有推进NVIDIA/RF-DETR训练，没有安装第三方依赖/FFmpeg，没有更改驱动、全局Python、代理/VPN或其他AI项目。
- 当前可启动人工验收的开发版已经更新，但**不能称为已完成用户要求的真实GUI稳定性验收**。

## 本次实现

| 范围 | 本次实现 | 证据/仍欠缺 |
|---|---|---|
| 项目操作 | 项目/视频/标注/交换四页；目录可直接输入或浏览；创建/打开/关闭；设备摄像头关联显示 | 服务层PASS；真实GUI NOT TESTED |
| 矩形 | 选择、内部拖动移动、四角调整、软删除和修订；坐标限制在原图范围 | 几何保存/重新打开PASS；真实鼠标手感NOT TESTED |
| 多边形/ROI | 逐点绘制、完成/取消草稿、形状选择/平移、已有顶点拖动；ROI关联一致性校验 | 服务层PASS；不含顶点增删/复杂自交拓扑 |
| 审核 | 四种帧状态、审核结果/审核人、最新审核恢复、修改记录 | 正常/异常/未知逐项重新打开PASS |
| 后台任务 | Task.Run承担视频hash/复制、保存资产校验、IDS导入导出；抽帧保留隔离子进程；进度、取消、关闭时先取消 | 实际子进程与取消回滚PASS；真实GUI响应/关闭交互NOT TESTED |
| 抽帧范围 | 起止秒[含开始,不含结束)、间隔、1–5000新增帧上限；范围空与达到上限提示 | 精确PTS、分批续抽、重复去重和已有审核保留PASS |
| 视频来源 | 同摄像头同内容视频复用ID；保留原文件、hash、源视频ID与100ns PTS | 导入重复与源关联PASS |
| Media Foundation | 兼容首帧重协商；按显示区域处理1088编码行/1080可见行；可见尺寸真实改变仍拒绝 | H.264、HEVC、VFR、1080p实际测试PASS |
| 事务与取消 | 复制/导出检查实际字节数和hash；原子清单；写锁内资产校验；按本任务所有权清理，保留已提交引用 | 复制、解码、提交、导出、导入取消，以及晚期导入失败回滚PASS |
| IDS | 完整/增量双向、空目录恢复、重复完整/增量幂等、冲突拒绝、hash校验与回滚 | 包实际往返PASS；GUI交换仍NOT TESTED |
| Gate | 真实GUI单列；构建/测试异常立即写失败状态，不能沿用旧PASS | 最终工程PASS，发行不升级 |

## 实际视频结果

AVI、MP4(H.264)、QuickTime品牌MOV、真实Matroska MKV、HEVC均通过本机真实编解码/抽帧；VFR六个非等间隔PTS逐项一致。损坏字节流和截断真实MP4正确拒绝，原项目未被覆盖。

长视频包含真实1800样本、30分钟时长；1080p版本1920×1080、1fps、5,231,257 bytes，每60秒采30帧。编码耗时3268ms，导入/解码/保存16171ms。真实GUI响应未测，不能将这些时间当GUI性能。未测试高码率25/30fps、全天监控、多音轨/旋转/HDR、所有容器变体、跨Windows/显卡。

细节：[视频与后台实测](V1_1_VIDEO_VALIDATION_20261026.md)。

## IDS端到端结果

完整文档指纹：`fccc8f5239a225280f84ee7216fc0393d04cf498a5a2be35dd59771d33f194e2`；重导入指纹：`fccc8f5239a225280f84ee7216fc0393d04cf498a5a2be35dd59771d33f194e2`。二者相等，完整实体字段与数量包括图片关系、几何坐标、分类UUID、ROI、相机/设备、审核和修订均进入比较。所有69个资产再按字节数与SHA256验证；重复导入没有额外实体。

最终包SHA256：`dc21afb9e3a22e65f13ecc8441a1a4305cf94693a6a2743acb8c94b9be73b9d7`。这是本地测试数据交换包，不是软件发行安装包。

实体数量：

| kind | 数量 |
|---|---:|
| Site | 1 |
| Project | 1 |
| Equipment | 1 |
| Camera | 1 |
| Video | 10 |
| Revision | 155 |
| Frame | 128 |
| Fault | 1 |
| Annotation | 3 |
| ROI | 1 |
| Review | 4 |

完整A→B、增量A→B、反向增量B→A由既有回归验证；完整包/增量包重复应用保持幂等。分叉目标拒绝；同长度篡改文件必须被SHA256检查拒绝，不能仅靠尺寸或ZIP CRC。晚期提交时已有文件冲突，回滚本次已移动文件并保留预先存在文件。取消导入/导出不留下输出包或导入staging。

## 发现并修复的问题

| 问题 | 发现方式 | 处理与验证 |
|---|---|---|
| 缺少矩形选择/移动/调整、选中删除及顶点编辑 | 原代码检查 | 加入事件处理与列表选择；服务持久化测试；GUI待验收 |
| 视频hash/复制、保存校验、IDS交换同步阻塞UI | 原代码检查 | 改后台任务和流式进度/取消；实际子进程测试；GUI响应待验收 |
| 只有间隔，没有范围与明确上限反馈 | 原代码检查 | 范围/数量UI、网格采样、空范围/上限提示与回归 |
| 重复导入同源视频创建重复Video实体 | 代码检查与新增回归 | 同摄像头+内容路径复用；不增长sequence |
| 已应用的增量重放仍报基线冲突 | 原逻辑检查与回归 | 接受完全相同目标指纹，仍完整验证包与资产 |
| 基线保存默认使用ZIP扩展名 | 原GUI代码检查 | JSON基线与IDS包使用不同filter/default extension |
| 审核和选择刷新不能充分恢复上下文 | 原代码检查 | 恢复最新审核、形状选择，空项目清空旧图像 |
| 首次VFR测试得到9个CFR样本而非6个VFR样本 | 真实失败日志+容器stts检查 | 测试编码输入改NV12，避免RGB转换链改帧率；真实PTS通过 |
| HEVC首帧兼容重协商误判不兼容 | 真实解码失败日志 | 重读类型并验证可见尺寸/RGB32；HEVC通过 |
| 1080p解码缓冲对齐为1088行被拒绝 | 真实1080p长视频失败日志 | 读取显示aperture、校验步幅与裁切；1080p通过 |
| 复制/导出验证与实际写入之间可能变化 | 代码检查 | 复制后hash、导出流hash与实际长度再次验证 |
| 写锁外校验可能与失败资产清理竞争 | 代码检查 | 写锁内验证资产；清理也持锁，只删本次创建且无提交引用文件 |
| 子进程异常/取消时可能遗留任务目录 | 代码检查与实际子进程回归 | finally终止未结束子进程、所有权日志清理、保留原媒体与已提交标注 |
| 构建失败会中止脚本并留下上轮Gate状态 | Gate路径检查 | catch立即生成FAIL/BLOCKED及失败原始记录，不再沿用旧PASS |
| GUI自动化启动被审批工具拒绝 | 真实工具结果 | 保留原文、标记NOT TESTED，没有绕过或伪报PASS |

中间失败构建/测试日志与每次运行目录均保留。最终通过不覆盖早期失败记录。构建过程中的成员隐藏警告也已处理。

## 剩余阻断与部分实现

1. 真实GUI全流程和实际界面响应、关闭/取消交互 **NOT TESTED**，需要恢复computer-use权限或按指南人工验收；详细逐项见 [GUI验收记录](V1_1_GUI_ACCEPTANCE_20261026.md)。
2. 已实现已有顶点拖动，未实现顶点增删、复杂自交检查、缩放平移、完整撤销重做、类别迁移、冲突合并UI和视频播放时间轴。
3. 当前是可取消单任务，未实现持久任务队列/自动崩溃续传。正常取消/异常回滚已测；硬杀/断电、资产移动与所有权日志写入之间的极小孤立文件窗口未验收。不会自动清理未知历史任务或用户业务资产。
4. 长视频测试为低帧率合成输入；高码率/高帧率/全天监控、海量项目、多音轨/旋转/复杂编码组合、干净Windows和跨机仍未验收。当前保存仍会重新核对全项目资产，工作转到后台但大项目可能耗时。
5. 真实禁网、正式安装/升级/卸载、签名/发布未做。正式分发冻结持续；没有以工程PASS宣告Windows发行READY。
6. Full/NVIDIA保留原先BLOCKED，本轮只随既有Gate运行原回归，没有推进训练或安装训练依赖。

## 可复核证据

- 最终构建日志：`governance/evidence/build-test-20261026-134738.log`。
- 最终测试：`build/test-data/20261026T054739-eb3aa46f/results.json`，61 PASS / 0 FAIL。
- 精确媒体与IDS证据：`build/test-data/20261026T054739-eb3aa46f/media-fixtures.json`、`hevc-environment.json`、`long-video-metrics.json`、`worker-process.log`、`ids-roundtrip.json`。
- Gate：`governance/evidence/release_gate.json`、`governance/RELEASE_READINESS.md`；GUI工具原文：`governance/evidence/windows_gui_attempt.json`。
- 当前开发EXE SHA256：`9a04888530891fe8cd495498df38a6f49ca95d65131588bca3e13931b53dbaab`。
- 应用后续人工操作日志：`build/logs/annotator.log`。
- 官方API依据：`governance/evidence/media-reference-sources.json`。未把外部SDK参考头文件编入或随附产品。

## 人工验收启动

双击 `C:\Users\kevin\Desktop\IVAD Project\IVAD_Platform_v1.0\build\dev\Ivad.Annotator.Dev.exe`。

操作顺序：项目→设备/摄像头→视频范围抽帧→标注与审核→关闭重新打开→IDS导出/导入空目录。详细步骤和测试素材入口见 [开发版人工验收指南](../docs/ANNOTATOR_QUICKSTART.md)。当前无需用户安装任何依赖或改变系统配置。

## 最终回归逐项结果

以下均为实际服务/文件/编解码/子进程或既有私有接口测试，不是鼠标GUI测试。

| 测试 | 状态 |
|---|---|
| project/create-reopen | PASS |
| entities/equipment-camera-fault | PASS |
| video/import-real-generated-avi | PASS |
| video/media-foundation-extract-real-PTS | PASS |
| video/reextract-idempotent | PASS |
| annotation/box-save | PASS |
| annotation/polygon-and-ROI | PASS |
| review/state-and-history | PASS |
| validation/duplicate-ID | PASS |
| validation/dangling-reference | PASS |
| validation/outside-coordinate | PASS |
| validation/unknown-state | PASS |
| package/full-roundtrip | PASS |
| package/snapshot-immutable | PASS |
| package/incremental-roundtrip | PASS |
| package/bidirectional-incremental | PASS |
| package/conflict-no-change | PASS |
| package/corrupt-hash-rollback | PASS |
| package/path-traversal-rejected | PASS |
| package/undeclared-files-rejected | PASS |
| package/case-collision-rejected | PASS |
| storage/concurrent-writer-conflict | PASS |
| full/adapter-rejects-unsupported-polygon | PASS |
| full/coco-stable-fault-map | PASS |
| full/training-fails-closed | PASS |
| full/latest-review-wins | PASS |
| storage/windows-reserved-paths | PASS |
| video/import-same-camera-idempotent | PASS |
| video/range-end-exclusive-PTS | PASS |
| video/range-invalid-no-mutation | PASS |
| video/range-past-end-empty-not-codec-error | PASS |
| video/resume-limit-without-duplicates-or-label-loss | PASS |
| video/cancel-decode-no-partial-frames | PASS |
| video/retry-after-cancel-retains-existing | PASS |
| geometry/edit-box-polygon-ROI-reopen | PASS |
| geometry/soft-delete-retains-history | PASS |
| geometry/invalid-edit-no-disk-change | PASS |
| review/all-states-reopen-latest | PASS |
| validation/PTS-units-and-duplicate | PASS |
| package/full-all-fields-hashes-idempotent | PASS |
| package/delta-repeat-no-duplicates | PASS |
| package/same-size-SHA256-tamper-rejected | PASS |
| package/late-commit-failure-rolls-back-owned-files | PASS |
| package/export-cancel-cleans-temp | PASS |
| package/import-cancel-rolls-back | PASS |
| video/import-copy-cancel-cleans-temp | PASS |
| video/corrupt-input-fails-preserves-project | PASS |
| video/H264-MP4-real-encode-decode | PASS |
| video/truncated-real-MP4-fails-without-loss | PASS |
| video/VFR-H264-exact-PTS | PASS |
| video/MOV-QuickTime-brand-H264 | PASS |
| video/MKV-Matroska-H264 | PASS |
| video/long-30min-H264-range-and-PTS | PASS |
| video/long-1080p-30min-H264 | PASS |
| worker/actual-child-process-range | PASS |
| worker/actual-child-cancel-rollback | PASS |
| worker/corrupt-input-recovery | PASS |
| storage/cleanup-preserves-committed-assets | PASS |
| storage/cancel-at-commit-cleans-created-assets | PASS |
| video/HEVC-MP4-actual | PASS |
| package/final-complete-project-all-fields-assets | PASS |
