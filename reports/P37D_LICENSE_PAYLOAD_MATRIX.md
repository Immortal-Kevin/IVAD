# P3.7-D 增量许可门禁

日期：2026-10-19。**LICENSE_PAYLOAD_STATUS=BLOCKED；没有最终 Payload。** 复用 P37L 原始材料，不重做四环境完整审计。下面区别“既有安装”“研究输入”“最终携带”，不把本机安装等同于再分发授权。

| 组件 | 当前准确输入/证据 | 最终携带状态与缺口 |
|---|---|---|
| PySide6/Shiboken/Qt | 6.8.3；历史真实运行 Core/Gui/Widgets/Svg/qwindows；本轮原生 GUI 回归正常 | 未构建。按这五项起建白名单，图像/样式插件另测；不整体收集 Addons。Charts/DataVisualization/Quick3D/VirtualKeyboard 等未批准携带 |
| Qt 对应源码 | qtbase、qtsvg、qtimageformats、pyside-setup 四份6.8.3归档，全部官方 SHA256 匹配，pyside-setup含 PySide/Shiboken 来源 | 已准备，不代表全部义务落实；最终二进制来源/静态第三方对应、适用通知和安装说明仍须逐文件核对，最终载荷尚未附带源码 |
| Qt 替换权 | 计划动态 DLL、独立目录，无防替换/调试限制 | 未执行兼容替换后实际 IVAD EXE 启动/退出，不填 PASS；也未修改 Qt 库 |
| 现有 PyAV | GUI15.1.0，旧 FFmpeg61.19.101；wheel 实有 x264/x265 DLL，旧人工片段用libx264 | 不批准直接复用。返回LGPL字符串与含x264/x265构建不能替代来源/链接审查，也不在此宣判违法 |
| 免费 FFmpeg 研究输入 | BtbN `autobuild-2026-07-31-14-10`，n7.1.5-12-g1fdbca85aa；发布校验匹配；实际7个共享DLL，配置禁用x264/x265、没有enable-gpl/nonfree | **研究用，未批准随IVAD携带。** archive230项含头文件，无完整`.c`源码、无源码归档；该release无source asset/body说明。不等于上游无法提供源码，需要取得与该构建、补丁及静态依赖准确对应的完整材料 |
| PyAV 与替代FFmpeg集成 | libavcodec61/libavutil59主要ABI相近 | 未编译/重新链接PyAV，不能以同ABI或改名替换冒充兼容验证；没有修改/隐藏旧DLL名称规避检查 |
| OpenCV | GUI输入计划不需要；RF环境已装headless5.0.0.93历史材料复用 | 最终RF闭包未生成。未把OpenCV的Apache声明当作自带FFmpeg授权；不可声称已排除所有视频后端 |
| Torch/RF-DETR | 研发2.9.1+cu128 / RF1.11.2，当前仅开发机参考检查 | 未生成独立可携带Worker，不复制整个开发环境；保留源码GUI/Registry不代表便携Worker已可用 |
| NVIDIA | 历史22种CUDA/cuDNN DLL的准确来源/SHA/资源版本在P37L NATIVE.json/BINARY_VERSIONS.json | 最终携带零文件，因为没有最终包；**不是许可PASS或“无需审查”。** 逐DLL适用EULA、redistributable、条款主体和通知仍未闭合，不携带驱动 |
| 公共Nano权重 | 来源和SHA见`packaging/p37d/source-materials.json`、P37L RF_WEIGHT.json | 未下载、未复制、未携带。未使用私有工业权重代替公共资源 |
| Python/MSVC/其它GUI依赖 | 14包输入计划及P37L平台补表 | 最终运行时/复合许可证及通知仍须按实际闭包收集，不能把旧环境材料复制一遍就填PASS |
| PyInstaller | 历史6.22.3工具许可/bootloader例外已有材料 | 本轮未在新环境安装、未执行构建，未修改bootloader |
| Ultralytics | 正式输入禁止，历史代码保留 | 未做最终文件名/内容/PYZ模块/动态导入/失败回退/运行模块检查；没有最终包不能填写“零残留PASS” |

研究 FFmpeg 的7个DLL逐文件 SHA、来源archive和未闭合状态已记录到 `packaging/p37d/source-materials.json`。该清单明确不是最终EXE/DLL清单。Qt四份源码共69,082,516 bytes；不直接把公共归档大文件提交Git，真实本地材料和官方URL可按索引核验。

免费路线仍可行，未发现必须购买商业许可的证据。首选进一步完成 LGPL 共享构建的准确源码/构建脚本/静态依赖通知，再验证 PyAV 重链接和编码器替换。另一条路线是 Windows Media Foundation：本机CFR CLI编码成功，但微秒时基实验失败、目标OS/MFT未知，尚不能直接替换现有业务。MPEG-4 Part 2也有免费实现，但VFR实验存在帧数/PTS差异；若最终必须改变输出格式或精度，应先给用户具体影响结果再决定，不能擅自降低抽帧/片段能力。

开源版权与编码专利分开：去掉GPL编码器或使用系统MFT，不自动解决H.264/H.265或其它codec在特定地区/用途的专利问题。本轮没有以“内部使用”豁免第三方义务，也没有授权外部发行。

依据：[Qt LGPL义务](https://www.qt.io/development/open-source-lgpl-obligations)、[FFmpeg合规说明](https://ffmpeg.org/legal.html)、[BtbN构建变体及构建方式](https://github.com/BtbN/FFmpeg-Builds/blob/master/README.md)、[固定研究版本](https://github.com/BtbN/FFmpeg-Builds/releases/tag/autobuild-2026-07-31-14-10)、[CUDA12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html)。本次没有代公司接受条款或开源自研源码。
