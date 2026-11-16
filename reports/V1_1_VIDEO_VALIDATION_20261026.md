# IVAD v1.1 视频与后台任务实测报告

记录时间（UTC）：2026-10-26T05:51:09.995038+00:00。执行机：Microsoft Windows 11 家庭版 中文版 / 10.0.26200。全部视频为自研合成测试数据，Windows已有Media Foundation编解码器参与真实编解码；没有安装任何codec或引入FFmpeg。素材与生成器均排除出开发EXE候选分发。

本轮最终数据：`build/test-data/20261026T054739-eb3aa46f`；原始日志：`governance/evidence/build-test-20261026-134738.log`。

| 场景 | 实际输入 / 方法 | 实测结论 | 限制 |
|---|---|---|---|
| AVI | 自研RIFF AVI，64×48 RGB24，2fps，6帧 | PASS；6帧，0–2.5秒、间隔0.5秒真实PTS | 未涵盖AVI中全部编码 |
| MP4 H.264 | OS编码器，NV12输入，64×48，4fps，12帧 | PASS；12帧，100ns PTS逐项一致 | 非全部profile/音轨/旋转组合 |
| MOV | 同AVC样本与合法原子结构，ftyp改为QuickTime品牌及兼容品牌，64×48 | PASS；12帧；是受限合成MOV覆盖 | 未声称覆盖所有相机MOV、ProRes或编辑列表；不是只改扩展名 |
| MKV | 自研EBML Matroska封装、AVC CodecPrivate与真实block时间戳 | PASS；12帧，末帧2.75秒 | 不覆盖字幕、多音轨、特殊lacing等 |
| HEVC MP4 | 现有OS HEVC编码/解码，64×48，12帧 | PASS；实际解码12帧 | 本机具备能力，不保证其他Windows已装相同组件 |
| VFR H.264 | 输入PTS（秒）：0、0.1、0.4、1.2、1.25、2.2 | PASS；6帧，返回100ns时间与输入逐项一致 | 不覆盖所有B帧/编辑列表变体 |
| 30分钟视频 | 64×48 H.264，1fps，1800帧 | PASS；每60秒采30帧；1795–1800秒再采5帧，末帧1799秒 | 合成低帧率素材 |
| 30分钟1080p视频 | 1920×1080 H.264，1fps，1800帧，5,231,257 bytes | PASS；每60秒采30帧，末采样1740秒，图像尺寸1920×1080 | 非高码率25/30fps持续监控压力测试 |
| 损坏输入 | 伪MP4字节流及真实H.264 MP4截断一半 | PASS（正确拒绝）；没有清单或标注变更，任务临时目录清理 | 不声称能修复损坏视频或检测每种部分码流损伤 |
| 范围/上限/去重 | 左闭右开；范围越界为空；多批续抽；重复导入 | PASS；稳定Video ID、PTS去重、已审核帧保留 | 同一文件关联不同摄像头是不同来源实体 |
| 后台子进程 | GUI同一VideoJobs实现，实际启动开发EXE的--extract路径 | PASS；范围参数、取消、损坏失败、目录清理 | 非GUI点击流程 |
| 取消后回滚 | 解码时、复制时、提交校验时、IDS导入/导出时取消 | PASS；保留原清单，回滚本次未提交资产 | 断电、强杀及任务日志写入极小窗口未验收 |

## 1080p长视频记录

实际编码耗时：3268 ms；导入、解码、PNG保存和提交校验耗时：16171 ms。该数字来自测试进程计时，不是GUI响应时间或工业性能指标。真实GUI响应状态：**NOT TESTED**。

长视频生成使用Windows编码器，媒体包含真实1800个样本及30分钟时间跨度，不是改文件名或延长单帧显示时间。编码器格式头的标称帧率不用于PTS推断；时间以样本100ns时间和实际容器时间表为准。

## 修复与真实失败记录

1. 早期VFR测试失败：RGB32输入的颜色转换链输出CFR，容器stts为固定步长且9帧，而预期6个非均匀时间样本。改用自生成NV12直接输入编码器；重新测试生成的VFR保持六个真实PTS。该问题属于测试生成器，未掩盖成解码成功。
2. HEVC初次失败：首帧报告兼容输出类型重新协商，被旧代码一概拒绝。现在读取新类型并验证RGB32和可见尺寸，仅接受兼容更新。
3. 1080p初次失败：实际输出从1920×1080协商为1920×1088编码缓冲。现在读取MFVideoArea，按明确声明的显示区域裁切；可见帧与标注坐标保持1920×1080。可见尺寸/像素类型真实变化仍拒绝。
4. 空抽帧范围原先易误报缺少解码器，现在返回0帧并显示范围/重复提示；达到上限则明确提示可以继续。

所有失败日志仍在 `governance/evidence/build-test-*.log`，对应运行目录保留results.json，不覆盖原记录。最终61项的逐项状态以最终results.json为准。

## 证据入口

- `build/test-data/20261026T054739-eb3aa46f/media-fixtures.json`：实际测试文件字节数与SHA256。
- `build/test-data/20261026T054739-eb3aa46f/long-video-metrics.json`：1080p长视频参数与计时。
- `build/test-data/20261026T054739-eb3aa46f/hevc-environment.json`：实际HEVC测试状态。
- `build/test-data/20261026T054739-eb3aa46f/worker-process.log`：成功、取消、COM失败的真实子进程结果。
- `governance/evidence/runtime_environment.json`：系统媒体DLL身份/hash，明确不随附。
- `governance/evidence/media-reference-sources.json`：官方API/格式依据与SDK参考来源。
