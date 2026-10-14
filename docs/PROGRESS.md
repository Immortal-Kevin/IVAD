# 进展

2026-10-13：P0-NVIDIA PASS，原始资产/环境/历史BLOCKED记录保留。
用户明确批准P1；已交付真实PySide6 GUI、项目/SQLite/任务/设备/设置/日志，37项自动化通过，一键启动及DPI检查完成，P1验收PASS。
本地Git nvidia-first，忽略用户数据/大型资产，无远程推送。
P2经用户正式指令批准，完成统一GUI媒体导入/真实PTS播放与抽帧、人工标注/ROI/标签库、审核/不可变数据集/四格式导出。
主套71通过/0失败（含37项P1），100/200%DPI画布各3项额外通过，12个导出目录独立回读PASS。
Schema0003添加业务表，旧0002数据/迁移备份验证；原P0/P1报告和环境包版本保持。
报告reports/P2_*，操作docs/P2_USER_GUIDE.md，原始证据artifacts/p2/。只完成工程样本验证，真实工业场景NOT TESTED。
未开始P3–P6；等待用户明确批准，Intel独立历史BLOCKED不变。

2026-10-14：用户批准P2补充修改，左右媒体布局/蓝白标签/可见参数说明/人工实际视频裁剪完成。Schema0004增量保留旧数据，主套84通过/0失败，原71项回归；100/200%DPI新GUI流程各1通过。报告P2_UI_ADJUSTMENT.md、P2_CLIP_SAVE_FEATURE.md及更新验收/测试报告；原P2证据与报告历史保留。没有进入P3。


2026-10-14 P2-Test Distribution：冻结db81c49，P2 Lite Beta onedir ZIP与独立IVAD.exe已构建；86项最终回归、15条真实EXE链路、另进程原生打开项目恢复均通过。跨电脑/无NVIDIA实机/真实断网尚未测。分发审核BLOCKED（FFmpeg/x264/x265/Qt许可与源资料未闭合）；历史保护FAIL（3文件hash变化，另1旧截图重新写入，未找到原版）。后续测试输出已隔离，原GPU/GUI环境包版本未变。报告P2_DISTRIBUTION_ACCEPTANCE.md和P2_DISTRIBUTION_TEST_RESULTS.md；仅供用户审核，不建议外发，无Setup版，未进入P3。


2026-10-14 P2 Annotation UX v2：正常/异常/未知快捷保存、自动翻页开关、处理状态图标/勾选筛选、批量正常、UUID摄像头/ROI/片段关联、软剔除/恢复和保护已实现。0005增量迁移前备份，真实45帧复用仅在副本测试，用户原数据与环境保留。最终完整100测试通过，额外真实GUI及DPI验证见P2_ANNOTATION_UX_V2_TEST_RESULTS.md；原生自动化访问冲突仍未定位。Word18页/PDF1页更新；旧Beta.1过期，新Beta.2另名本地候选，许可/分发继续BLOCKED。停止在P2，等待用户审阅，未进入P3–P6。构建/哈希/验收按本轮package-summary和P2_ACCEPTANCE为准。
