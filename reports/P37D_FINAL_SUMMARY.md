# P3.7-D 最终收尾

日期：2026-10-19。**未生成IVAD EXE，当前不能发送给同法人研发部领导。** 本轮在D2许可门禁停止，完成最小输入分析、公开源码材料准备、免费视频原型、源码针对性回归和原资产保护；未达到本次构建/交付目标，不能宣告任务验收PASS。

## 实际成果

- 从`458e32688638ecea630fa98ad427df52bc5652c3`创建`feature/p37d-internal-demo`，保留原分支与`nvidia-first`。新增两份工程脚本、输入来源/状态文件、待验收中文指南及本组七份报告；没有改应用、测试、schema或旧打包脚本。
- 独立创建`.venv-p37d-build`，未修改旧环境安装包或系统/驱动。没有复制整个开发环境。
- 下载Qt6.8.3的qtbase/qtsvg/qtimageformats/pyside-setup四份源码，69,082,516 bytes，全部匹配官方SHA256；最终DLL对应/第三方材料及替换后EXE运行未验收，所以Qt分发义务仍PARTIAL。
- 固定LGPL共享FFmpeg研究包62,425,578 bytes，发布校验匹配，实际配置禁用x264/x265；7个DLL的SHA/来源已列索引。完整对应源码/静态依赖及PyAV链接尚未闭合，未宣称是合规成品载荷。
- Windows源码原生GUI/媒体/标注/数据集针对性14项PASS，24.96秒。是独立空白项目及合成夹具，不能代替无需Python的EXE验收。
- 合成CFR/VFR H.264各40帧，替代工具解码与抽帧通过；CFR的mpeg4和h264_mf片段通过；VFR片段配置有PTS/帧数失败，微秒时基h264_mf失败，原始日志均保留，未集成到应用。
- RTX5070Ti独立RF环境Torch导入及小张量CUDA通过；没有RF模型新前向/训练。RTX3050Ti 4GB完全未实测，未宣称Batch4/Batch1可用，源码尚缺完整4GB准入门控。

## 判定

| 项目 | 结论 |
|---|---|
| EXE路径、大小、SHA256；onedir大小 | N/A，未生成，不借用上游FFmpeg.exe或历史IVAD冒充 |
| BUILD_STATUS | BLOCKED_D2_NO_EXE |
| LOCAL_FUNCTIONAL_STATUS | NOT_TESTED_CANDIDATE，源码参考14 PASS |
| VIDEO_IMPORT_EXTRACTION_STATUS | NOT_TESTED_CANDIDATE，研究CLI解码/抽帧PASS |
| RF_3050TI_COMPATIBILITY_STATUS | NOT_TESTED |
| LICENSE_PAYLOAD_STATUS | BLOCKED，Qt/PyAV/FFmpeg/平台运行时/NVIDIA最终闭包未验收 |
| CONFIDENTIALITY_STATUS | NOT_TESTED_PAYLOAD；本轮原资产保护5组全部true，2,328文件不变 |
| Ultralytics残留 | 最终载荷NOT TESTED；历史代码保留，不能宣称已完成最终零残留扫描 |
| 真实工业数据泄露 | 本轮未交付/上传工业数据或私有模型；没有成品可作载荷泄露验收 |
| SAME_ENTITY_INTERNAL_DELIVERY_STATUS | BLOCKED，不能发送 |
| P3.7-A功能/迁移技术历史验收 | 原PASS不改写，不等同本轮EXE通过 |
| IVAD-QT-001 | OPEN/PARTIAL；本轮未复现，原始根因仍未确定 |
| 整体Ultralytics迁移 | PARTIAL，保留P3.7-A历史边界，未补成所有功能/发行均PASS |
| 正式软件发行 | DISTRIBUTION_STATUS=BLOCKED |
| 打包冻结 | PACKAGING_FREEZE=TRUE，已恢复 |

具体缺项见`P37D_INTERNAL_DELIVERY_READINESS.md`的D-B01–07：先完成免费视频二进制/源码/通知和链接、可靠片段PTS、Qt兼容替换、RF/显存门控及NVIDIA映射，再构建和验证空白离线EXE、扫描最终依赖/隐私，最后单独判定同法人内部交付。未证明必须购买商业许可；不要求用户公开任何私有录像/标注/权重。目标机信息和受控访问仍需公司提供。

## Git与保护闭环

最终Commit：本报告所属的本地Git提交，执行`git log -1 --format=%H -- reports/P37D_FINAL_SUMMARY.md`可取得完整值；提交后回执`artifacts/p37d-20261019/closeout.json`及本轮最终回复记录同一SHA。所有本轮变更一次本地提交，不上传远程。

保护核验覆盖原项目全表、2,328个原项目/媒体文件、两份原未跟踪规划文档、Qt原始日志/Windows Event/WER、四个旧环境登记的native/notice/METADATA及原分支指针；前后结果见`protection-result.json`。两份规划文档继续未跟踪、不提交。未删除数据库/权重/缓存、未改历史、未重训、未进入P3.7-B/P4、未发布源码、未发送任何目录。

本轮完成阻断收尾后停止，等待用户审阅；不会自动继续构建或扩大交付范围。
