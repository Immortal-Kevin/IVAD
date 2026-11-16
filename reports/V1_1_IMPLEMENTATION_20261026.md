> 当前 UI/连续标注修订见 [本轮报告](V1_1_UI_ACCEPTANCE_20261026.md)。本文件保留此前阶段记录，计数不代表最新结果。

> 后续更新：本报告保留基础轮历史；当前Annotator稳定化结果见 [本轮验收报告](V1_1_ANNOTATOR_STABILIZATION_20261026.md)。旧27项计数和同步IO限制不再代表最新代码。

# IVAD v1.1 重构基础轮交付报告

日期：2026-10-26。当前项目根保持IVAD_Platform_v1.0；产品与授权基线为v1.1。原Intel P0未完整验收；本轮没有继续旧训练，也没有借用其他NVIDIA项目的完成状态。

## 实际完成

1. 清理Ultralytics三项安装依赖、相关官方/实验权重、IR、专用脚本、配置/字体、样例和专用实验日志。删除前记录745个文件、48,142,514 bytes的路径/hash/用途；另记录并移除4,549个旧NumPy/OpenCV/绘图/build相关文件。详细范围与原因见治理清理报告。
2. 按Policy B.1建立永久项目规则、实际环境/缓存wheel/EXE引用检查和A–L Release Gate，生成用户要求的9份治理材料及原始证据。
3. IDS1.0包含全部11类实体、稳定UUID、PTS来源、几何、审核/修订、文件hash、完整包与增量双向交换、冲突拒绝、staging回滚及不可覆盖快照。
4. 自研C#/WPF独立Annotator开发版，Windows系统组件为外部先决条件，没有Python/AI或第三方GUI运行依赖。可创建项目、建立设备/摄像头关联、复制视频、后台抽帧、预览、画框/多边形/ROI、保存状态/审核、查看记录与故障图库、交换IDS包。
5. Full保持私有源代码边界；实现IDS→COCO矩形数据适配，保留Fault UUID映射，读取最新审核。训练接口明确BLOCKED，不下载模型、不安装RF-DETR。
6. 对官方RF-DETR1.11.2[train]完成88项候选递归元数据解析，核对Windows x64/CPython3.12 wheel标签和最终依赖约束；解析未解决错误0。5个小wheel已按发布方SHA256检查LICENSE/METADATA，未安装。具体训练二进制、权重及CUDA没有获准。

## 测试结果

| 项目 | 结果 | 证据范围 |
|---|---|---|
| Windows x64开发编译 | PASS | 系统C#编译器；PE machine=AMD64；非安装包 |
| 自动测试 | **27 PASS / 0 FAIL** | build/test-data/latest.txt指向本轮结果；包含负向安全/冲突测试 |
| 真实视频解码 | PASS | 自生成6帧AVI，经Windows Media Foundation读取；第二帧100ns时间5,000,000、pts_us=500,000 |
| 标注/审核/修订 | PASS（服务层） | 矩形、多边形、ROI、状态与持久化 |
| IDS完整/增量双向 | PASS | A→B、B→A；hash与数据一致 |
| 损坏/冲突/攻击包 | PASS（拒绝） | hash、路径越界、大小写重复、未声明文件、基线分叉；失败不提交 |
| 并发写保护 | PASS | 旧清单hash发生变化则拒绝覆盖 |
| WPF启动 | PASS（实际启动） | 开发窗口实际运行与渲染截图 |
| UI工作流 | PASS（模拟） | 在WPF上下文加载项目、保存矩形/审核/导出；不冒充真实鼠标验收 |
| RF-DETR训练 | NOT TESTED / BLOCKED | 未启用真实训练栈，接口拒绝执行 |
| 跨Windows版本/显卡/编码 | NOT TESTED | 本机单环境与AVI不代表全部支持 |
| 真实禁网、安装/升级/卸载 | NOT TESTED | 未改系统网络，未生成正式安装包 |

本轮修复的工程问题包括：系统WindowsBase引用路径、旧C#局部变量作用域冲突、扫描器误把DirectorySeparatorChar中的子串当作torch、训练快照错误沿用较早确认审核。增加“最新审核优先”和Windows保留路径的回归测试。依赖元数据下载改为有墙钟上限和大历史文档的完整info对象解析，没有改系统VPN。

## 许可证结果

Annotator/IDS源代码及自研开发EXE为Apache-2.0；Windows运行组件/系统字体按OS环境登记，不伪称Apache、不复制进候选。Full代码没有被套用开源许可。FFmpeg未启用，LGPL专项例外没有被擅自扩展。

已核实的阻断包括：tqdm4.70.1实际wheel为MPL-2.0 AND MIT；certifi2026.10.23为MPL-2.0；PyTorch2.14.1复合声明含B.1未允许部分；科学计算wheel有内嵌库审查问题。旧NumPy Windows wheel中的GPL GCC exception二进制已移除。supervision自身MIT不代表其依赖链通过。没有下载未知授权权重，没有引入Plus/PML或收费许可。

88项列表是候选依赖审查，不是已批准安装锁；包元数据不能代替每个wheel/DLL及运行库的审查。通用旧AI环境资产保留但退休、禁止作为当前运行/发行依赖；剩余历史资产的保留不表示B.1通过。

## 分发状态

- **IVAD Annotator：NOT VERIFIED。** 可运行的开发MVP与测试已完成，但实际安装/卸载、目标机、禁网等证据仍缺。
- **IVAD Full / NVIDIA：BLOCKED。** 训练依赖、模型权重和CUDA/硬件尚未全部获准与验证。
- **正式发行冻结持续有效。** 未制作安装程序、签名、公开仓库、上传或分发；没有改变许可证政策，没有系统网络/驱动/全局Python改动。

## 仍需完善

大文件导入/hash/包导出还会同步执行；复杂几何编辑、完整撤销重做、类别版本迁移、冲突合并UI、跨录像分组数据划分、崩溃/断电恢复尚未完成。未将基础MVP声称为完整成熟标注软件。

后续优先三项：

1. 实际GUI交互验收与大文件后台作业/取消、标注编辑完善。
2. 跨编码/目标Windows、离线、数据恢复与迁移验证，保持正式打包冻结。
3. 独立推进Full的合规依赖替代、具体权重与NVIDIA验证，不阻塞Annotator。

## 文件入口

- [操作说明](../docs/ANNOTATOR_QUICKSTART.md)
- [IDS规范](../docs/IDS_V1_SPEC.md)
- [v1.1需求](../docs/V1_1_SRS.md) / [架构](../docs/V1_1_ARCHITECTURE.md)
- [Release Readiness](../governance/RELEASE_READINESS.md)
- [未解决阻断](../governance/RELEASE_BLOCKERS.md)
- [清理报告](../governance/LEGACY_CLEANUP_REPORT.md)
- [第三方清单](../governance/THIRD_PARTY_LICENSES.md) / [模型登记](../governance/MODEL_LICENSE_REGISTER.md)

开发入口：build/dev/Ivad.Annotator.Dev.exe；复现门禁：scripts/release_gate.ps1。治理证据含私有路径和本机信息，不能作为开源分发文件直接上传。
