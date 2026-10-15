# 当前任务

2026-10-15 P3 Dataset Hotfix v2 PASS。四Tab保留，顶部筛选142→72px，正常/异常/当前有效全选与计数、动态项目提示、Tab待添加及草稿去重完成。

8525时长70.040秒、起始PTS对应52241.877778秒；旧数据集列表误直接展示pts_us。200条既有time_us全部正确，本轮统一派生媒体/原视频时间，不写回历史。真实副本三处5.800秒一致，正常16/异常184/合计200批量选择与重复添加验证通过。

最终A66+B31=97不同用例通过，200% GUI专项1项重复通过。165项选取保护哈希0变化，SQLite只读备份逻辑一致，Schema0008无迁移。报告：P3_DATASET_UX_HOTFIX_V2.md、P3_FRAME_TIMESTAMP_INVESTIGATION.md、P3_DATASET_SELECTION_TEST_RESULTS.md。

P3已有成果完成，不重训、不重复开发；真实单来源LIMITED仍需补充独立来源。Hotfix完成后停止待审，PACKAGING_FREEZE = TRUE，无EXE/Portable/Setup，不进入P4–P6。历史Qt原生访问冲突未定位限制保留。
