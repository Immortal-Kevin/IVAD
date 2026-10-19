# P3.7-A Windows Qt 原生异常调查

日期：2026-10-19。结论 **PARTIAL：根因未确认**。未据操作系统、驱动、Qt或Python模块名直接归因，也未声称修复原异常。

## 原始证据

原日志 `artifacts/p37a-20261016/regression.log` 原样保留，858字节，SHA256 `3908392558dd1448843376687ce2a49a5a5808b3e2545424104dfd3a9bbbbd9b`。含 `0x8001010d`、access violation及SQLAlchemy `engine/default.py:945` / `database.py:51` 工作线程片段，但没有失败nodeid、完整主线程或原始命令/测试顺序。33个进度点不能唯一确定触发用例，因此不能声称已经精确复现原始失败用例或完成因果二分。

本轮只读采集Application事件1000/1001，见 `windows-events.json`、`wer-details.txt`。2026-10-16 20:07:41事件1000报告Python312.dll、0xc0000005、offset0x287730；20:07:51 WER记录c000041d，与原日志20:07:52落盘时间相邻。异常模块位于Codex捆绑Python运行时，不是证明该运行时负责的证据。未找到可据此分析的完整原始内存转储/符号栈；不修改系统WER或COM配置。

## 排查与真实复验

使用`.venv-p1`、Python `-X faulthandler`、`PYTHONFAULTHANDLER=1`、必要Qt QPA日志；最终大批次设 `faulthandler_timeout=45`。平台实际为 `windows`，本轮没有用offscreen替代原生结果。

| 调查点 | 实际检查与结论 |
|---|---|
| QComboBox/QMenu及C++包装生命周期 | 原RF GUI单测；新增菜单弹出/关闭/deleteLater和异步刷新压力、两次窗口/服务重建。未复现原访问异常，不证明无所有权缺陷 |
| QWidget/QObject所有权 | QTimer以页面为父；QMenu压力夹具以页面为父。检查MainWindow/TrainingPage/AsyncRunner/VideoPlayer关闭代码；未定位与原异常相连的错误释放 |
| 跨线程signal/slot | AsyncRunner完成信号连接QObject Slot，后台不直接写训练控件；VideoPlayer通过队列关闭、解码信号回GUI。检查不替代线程竞态证明 |
| 定时器/异步结果 | 训练页刷新有busy和root/model门禁；本轮主任务列表新增项目ID门禁，防止切项目后旧查询回写 |
| Worker取消/关窗/GPU锁 | 原26项RF契约回归、当前队列取消、跨进程锁/自有进程树测试；真实副本CUDA验证完成，无模型误登记；未重复真实GPU训练关窗实验 |
| QApplication/fixture | pytest-qt qapp为session作用域；初次新增测试复用了被MainWindow.close关闭的服务容器导致等待超时，修正为真实新容器重启。这是本轮夹具缺陷，不能冒充旧原生崩溃根因 |
| Windows COM | 独立GUI探针通过CoGetApartmentType只读记录建QApplication前后状态（native-real.json）；没有调用CoInitializeEx改变线程模式；不足以解释历史异常 |
| 合并批次共享状态 | 最终合并 `1 failed, 86 passed, 1 skipped in 104.62s (0:01:44)`；没有原生访问异常。唯一旧GUI断言冲突及既有条件SKIP见Closure，未删除/屏蔽它们 |

原生单独压力测试15项通过，RF专项26项通过，150% DPI专项1项通过（最终串行复验日志见目录）；真实数据副本另行主窗口打开/缓存回放/关闭成功。较大批次当前未重现致命异常，因此没有可重复失败组合用于可信二分。不能推断历史问题只发生于合并批次。

## 修复与剩余条件

本轮修复的是后端/历史隔离、队列历史投影、兼容数据预检与项目回写门禁；未提交假设性的Qt生命周期重构。复验未复现不等于已归因。需要可重复原始命令/顺序或新的完整原生转储后才能做触发组合二分和最小Qt修复；对应验收保持PARTIAL。
