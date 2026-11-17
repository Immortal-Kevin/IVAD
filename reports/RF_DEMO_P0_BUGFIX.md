# RF Demo P0 闪退修复与去姓名

2026-10-19；仅本轮BUGFIX。未训练、下载模型、修改环境/驱动、审计许可证或进入P3.7-B。最终文件保护及SHA见 `artifacts/rf-bugfix-20261019/final-protection.json`。

## 根因与最小复现

三次Windows Application Error/WER均指向旧GUI `IVAD_RF_Demo.exe` 的 `avutil-59.dll`，异常 `0xC0000005`、偏移 `0x105DC`，落在导出 `av_dict_free` 函数内。原始WER和三份Worker日志已复制封存，没有覆盖。

不启动GUI、不加载模型，使用原PyAV15.1及原FFmpeg DLL，`av.open(video, options={'protocol_whitelist':'file'})` 对用户指定视频稳定复现访问冲突，实际退出码 **3221225477 / 0xC0000005**；faulthandler停在 `av.open()`，尚未取得首帧。文件虽为.mp4扩展名，真实容器是MPEG-PS/H.264；不是因改后缀而修复。中文路径的标准MP4对照正常，排除了“中文路径必然失败”的猜测。

同DLL原生探测记录：用户视频流数量在 `avformat_open_input` 后为0，`avformat_find_stream_info` 后为2；合成MPEG-PS为0→1，标准合成MP4为1→1。[PyAV15.1原始代码](https://raw.githubusercontent.com/PyAV-Org/PyAV/v15.1.0/av/container/input.pyx)按探测前流数分配全局options数组、按探测后流数清理，动态新增流时越界，和WER故障函数及对照结果吻合。将仅用于容器的协议白名单移到 `container_options` 后，真实及合成MPEG-PS均通过；保留同一DLL、模型及本地文件白名单。

独立当前Nano Worker对用户首帧1280×720执行384输入、阈值0.5真实CUDA前向成功，退出码0，无超过阈值目标。证据：`A-current-worker.jsonl`、`A-exit.json`、`decode-isolation.json`、`synthetic-ps-ab.json`、`native-stream-counts.json`和对应stdout/stderr（均在本轮artifacts目录）。本次可复现崩溃发生在解码打开阶段，不是模型首次前向、OOM或Qt控件绘框阶段。

## 最小修复

- `demo_rf/decode_entry.py`（新增）：容器选项修正；PyAV仅在独立进程运行，保持真实PTS/背压和采样规则。
- `demo_rf/gui_entry.py`：QThread仅桥接子进程消息，通过显式QObject Slot更新界面；解码或CUDA Worker失败时保留GUI、中文原因和退出码；等待线程/进程结束后再允许重开或关闭。
- `demo_rf/diagnostics.py`（新增）：保留每次运行的启动参数、stderr、Python异常、faulthandler原生栈及退出记录；不记录图像像素。
- `demo_rf/worker_entry.py`：日志与前向阶段记录、OOM异常清理后退出、去姓名；继续结构化错误、CUDA-only。
- `demo_rf/gui.spec`：增加独立解码console EXE，使用重定向管道且隐藏控制台；`freeze_worker.py`仅增加本轮独立构建输出目录参数。
- `demo_rf/model_manifest.json`及新候选随包手册/范围文案去姓名；统一“仅限IVAD办公电脑本地演示，不向厂方提供软件副本”。未改真实数据或第三方作者署名。

日志默认路径：`%LOCALAPPDATA%\IVAD\RF Offline Demo\diagnostics\<运行编号>\`。历史会话不删除；退出只清理本实例临时预览。原权重字节未修改。

## RTX5070Ti 实际EXE验收

| 检查 | 实际结果 |
|---|---|
| 第1轮：合成MPEG-PS，384/阈值0 | 解码100帧、CUDA推理4帧、57个真实低分框；界面显示类别/置信度；GUI/Worker退出0 |
| 第2轮：用户指定真实录像，384/阈值0.5 | 完整解码1751帧、CUDA推理71帧、0个超阈值目标；明确空结果；GUI/Worker退出0 |
| 第3轮：标准H.264 MP4，384/阈值0.5 | 解码40帧、CUDA推理2帧；GUI/Worker退出0 |
| 暂停/继续 | 540帧计数暂停后保持不变，继续后增加 |
| Worker失败隔离 | 主动终止测试Worker（故障注入，非自然复现）后GUI存活，显示-1/0xFFFFFFFF及日志目录，可重开 |
| 取消 | 720个已推理帧时取消，两个子进程停止，GUI正常退出0 |
| 新路径启动/关闭 | 指定目录实际完成2帧CUDA推理；再次启动Worker时关窗，GUI退出0，无子进程遗留 |
| 姓名 | 检查实际编译入口代码常量、源码和随包文本；无指定使用者姓名 |

证据：`three-rounds.json`、各轮complete/exit/logs、`pause-start/stable.json`、`injected-worker-failure.json`、`cancel-final.json`、`deployed-complete.json`、`close-active-final.json`、`name-check.json`。另有一次未执行识别的空白窗口已正常退出，不计为完整识别轮次。合成视频阈值0仅验证显示链路，不能用这些框宣称现场准确率。

## 交付与剩余边界

新路径：`[本地路径]`；完整onedir和新SHA256SUMS保留。原 `dist/IVAD_RF_Demo_Candidate` 未改，作为回滚副本。原Lite全部387文件、受保护原候选EXE、权重及用户视频做SHA保护检查。Git历史未改，两份原未跟踪规划文档保留。

本轮已知、可复现的av_dict_free触发条件已修复，三轮回归无闪退。不能据此声称所有原生异常根治：新路径一次faulthandler记录 `0x8001010D`，但GUI继续完成任务并退出0；没有对应新APPCRASH。已补充 `P37_QT_NATIVE_ISSUE.md`，**IVAD-QT-001仍OPEN/PARTIAL，原始根因仍未确定**。RTX3050Ti/目标办公电脑及真实OOM仍未实测；既有许可未决状态不变。本轮停止，PACKAGING_FREEZE=TRUE。
