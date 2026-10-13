# P2 测试结果

最终结果：71通过，0失败，0错误，0跳过；主套耗时39.227秒。P1原有37项回归保留通过，P2新增34项。额外100/200%DPI画布各3项通过，作为同用例多环境复测，不重复计入主套总数。

执行日期：2026-10-13，Windows本机。P2最终自动化 71 passed / 0 failed / 0 errors，P1回归 37 项；证据 artifacts/p2/pytest.xml、pytest.log。源码本地 nvidia-first（报告生成时HEAD 2626af8，最终提交见Git记录）。未经用户另行批准不得进入P3–P6。

所有视频为scripts/p2/make_samples.py自行生成：320×180、36帧、运动色块和文字；无第三方/工厂素材。人工测试几何只验证工具和格式，不代表选煤厂缺陷真值。真实厂区视频/标注质量/工业精度：NOT TESTED。

|测试模块|通过|失败|
|---|---:|---:|
|tests.test_crash_restart|1|0|
|tests.test_devices|4|0|
|tests.test_gui|8|0|
|tests.test_jobs_logs|6|0|
|tests.test_p2_canvas|3|0|
|tests.test_p2_gui|1|0|
|tests.test_p2_media|11|0|
|tests.test_p2_safety|14|0|
|tests.test_p2_services|5|0|
|tests.test_projects_database|18|0|

命令：.venv-p1/Scripts/python.exe -m pytest tests -q --junitxml=artifacts/p2/pytest.xml。PySide6实际Qt窗口/鼠标和真实解码，并非静态截图代替操作。测试数据在独立pytest临时目录；持久化截图/导出项目在artifacts/p2/gui-evidence-*，不使用用户厂区数据。

额外实际运行：QtMultimedia36帧播放；12份导出hash/坐标/COCO/native独立读回；8个媒体样本；三个DPI真实窗口截图；pip check无依赖错误；P0/P1历史文件/原有包版本只读比对PASS。详细JSON/XML/log位于artifacts/p2。

测试发现的问题已修复并重跑。最终主套无未解决失败；中间失败日志final-focused.log等保留研发痕迹，最终以pytest.xml为准。模拟磁盘不足、数据库提交失败和异常PTS标明故障注入；没有声称真实断电或现场坏码流试验通过。

未测试：真实厂区数据、工业标注质量、4K/小时录像、百万帧、大规模并发、恶意文件、全编码矩阵、断电恢复、Intel硬件、工业AI精度。P0训练/推理验收不在本轮重复执行；P1设备回归真实调用P0独立worker作CUDA张量检查，未升级GPU环境。
