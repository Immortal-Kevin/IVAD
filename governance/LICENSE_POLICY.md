# IVAD License Policy B.1

生效依据：2026-10-26用户v1.1总指令；预算永久0元。原文保存在prompts/IVAD_V1_1_AUTHORIZATION.md。

| 范围 | 允许 | 拒绝/默认阻断 |
|---|---|---|
| Annotator/IDS随附依赖 | Apache-2.0；明确可选择Apache分支的双许可证 | 其他许可证不得自动批准 |
| FFmpeg专项 | 经具体构建核实的LGPL；优先原样独立EXE | enable-gpl、enable-nonfree、GPL外部库、缺源码/配置/许可材料 |
| Full/NVIDIA | 逐项审查的Apache-2.0、MIT、BSD-2-Clause、BSD-3-Clause | 其他免费许可证也不自动批准 |
| 全项目 | 自研代码按产品边界；OS/开发工具单列 | GPL/AGPL/PML、收费/平台绑定、未知权重授权 |

不得删除声明、伪造METADATA、隐藏依赖或以改名通过审查。GPL runtime exception不自动成为B.1例外。MPL、ISC、PSF、Zlib、OFL等与“免费/可商业使用”是不同判断，本政策未批准其作为产品随附依赖。

覆盖直接/传递依赖、内嵌代码、动态库、字体、编解码器、模型权重、运行库和SDK。顶层许可证不足以批准二进制。固定工件URL、hash、完整LICENSE/NOTICE、源码和构建信息需可追溯。

本轮Annotator使用Windows内置.NET Framework/WPF和Media Foundation，不附带它们的DLL、安装程序、系统字体或第三方编解码器。它们按用户允许的OS环境依赖登记，**不是Apache组件**。开发使用现有系统C#编译器、PowerShell和项目遗留Python/pip审计工具；不进入Annotator候选文件。

每次变更运行scripts/release_gate.ps1。状态为READY/BLOCKED/NOT VERIFIED。没有实际安装、升级、卸载验证，正式分发不能READY。正式安装包、签名、公开和分发冻结持续有效，需用户另行明确批准。

专利、权利归属和合同风险独立记录；工程扫描不作绝对保证。
