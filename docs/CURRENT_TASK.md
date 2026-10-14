# 当前任务

P2完成，工程验收PASS；查看reports/P2_ACCEPTANCE.md、P2_TEST_RESULTS.md、docs/P2_USER_GUIDE.md。
一键启动：根目录启动IVAD.cmd。代码ivad_app/，独立GUI环境.venv-p1；原GPU环境.venv-nvidia保留。
等待用户决定；未经再次明确批准不得进入P3–P6。Intel恢复同样需授权。
本轮真实视频/人工标注/数据集闭环完成，71项测试通过（含37项P1回归）。P0/P1历史与原环境已核对保留。
合法自制样本可作为P3工程输入；真实选煤厂视频和工业真值未测试，不足以训练合格工业模型。
正式安装包、完整备份恢复、生产许可/工业精度/长期稳定性尚未完成。

2026-10-14补充修改已完成：本机视频管理左右布局、参数说明及人工保存MP4 CLIP真实运行，当前Schema0004，84项主套通过；原71项历史回归均通过。仅P2，停止等待用户审阅；P3–P6未经授权不得开始。新证据artifacts/p2-adjustment，旧artifacts/p2不覆盖。


2026-10-14 P2-Test Distribution：冻结db81c49，P2 Lite Beta onedir ZIP与独立IVAD.exe已构建；86项最终回归、15条真实EXE链路、另进程原生打开项目恢复均通过。跨电脑/无NVIDIA实机/真实断网尚未测。分发审核BLOCKED（FFmpeg/x264/x265/Qt许可与源资料未闭合）；历史保护FAIL（3文件hash变化，另1旧截图重新写入，未找到原版）。后续测试输出已隔离，原GPU/GUI环境包版本未变。报告P2_DISTRIBUTION_ACCEPTANCE.md和P2_DISTRIBUTION_TEST_RESULTS.md；仅供用户审核，不建议外发，无Setup版，未进入P3。


2026-10-14 P2 Annotation UX v2：正常/异常/未知快捷保存、自动翻页开关、处理状态图标/勾选筛选、批量正常、UUID摄像头/ROI/片段关联、软剔除/恢复和保护已实现。0005增量迁移前备份，真实45帧复用仅在副本测试，用户原数据与环境保留。最终完整100测试通过，额外真实GUI及DPI验证见P2_ANNOTATION_UX_V2_TEST_RESULTS.md；原生自动化访问冲突仍未定位。Word18页/PDF1页更新；旧Beta.1过期，新Beta.2另名本地候选，许可/分发继续BLOCKED。停止在P2，等待用户审阅，未进入P3–P6。构建/哈希/验收按本轮package-summary和P2_ACCEPTANCE为准。
