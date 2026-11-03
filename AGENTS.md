# IVAD v1.1 项目规则

当前授权以 prompts/IVAD_V1_1_AUTHORIZATION.md 为准。旧P0/YOLO路线退休，旧阶段限制不阻止本次v1.1开发；旧报告仅为历史，不能当作当前状态。

- Annotator/IDS自研代码Apache-2.0；Full/NVIDIA业务代码私有。开源候选不得包含src/Full或用户数据。
- 严格执行governance/LICENSE_POLICY.md的B.1。Annotator仅Apache或可明确选择Apache分支；FFmpeg是唯一需逐构建审查的LGPL例外。Full逐项审查Apache/MIT/BSD-2/BSD-3。
- 禁止GPL/AGPL/PML、收费/平台绑定组件；UNKNOWN默认BLOCKED。覆盖传递依赖、内嵌代码、wheel/DLL/EXE、字体、编解码器及权重；不得伪造或删许可证声明。
- OS/开发工具单列环境依赖，不伪称Apache，也不擅自随附。RF-DETR未通过完整验收，禁止自动安装或下载权重；标注端不引用AI框架。
- 每次代码、依赖、模型或阶段变更后必须执行scripts/release_gate.ps1；修复后重跑适用检查。它执行开发编译、测试、WPF启动、依赖/二进制/许可证/私有数据检查并生成A–L证据。不得把静态/模拟检查当实际安装、GPU或禁网测试。
- 正式发行持续冻结：不得制作正式安装包、解除冻结、签名、公开、上传、分发或采购。开发EXE/测试工件允许。READY不自动解除冻结。
- 仅写当前项目；不得修改全局Python、其他项目、驱动、代理/VPN、项目外数据。旧临时VPN授权不延伸到v1.1。
- 不删除真实业务数据。退休实验资产先记录路径/用途/hash，递归删除前检查绝对路径位于项目内。严禁打包业务视频、标注、模型或本地项目。
- 保留IDS稳定ID、PTS、四种帧状态、哈希、修订、冲突拒绝与回滚。模型类别编号不能代替工业故障ID。
- 维护docs/PROGRESS.md、CURRENT_TASK.md、DECISIONS.md和governance；不移植其他NVIDIA项目的进度。

## 2026-10-26 单次便携授权记录

用户明确授权的Annotator Windows x64便携测试交付已完成，见governance/portable-authorization-20261026.json（CONSUMED_FROZEN）和reports/V1_1_PORTABLE_DELIVERY_20261026.md。该授权只覆盖已固化的本次ZIP；不允许后续新版自动打包、Full、签名、公开或上传。常规打包冻结与Policy B.1保持。
