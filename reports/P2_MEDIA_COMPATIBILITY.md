# P2 媒体兼容性报告

执行日期：2026-10-13，Windows本机。P2最终自动化 71 passed / 0 failed / 0 errors，P1回归 37 项；证据 artifacts/p2/pytest.xml、pytest.log。源码本地 nvidia-first（报告生成时HEAD 52d36f1，最终提交见Git记录）。未经用户另行批准不得进入P3–P6。

所有视频为scripts/p2/make_samples.py自行生成：320×180、36帧、运动色块和文字；无第三方/工厂素材。人工测试几何只验证工具和格式，不代表选煤厂缺陷真值。真实厂区视频/标注质量/工业精度：NOT TESTED。

一键启动实际验证PASS：独立smoke实例正常退出，默认实例实际窗口标题IVAD Platform 1.0.0-P2，保留运行供用户使用；证据launcher-validation.json。

|自制实际样本|实际codec|解码帧|B帧|结果|
|---|---|---:|---:|---|
|corrupt.mp4|—|0|0|REJECTED|
|noninteger.mp4|h264|36|14|PASS|
|rotation.mp4|h264|36|15|PASS|
|sample.avi|mpeg4|36|0|PASS|
|sample.mkv|h264|36|14|PASS|
|sample.mov|h264|36|14|PASS|
|sample.mp4|h264|36|15|PASS|
|vfr.mp4|h264|36|14|PASS|

每个正常文件实际解码36帧；随机定位与上一帧按实际PTS断言，不能把文件扩展名当codec保证。样本SHA256、时长、时间基、帧率、旋转、实际PTS差值记录在artifacts/p2/media-validation.json；样本文件在samples/，生成脚本可复现。H.264编码设bf=2、g=12，表内B帧数来自真实解码帧类型。

VFR实际PTS间隔不同；非整数标称30000/1001，实际微秒间隔33366/33367；90°矩阵旋转实际输出180×320。时间原点为流start_time或首帧PTS，拍摄日期保持未知。求帧索引只在从头顺序解码时可靠，seek后留空。整数微秒精度不等于知道现场绝对时钟。

Qt Multimedia 6.8.3真实QMediaPlayer+QVideoSink播放MP4：36帧，时长1440ms，错误[]，PASS。源Qt接口时间轴为毫秒；P2采用同一PyAV/FFmpeg解码器统一实际PTS播放与抽帧，避免两套定位语义。Qt探针记录qt-decode.json/log。

缺PTS、重复PTS、倒退PTS：明确拒绝，不用FPS补造。三种异常通过可控解码器故障注入测试；现实中缺PTS损坏容器尚未提供，NOT TESTED。损坏MP4样本实际拒绝，非直角旋转/未知时长明确不支持。

H.265、MJPEG、AV1、其他AVI/MOV组合、多视频轨、音频、超长/4K/网络录像及真实厂区来源：NOT TESTED。当前仅处理第一个视频轨，无音频，不宣称所有MP4/AVI兼容。
