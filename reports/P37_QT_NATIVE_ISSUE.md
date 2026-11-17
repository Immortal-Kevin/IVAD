# IVAD-QT-001：历史 Windows Qt/Python 原生异常

登记日期：2026-10-19。状态 **OPEN / PARTIAL**。独立于 P3.7-A 功能与迁移验收；不能用功能测试通过关闭该问题。

历史证据保留：`artifacts/p37a-20261016/regression.log`、`artifacts/p37a-closure-20261019/windows-events.json`、`wer-details.txt`，以及 [原调查报告](P37_A_QT_CRASH_INVESTIGATION.md)。日志出现 `0x8001010d` / access violation；相邻 Windows Application/WER 事件涉及 Python 原生异常。现有证据缺少完整主线程栈、可重复测试顺序和原生转储，根因仍未确定；不能归咎于 Qt、Windows、驱动或具体应用代码。

本轮结论用语：**本轮未复现，原始根因仍未确定。** 未提交 Qt 生命周期修复，未屏蔽异常，未改系统 COM/WER 设置。历次 PARTIAL 结论保留为历史事实；不声称已根治。

满足任一条件时重新调查：

1. GUI/原生测试再次出现上述异常码、access violation、`0xc0000005`、`0xc000041d`，或相似 Windows Application Error/WER 事件。
2. 下拉菜单、QMenu、定时刷新、项目切换、取消任务或关窗出现可重复崩溃/卡死、已销毁 QObject 引用或跨线程控件警告。
3. 获得原始完整测试命令、nodeid/执行顺序、原生转储或足以缩小失败组合的新证据。

重新调查时保留失败日志与文件哈希，记录时间/进程ID、解释器、Qt/PySide版本、平台插件、DPI、测试顺序及活动Worker；启用 faulthandler/Qt日志并只读采集对应Windows事件。先独立进程复现，再合并并缩小顺序/共享状态；有明确应用缺陷证据后才实施最小修复。不可重复时继续PARTIAL，不以offscreen结果替代原生验收。

本问题未自动授权 P3.7-B、P4、重新训练、系统环境变更、打包或正式发行。


## 2026-10-19 RF Demo P0 Bugfix 补充（保持 OPEN / PARTIAL）

RF Demo 的三次GUI闪退已在独立解码进程复现为 `avutil-59.dll / av_dict_free / 0xC0000005`，触发条件是PyAV15.1全局options数组清理与MPEG-PS动态发现流数量不一致；该问题有独立复现及修复证据，不等同于本历史Qt问题。

本轮新增GUI faulthandler在新目录启动检查中记录一次 `0x8001010D`，Python栈仅落在 `QApplication.exec()`；该进程随后完成2帧真实CUDA任务，继续响应关窗并以0退出，未发生对应Windows APPCRASH。不能将faulthandler的“Windows fatal exception”字样直接解释为该进程已闪退，也不能因此忽略原始记录。原生调用栈/转储仍缺少，原始根因仍未确定。证据：`artifacts/rf-bugfix-20261019/deployed-final-logs/gui-fatal.log`、`gui-events.jsonl`、`deployed-exit.json`及`windows-events-after.json`。

本轮三次完整识别/退出均以0结束，仅证明该回归范围通过；不关闭IVAD-QT-001。原有重新调查触发条件继续适用，若该异常伴随实际非零退出、冻结、WER故障或可重复Qt交互序列，再针对原生线程栈调查。未修改Qt或系统COM设置。
