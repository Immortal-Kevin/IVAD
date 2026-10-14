# P2 Test Distribution 测试结果

日期：2026-10-14。版本：1.0.0-P2-Beta.1。冻结源码：`db81c49`；完整提交号见包中 BUILD_INFO.json。仅 P2 测试分发与必要修复，未进入 P3–P6 业务开发。

## 结论

技术功能验证 PASS；分发批准 BLOCKED；历史证据保护 FAIL。不能以功能结果掩盖许可或保护问题，也不能将本轮称为 P2 正式发行 PASS。

## 构建和固定资产

- PyInstaller 6.22.3 onedir，Windows x64；独立 `.venv-distribution`，复用原 P2 运行库的相同版本文件，不安装或修改原 `.venv-p1`／`.venv-nvidia`。
- 使用 Git archive 的固定源码快照构建。构建期间开发目录后续仅修改测试输出保护及文档；包的源提交与完整文件 SHA256 独立记录。
- 版本和图标已写入 IVAD.exe Windows 资源；无代码签名，Authenticode=NotSigned。
- ZIP：98,806,690 bytes（98.81 MB）；程序 EXE：9,903,314 bytes（9.90 MB）；解压内容约 250.19 MB。
- Setup 安装版未生成：便携版分发审核未通过，不推进第二交付目标。没有管理员安装、驱动修改、全局 Python 或 CUDA Toolkit 安装。

## 实际测试环境

唯一物理环境：Microsoft Windows 11 专业工作站版，build 26200，x64，RTX 5070 Ti 16GB，驱动 617.42；进程未提升权限，WindowsPrincipal 管理员检查为 False。没有创建其他 Windows 用户账户，没有第二块 NVIDIA GPU，没有完成干净 VM。

| 要求 | 结果 | 真实边界 |
| --- | --- | --- |
| 独立 EXE 启动 | PASS | 实际 PyInstaller EXE，非 venv 内运行源码；PATH 仅 Windows/System32，移除 PYTHONPATH/PYTHONHOME。 |
| A NVIDIA 电脑但没有 Python | NOT TESTED（场景本身） | 本机有开发 Python；独立冻结运行作为替代证据，不冒称目标电脑未安装 Python。 |
| B 没有 NVIDIA 独显的办公电脑 | NOT TESTED | Lite 逻辑拒绝 Worker 且不加载 torch/ORT 已验证，但未获得无 NVIDIA 实机。 |
| C 中文和空格目录 | PASS（目录）；NOT TESTED（用户名） | EXE 和项目路径含中文、空格；本轮 Windows 用户名非中文。 |
| D 非系统盘 | PASS | 程序和测试项目实际位于 E 盘。 |
| E 普通权限 | PASS（未提升） | 当前进程无管理员 token；独立标准用户账户及不同用户之间部署未测。 |
| F 真实断网 | NOT TESTED | 核心流程只用本地文件，无联网业务、自动下载和上传；未断开系统网络或修改防火墙。 |
| AppData 独立目录 | PASS | 正常无参数启动创建 LocalAppData/IVAD/IVAD P2 Beta/P2Beta；不向程序目录写应用数据库。 |
| 程序目录拒绝写入 | NOT TESTED | 已采用用户可写 AppData 设计；未改变目录 ACL 或到 Program Files 做真实拒绝写测试。 |
| ZIP 解压后异目录启动 | PASS | CRC 正确；重新解压到另一中文空格目录，实际启动新的 EXE 进程。 |
| 关闭／新进程重开项目 | PASS | 真实 Windows 原生目录选择提交，恢复 REVIEWED、矩形、多边形、ROI 和标注修订1。 |

## 功能及 GPU 规则

原有 84 项加新增 2 项：86 passed，0 failed，0 errors；安全输出修正后的最终回归耗时 43.06 秒。原始 XML/log 位于本轮 artifacts。开发 pytest 进程有 Windows COM fatal exception 0x8001010d 诊断栈，之后测试通过且退出码 0；原因未定位，保留记录，不声称已修复。最终冻结 EXE 运行没有该异常输出，实际退出码 0。

以下 15 条来自实际冻结 EXE 的 Qt GUI／后台真实链路；文件选择返回值和部分确认响应在自动核验中注入已知测试路径／Yes。不是模拟后台成功。除真实原生打开项目选择框外，其他原生选择框最终提交仍待人工复测。

| 核验 | 状态 |
| --- | --- |
| standalone GUI startup without development Python PATH | PASS |
| bundled FFmpeg generates and decodes five owned codec/container samples | PASS |
| GUI create project and migrations 0004 on Chinese space path | PASS |
| GUI batch import H264 HEVC AVI MOV MKV | PASS |
| GUI playback pause and timeline seek | PASS |
| GUI save real CLIP; original hash unchanged | PASS |
| new CLIP actually plays | PASS |
| fixed sampling creates ten actual images | PASS |
| change sampling and baseline run | PASS |
| GUI fault label create and select | PASS |
| GUI rectangle polygon ROI review and save | PASS |
| GUI dataset freeze and YOLO export | PASS |
| Lite denies AI with CPU/GPU selections; no torch or ORT loaded | PASS |
| GUI diagnostic ZIP export contains allowlisted JSON only | PASS |
| new GUI window reopens project with persisted annotations and ROI | PASS |

视频素材全部为本轮自制 4 秒、10 fps、320×180 色块，无现场或第三方视频。MP4/H.264、MP4/HEVC、AVI/MPEG4、MOV/H.264、MKV/H.264 均独立编码、读取／导入 READY；播放定位和保存／再次播放／抽帧闭环实际用 H.264。不能推断所有封装／编码组合、HEVC 完整倍速播放、4K 或小时级录像均通过。固定间隔本例真实生成10张；变化筛选实际生成候选。

普通双击无参数启动后，通过真实 GUI 可选硬件诊断：NVIDIA GeForce RTX 5070 Ti，16303 MiB，617.42，CC12.0；Worker Installed=False、backend_available=False、backend_validated=False、CUDA test NOT TESTED。没有把探测到硬件写成推理通过。相关材料 `native-hardware-diagnostics.json`。

P2 Lite 不包含 PyTorch、ORT、Ultralytics、YOLO 权重或 AI Worker。CPU/GPU/空选择调用 AI 设备要求均被明确拒绝；普通视频与人工数据处理可用 CPU。其他 RTX 20/30/40/50 与若干专业卡仅做官方架构静态分析，具体机器 REQUIRES VALIDATION / NOT TESTED，见兼容性矩阵。原 5070 Ti CUDA/YOLO PASS 仅引用原 P0 范围，不代表本 Lite 执行模型。

## 分发内容、隐私和许可证

ZIP 包含 EXE、DLL/PYD/标准库、SQLite/Alembic 0001–0004 资源、图标和版本信息、安装操作指南、快速开始 PDF、GPU矩阵、兼容性反馈 CSV、原业务测试 XLSX、版权说明及文件清单。扫描未发现原视频、抽帧、数据库、权重、venv、开发日志、缓存、Torch/ORT/Ultralytics 或已知本机私人路径。Word/Excel 的个人编辑者元数据已从包内副本移除；没有修改原正式指南。

诊断 ZIP GUI 导出实测：只有 environment.json、hardware.json、errors.json、manifest.json，默认排除媒体／项目数据库／任意系统文件／配置凭据；路径和凭据脱敏。导出前有检查提示，不上传服务器。发送前仍由测试员检查。

FFmpeg 通过 PyAV 15.1.0 wheel 的 DLL 运行，不依赖开发机 ffmpeg.exe；构建选项、全部 DLL 文件名与 hash、库版本及运行时许可标签可查 licenses/LICENSE_AUDIT.json 与 FILE_MANIFEST.json。存在 --enable-libx264／--enable-libx265，运行时标签 LGPLv3+，但没有完整可核实的下游商业例外条款与对应源码／构建资料。Qt/PySide 的 LGPL 动态链接、对应源码与重新链接义务亦需发行审核。已附可获取的许可证和 PyInstaller bootloader exception，不宣称商业再分发权通过。

官方资料：[FFmpeg legal](https://ffmpeg.org/legal.html)、[PyAV 上游许可说明](https://github.com/PyAV-Org/PyAV/issues/2270)、[Qt for Python licenses](https://doc.qt.io/qtforpython-6/licenses.html)、[PyInstaller exception](https://pyinstaller.org/en/stable/license.html)。BLOCKED 依据用户明确要求“许可证或再分发权不明确应记录 BLOCKED”，不是通过 Beta 字样豁免许可。

## 历史证据保护失误及处置

首次回归没有指定隔离输出，旧用例写回历史目录。这是本轮执行失误。对照既存基线，以下3份内容已变化，未在项目 artifacts/docs 中找到匹配原 SHA256 的副本：
- artifacts/p2/gui/annotation.png
- artifacts/p2/gui/dataset.png
- artifacts/p2/regression/device-live.json

另外 artifacts/p2-adjustment/gui-clip-save.png 被重新写入；本轮开始前未有该文件 hash，不能证明它与旧版相同。两张旧 regression 的项目／生产截图虽被重新保存，SHA256 与基线相同。没有补造旧图，也没有把当前图冒充原证据。原 P2 报告和原始 XML/log 未改写。

已修正4个测试文件的默认输出为唯一 artifacts/test-runs 路径，并支持显式本轮目录。最终再次回归86通过，包含之前受影响文件在内的 551 份保护目录文件自处置基线以来没有继续变化；这是处置后的保护，不是整个任务都未变的证明。P0、P1环境包清单保持一致（environment-preservation.json），原训练环境没有修改。历史保护项仍 FAIL，恢复需取得真实备份，不能靠重新运行生成代替旧证据。

## 证据目录

- build-final.log / build-requirements-lock.txt / source-db81c49 / source快照ZIP。
- regression-final.xml / regression-final.log。
- 最终 EXE 验证/deployment-results.json、final-exe-run.log、真实生成媒体／帧／CLIP／标注／导出目录。
- native-zip-reopen.json、native-hardware-diagnostics.json。
- history-screenshot-audit.json、contained-preservation.json、environment-preservation.json。
- payload-audit.json、distribution-summary.json、final-quality.json、install-page-map.json、doc-render/page-*.png。

## 文档及校验

安装指南17页 A4，首页快速上手独占1页，新增2页解压／Lite／诊断；复用13张真实旧 P2业务截图并注明来源。通过 Microsoft Word 实际分页、更新 PAGEREF 和 PAGE，再用 Poppler逐页查看；首页正文页码为5、5、6、7、8、9、11、12、14、17。快速开始PDF为A4一页，中文字体、表格、页边无溢出。原指南、原业务测试表保留不覆盖。

SHA256 校验与 ZIP CRC通过，文件清单见包内 FILE_MANIFEST.json：

```text
19acdfe0a2fe1efe280d960a3e794805d3bcbf889800f32e1cac6777d21591b9  IVAD_Platform_v1.0_P2_Beta_Portable.zip
16efb0e4ee05b25f1aeee4a5fb19f35278a3c38ef09a62d9bd09a587a8d8a80c  IVAD_Platform_v1.0_P2_Beta_Portable/IVAD.exe
```

当前只可交用户审阅本机候选包，不建议直接发送普通测试员。需完成许可证／源材料审核、处理历史保护失败并补测实际办公电脑及跨机器环境。完成后停止，未进入 P3。