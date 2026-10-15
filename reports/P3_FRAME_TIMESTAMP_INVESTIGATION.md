# P3 抽帧时间只读调查与修复

日期：2026-10-15。结论：8525异常源于显示字段语义混淆，历史时间数据正确；无需迁移/改写真实项目记录。

## 真实证据与根因

项目：E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2。

媒体：12a11464-0581-4bf1-8977-47fbcd5364b7，“超高压车间8525压滤机_1026191715.mp4”。解码对象为项目内COPY文件，未更改原始来源文件。

| 字段 | 现场读取值 |
|---|---|
| 容器/编码 | 实际为mpeg / h264，虽扩展名.mp4 |
| 视频流时长 | 70,040,000 µs =70.040秒 |
| 容器时长 | 70,065,000 µs =70.065秒，容器可含其他流 |
| 流time_base | 1/90000 |
| 容器start_time | 52,241,877,778 µs（FFmpeg容器时间单位1/1000000） |
| 流start_pts / 首帧raw_pts | 4,701,769,000 ticks |
| stream.duration | 6,303,600 ticks，即70.040秒 |
| 换算后的origin_us | 52,241,877,778 µs |
| 历史8525帧 | 200条，原pts_us范围52,241,877,778–52,297,197,778 |
| 已存time_us范围 | 0–55,320,000 µs，即0–55.320秒 |
| 一致性 | 200/200满足pts_us-origin_us=time_us |

上一轮DatasetPage列表和草稿直接显示pts_us/1e6，所以出现52247.677778秒。这是带起始偏移的媒体时间轴，不是媒体内相对位置，更不能当摄像头真实拍摄时钟。正确例：52247677778−52241877778=5800000µs，即5.800秒。播放器和旧标注列表原本使用正确time_us；标注详情原先标为PTS的绝对微秒本身未损坏，本轮另加媒体相对秒便于操作员对照。

此前P3报告中将该列称为视频相对时间的描述不准确，现由本调查更正；旧报告和截图原样保留作为历史证据，不修改过去验收记录来掩盖问题。

另51条给煤机帧的既有媒体元数据也有非零origin_us=81,272,186,444，51/51的PTS与相对时间差一致；旧DatasetPage同样会误显示带偏移PTS。本轮统一派生覆盖这251条读出显示，但只对指定8525执行原视频实时probe/重解码；未声称重新解码其他长录像。

## 抽帧间隔与真实画面

8525来自两批各100帧，真实参数interval_us均500000，起点分别5.800秒和0秒、上限100。各批99个相邻间隔为50次520000µs、49次480000µs；25fps实际帧格上约0.5秒采样产生0.52/0.48交替，非伪造固定0.500帧。两批范围5.800–55.320秒、0–49.520秒；没有为了覆盖70秒生成额外帧。

只读重新解码0、5.800、6.320、55.320秒，4/4实际PTS匹配历史值，4/4 RGB像素与保存PNG完全一致。真实项目副本GUI再次定位：播放器5.800/70.040秒，标注信息“媒体相对5.800秒”，数据集5.8；三处一致。JSON证据timestamp-readonly-investigation.json、real-video-time-verification.json、real-gui-verification.json均在本轮artifacts目录。对应真实GUI截图real-player-5_800.png、real-annotation-5_800.png、after-final-1920.png。

## 统一时间定义与实现

- raw_pts：解码器原始tick值；time_base：该流PTS时间基。pts_us=round(raw_pts×time_base×1000000)。历史数据库保存的是pts_us，不另存原始tick；派生raw_pts缺省None，不从微秒猜造原tick。
- media_relative_seconds：(pts_us−media.video.origin_us)/1000000，供默认时间列、播放器及标注定位使用。
- source_relative_seconds：当前媒体相对时间，递归加每级CLIP实际first_source_time_us；使用实际首帧而非requested_start_us，处理非整帧申请边界。
- capture_datetime：仅可信拍摄时钟可用。本轮没有这类证据，保持None，不解析文件名或把PTS当拍摄时间。

新增video/timestamps.py派生接口；reader.py共享relative_time_us；MediaService.frames/frame_image与DatasetService.screening返回同一派生定义。新冻结样本可以附加timing对象，旧manifest完全不改。

缺少origin时只显式回退到历史time_us并警告；历史PTS/time_us不一致或越界时记录timestamp_issues，读路径不写库。片段缺实际首帧来源映射时source_relative返回未知，不强填申请时间。测试覆盖真正的非零PTS MPEG-TS、普通视频、实际VFR、真实生成裁剪片段及多级映射；无依赖重装。

## 历史数据保护与后续方案

本项目未发现需要写回的时间错误，影响的是显示：8525共200条，全部既有来源另51条也受旧显示逻辑影响。已通过派生读出修复，旧标注、图片、帧UUID、raw pts_us、time_us及来源关系未变化。Schema仍0008，无Migration。原SQLite mode=ro读取、备份逻辑核验一致，165项选取保护文件hash0变化。

若以后发现真正历史语义冲突，先只读统计受影响UUID、逐视频probe和逐帧来源对照，提交含备份/回滚与派生映射方案，等待用户批准后才考虑写入。本轮没有执行或暗中准备覆盖真实记录的迁移。
