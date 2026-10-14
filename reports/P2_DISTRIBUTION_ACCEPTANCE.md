# P2 Test Distribution 验收报告

日期：2026-10-14。版本1.0.0-P2-Beta.1。冻结源码 db81c49。

**分发决策：BLOCKED。技术候选 ZIP 已构建，功能验证 PASS；历史证据保护 FAIL。不得宣称 P2 正式发行或商业生产通过。**

| 项目 | 结论 |
| --- | --- |
| onedir 便携ZIP / IVAD.exe | 已生成，本机实际独立启动与核心链路 PASS |
| 不需目标机 venv / 开发Python PATH | 冻结 EXE 的隔离PATH测试 PASS；无Python干净电脑本身 NOT TESTED |
| 中文空格目录、非系统盘、未提升权限 | 本机 PASS，其他用户／其他Windows NOT TESTED |
| ZIP真正解压并启动另一个进程，恢复项目／标注 | PASS，实际Windows原生目录选择提交，REVIEWED、框、多边形、ROI恢复 |
| 视频编码和业务回归 | 86项通过；独立EXE15条链路通过，具体编码／范围见测试报告 |
| Lite不加载AI、禁止CPU-only AI | PASS；未捆绑Worker、torch、ORT、Ultralytics、权重 |
| RTX5070Ti硬件检测 | 本机PASS仅硬件；Lite CUDA/模型 NOT TESTED，P0历史独立保留 |
| 其他NVIDIA卡 | STATICALLY COMPATIBLE / REQUIRES VALIDATION；实机NOT TESTED |
| 无NVIDIA办公机／干净VM／真正断网／中文用户名 | NOT TESTED |
| 默认用户AppData、诊断ZIP、隐私排除 | 已实测／审计PASS；只读程序目录拒绝写入场景 NOT TESTED |
| 许可证与完整对应源码／再分发权 | BLOCKED，FFmpeg/x264/x265及Qt发行义务未闭合 |
| P0/P1环境包版本 | PASS，保持原版本，无驱动／Toolkit／全局Python改动 |
| P2历史证据保护 | FAIL，3文件hash改变、另1截图重新写入；未找到原始副本；已隔离后续输出 |
| EXE安装版 | 未生成，便携版分发验收尚未通过 |
| 签名／SmartScreen／Defender各机器兼容 | 未签名；跨机策略 NOT TESTED，未关闭安全设置 |

交付：
- dist/IVAD_Platform_v1.0_P2_Beta_Portable.zip
- dist/IVAD_Platform_v1.0_P2_Beta_Portable/IVAD.exe
- dist/SHA256SUMS.txt
- docs/P2_TESTER_INSTALL_GUIDE.docx
- docs/P2_TESTER_QUICK_START.pdf
- docs/P2_GPU_COMPATIBILITY_MATRIX.md
- docs/P2_COMPATIBILITY_FEEDBACK.csv
- reports/P2_DISTRIBUTION_TEST_RESULTS.md

ZIP 98,806,690 bytes；IVAD.exe 9,903,314 bytes；解压约 250,187,095 bytes。Setup.exe 不存在，不提供其假哈希。

阻断和后续决定：获取明确的x264/x265下游许可与完整对应源码/构建资料，或选择可确认许可的视频运行库路线；完成Qt发行义务；取得真实旧证据备份以恢复，或由用户审核如何处理证据保护失败；取得真实办公电脑与跨Windows测试记录。不会自动接受商业例外、擅自更换生产许可、公开源代码或发布包。

本轮没有向其他测试员、服务器或公网分发。普通测试员操作材料已备齐，但目前不建议外发。已停止等待用户验收；不进入P3。