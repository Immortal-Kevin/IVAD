# P2 Lite Beta 构建记录

普通测试员只使用 ZIP、IVAD.exe 和 docs 中的操作资料，不运行本文件的开发命令。

本轮冻结源提交 `db81c49`，PyInstaller 6.22.3，Windows x64，Python 3.12.14。`requirements-distribution-lock.txt` 是独立构建环境的真实锁文件；不要在 P0/P1 环境中安装打包工具。

本轮步骤：Git archive 固定提交到 artifacts/p2-distribution/source-db81c49；生成 packaging/build-info.json（版本、源提交、日期、P2 Lite、许可状态）；使用独立 .venv-distribution 执行 PyInstaller 对该快照 packaging/ivad.spec 的构建。构建输出、日志、源快照、来源及组件资料均位于 artifacts/p2-distribution，不覆盖历史目录。

onedir 运行库包含原版本 PySide6、PyAV/FFmpeg、numpy、Pillow、SQLAlchemy、Alembic、YAML、迁移脚本和标准库。显式排除 torch、torchvision、onnxruntime、Ultralytics、模型权重及 Qt 的未使用大型模块。程序数据默认用户 AppData，项目存放父目录由操作员选择。

开发部署核验入口：实际生成的 IVAD.exe 使用 `--deployment-check <本轮唯一可写目录>`。此参数只用于明确选择的合成素材验证，不在双击启动时执行，不扫描旧项目。它执行真实 Qt/后台链路并保存 PASS/FAIL 与进度；自动验证注入文件选择结果和确认响应，不能当作所有原生选择框均实测。

本轮最终执行了86项回归、15条冻结EXE核验、ZIP解压后的新进程原生打开项目恢复，以及正常GUI硬件枚举。实际只有RTX5070Ti／当前Windows11。具体结果、未测试项目、源提交、CRC及SHA256见新建的分发报告。

分发决策仍 BLOCKED：FFmpeg/x264/x265明确的下游许可和对应源材料未闭合；Qt发行义务需复核；历史证据保护有已披露失误。不能以构建成功代替许可审核或数据保护验收。没有Setup安装版，没有商业／生产发行批准，没有进入P3。

测试输出默认已改为唯一 artifacts/test-runs；也可指定 IVAD_TEST_EVIDENCE_DIR、IVAD_P2_GUI_EVIDENCE_DIR 和 IVAD_P2_ADJUSTMENT_EVIDENCE_DIR。禁止再次把回归截图／设备信息写入历史证据目录。
