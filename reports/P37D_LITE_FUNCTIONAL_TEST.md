# P3.7-D Lite 真实EXE功能验收

日期：2026-10-19。范围仅北京金海泽地智能科技有限公司同法人研发部内部演示；接收方授权已确认，不再要求重复确认。本轮遵循新的Lite授权，先生成本机候选再审实际载荷。

源码/构建提交：`26dd8bcf10490384bcb993df4e0d38d35a9f9f8a`（其父工程提交`3fff1f734a2454f501a5b695f1adb8b76827a9aa`）；最终报告提交由本报告所属Git提交确定，提交后回执`artifacts/p37d-lite-20261019/closeout.json`和最终回复记录完整SHA。分支`feature/p37d-lite-demo`，基线`8b064b5e5fa8711e75293f189266aad99d92c502`。

最终测试对象是上述源码提交实际生成的`IVAD_Internal_Demo.exe`，不是源码测试替代。当前非AI功能本机通过，目标机NOT TESTED。

| 检查 | 实际结果 |
|---|---|
| 正常入口GUI启动/退出 | PASS；初始正常入口及最终候选原生Qt窗口运行成功，qwindows实际加载 |
| 空白首启/新项目 | PASS；项目初始无摄像头、录像、图片、标注类别、数据集或模型 |
| 保存、关闭、重开 | PASS；GUI保存名称后关闭/重开，UUID及数据保持 |
| 摄像头 | PASS（EXE内真实服务创建/编辑、UUID保持及媒体关联）；管理对话框全部人工步骤未逐项验收 |
| H.264导入 | PASS，独立合成CFR/VFR MP4各40帧，320×180 |
| 显示、播放、暂停 | PASS，真实Qt播放器显示图像且播放位置变化，暂停状态确认 |
| VFR时间戳 | PASS，40个解码PTS与输入非均匀真实PTS逐项一致；抽帧PTS均来自该集合，未按FPS伪造 |
| 抽帧/图片浏览 | PASS，12张真实PNG，尺寸和哈希核验 |
| 人工标注 | PASS，画布鼠标事件绘制矩形框/多边形、保存异常；GUI手动标正常，负样本无目标 |
| 草稿/划分/冻结 | PASS，真实GUI保存草稿并检查、冻结1个版本；单视频来源LIMITED仅为工程实验，不是工业质量认证 |
| 默认Native/显式COCO | PASS，各12图、2目标、11正常负样本；图像与manifest哈希完整，原来源关系保持 |
| 进程重启 | PASS，另一个EXE进程重开同项目，框/多边形、12帧和冻结版本持久化 |
| 禁用功能后台绕过 | PASS，训练/离线/片段队列、AI handler注入、直接片段服务、直接训练和旧缓存读取均拒绝；没有新建绕过任务 |
| 动态导入/CPU回退 | PASS，Torch/Ultralytics/RF/ORT动态导入被阻止，无AI模块加载，不存在静默CPU AI回退 |
| 离线约束 | PASS（已观测范围），正常流程Python网络审计0次；原生FFmpeg对测试HLS的HTTP引用明确报不在`file`白名单，阻止原生网络路径 |
| 程序与数据分离 | PASS，测试前后程序文件哈希不变且无新__pycache__，项目/视频/标注/导出写到独立数据目录 |

证据：`artifacts/p37d-lite-20261019/release-acceptance/results.json`、`restart-results.json`、`release-processes.json`及原生窗口截图。文件选择和确认响应由自动化注入；窗口、事件处理、后台任务及导出均为真实EXE。未声称所有系统选择框经过完整人工测试。另有32项源码针对性回归通过（23.84秒），包括Lite门禁与必要P2/P3迁移回归，仅作补充；未重训。历史SKIP/XFAIL原因保持，本轮不把未运行的历史节点改为PASS。

AVI/MOV/MKV/H.265未对最终候选实物验证；源码旧解码环境的容器测试不能转移为此候选的PASS。4GB GPU训练不适用于本版；无CUDA开发环境变量下的基础流程已测，但无NVIDIA驱动机器、干净VM/账户及目标3050Ti均NOT TESTED。

## 失败记录和Qt

初轮诊断在异步数据集刷新结束前检查了旧界面状态，断言失败；其清理确认映射也不适合未保存草稿。保留`exe-check-1`和受控结束进程记录；修复等待及诊断确认响应，没有删关键断言/跳过测试/伪造文件。新增原生协议拒绝检查时，首次日志捕获未开启FFmpeg日志，断言失败；修正日志级别和跨线程捕获后，最终EXE留下明确的协议拒绝证据。

Qt替换：直接混用6.8.2库与6.8.3绑定出现0xc0000409，stderr明确`Cannot mix incompatible Qt library (6.8.2) with this library (6.8.3)`。原始JSON、stderr、Windows Event1000/1001均保留。随后在独立候选副本用匹配的Qt/PySide/Shiboken组（包括Svg）替换，实际qVersion6.8.2、加载替代DLL，完整流程PASS；最终EXE原样再做匹配组启动/退出，返回0。主候选保持6.8.3，库字节未修改。替换证据在`qt-complete-replacement-results.json`和`qt-final-code-replacement.json`；不把最初失败改写PASS，也不保证任意版本/任意单DLL可混用。

历史`IVAD-QT-001`仍OPEN/PARTIAL：主候选本轮未复现原历史异常，原始根因仍未确定。本轮确有受控混版替换原生终止，不能概括成“本轮没有崩溃”，也不能把已明确的版本冲突解释套用于旧Python312.dll事件。主候选同版本栈再次出现原生异常、关闭/菜单/切换可重复卡死或QObject生命周期警告、取得新完整命令/顺序/dump时重新调查。原Qt日志/Windows历史事件/PARTIAL均保留。
