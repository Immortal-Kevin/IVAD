# P3.7-D 视频与基础功能验证

日期：2026-10-19。**VIDEO_IMPORT_EXTRACTION_STATUS=NOT_TESTED_CANDIDATE；LOCAL_FUNCTIONAL_STATUS=NOT_TESTED_CANDIDATE。** 未生成IVAD EXE，不具备“空白Windows、无需Python”的实测证据。

## 本轮Windows源码回归

开发机Windows11 10.0.26200，使用既有`.venv-p1`，真实原生Qt窗口，未设offscreen。14 passed / 0 failed / 0 skipped，24.96秒；原始命令和完整结果见 `artifacts/p37d-20261019/source-initial.log`、`source-initial.xml`。输入是临时新建项目和合成媒体，不使用开发机已有工业项目代替空白项目；文件选择结果与确认框由测试注入，不声称所有系统文件对话框已经人工验收。

| 测试 | 本轮源码结果 |
|---|---|
| `test_gui_project_create_save_reopen_and_error` | PASS，新建、保存、重开项目，错误路径处理 |
| `test_gui_import_play_extract_annotate_freeze_export_reopen` | PASS，视频导入、播放器/暂停、抽帧、鼠标人工多边形、冻结/导出、重启恢复的既有自动化流程；截图另存本轮source-gui目录。摄像头及矩形真值还用于四页数据集测试夹具，不冒称此节点做了完整摄像头/矩形绘制GUI验收 |
| `test_four_tabs_filter_sort_draft_batch_freeze_and_export` | PASS，筛选、草稿、划分、版本/来源关系保持，默认Native及显式COCO；本用例是合成5图3目标2负样本，不冒称200图真实集本轮再测 |
| `test_real_decode_actual_pts`，7种合成素材 | PASS：MP4/AVI/MOV/MKV、VFR、非整数帧率、旋转；仅当前旧解码环境，不能转移给未来候选包 |
| 损坏输入及缺失/重复/倒退PTS，4项 | PASS，拒绝无效元数据及异常时间戳，无伪造文件 |

本轮没有修改业务或测试断言，没有跳过/删减测试。P3.7-A既有真实200图/402目标/16正常负样本验收保留；本轮不重复该工业副本测试，不将其写为新EXE结果。历史`IVAD_LIFECYCLE_REAL_COPY`缺少专用夹具的SKIP及旧GUI XFAIL均保持原结论，本轮14项不覆盖这些历史节点。

## 免费视频路线的实际CLI原型

仅在本轮研究目录运行下载并校验的共享FFmpeg工具，不是IVAD应用集成验收。合成320×180、40帧H.264 MP4，CFR及非均匀PTS的VFR两份；源素材由既有开发编码器生成，仅用于测试，不是发行依赖，也不含真实录像。完整参数、stderr、帧数和逐帧PTS见 `video-prototype/results.json` 与 `vfr-preservation-experiment.json`。

| 原型事项 | 实际结果 |
|---|---|
| 两份H.264输入探测/解码 | PASS，均40帧，320×180 |
| 两份抽帧 | PASS，各40张PNG |
| CFR的MPEG-4 Part2/MP4片段 | PASS，25帧，PTS逐项匹配，0微秒最大误差 |
| CFR的h264_mf/MP4片段 | PASS，本机系统MFT可用，25帧，PTS逐项匹配 |
| VFR的默认片段参数，两编码器 | **FAIL时间戳契约**：虽进程成功，输出PTS被改变，比较最大误差12,345微秒；保留此失败，不用退出码0冒充通过 |
| VFR的trim/setpts+强制微秒时基h264_mf | **FAIL**，MFT输出类型`80004005`，完整stderr保留 |
| VFR的trim/setpts+1/60000时基mpeg4 | **FAIL本实验精确契约**，24帧而预期25帧，不能视为无损替换 |
| 候选EXE内视频显示/片段/抽帧/GUI不死锁 | NOT TESTED，无候选 |
| 替代载荷的AVI/MOV/MKV/H.265 | NOT TESTED；源码合成容器测试不能替代这些候选实物验证 |

这些失败只说明当前实验参数不能直接集成，不证明所有免费方案不能满足需求。没有将该方案写入生产服务，也没有擅自放弃视频抽帧或片段功能。恢复构建前须完成准确来源/许可材料、链接集成和实际PTS处理，并重新对候选EXE做完整空白流程。

## Qt历史稳定性

本轮源码GUI回归未复现原生崩溃；**本轮未复现，原始根因仍未确定**。`IVAD-QT-001`继续OPEN/PARTIAL，保留原始Qt日志、Windows Event/WER和历史PARTIAL；原生异常复现、关闭/组合框/菜单/异步切换可重复异常、卡死/对象生命周期警告，或取得完整原命令/顺序/dump时重新调查。见 `P37_QT_NATIVE_ISSUE.md`，不因本轮源码或未来打包成功宣布根治。
