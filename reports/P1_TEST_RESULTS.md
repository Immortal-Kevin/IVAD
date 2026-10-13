# P1 测试结果

日期：2026-10-13（Asia/Shanghai）。真实Windows11桌面与RTX5070 Ti本机测试。
最终pytest：**37 passed，0 failed，0 errors**，XML记录耗时14.71s。
命令：`.venv-p1/Scripts/python.exe -m pytest -q --junitxml=artifacts/p1/pytest.xml`。
原始日志/逐项结果：artifacts/p1/pytest.log、pytest.xml。

| 检查 | TESTED / 结果 | 方法与证据 |
|---|---|---|
| 真实GUI入口与退出 | PASS | python模块启动+原生Qt窗口；启动IVAD.cmd实际pythonw启动、设备检查与安全退出，oneclick-smoke/logs/application.jsonl |
| 双工作空间/所有导航/未实现标识 | PASS | pytest-qt真实控件导航，Not Implemented断言 |
| 中文项目新建/保存/关闭重开 | PASS | GUI按钮、真实SQLite和UUID/字段校验 |
| 最近项目、迁移目录、相对路径 | PASS | 实际复制完整测试项目并重开，UUID不变 |
| 非法路径/损坏JSON/目录UUID不符/路径穿越 | PASS | 真实测试文件，失败后原当前项目和文件保持 |
| 不可写路径错误处理 | PASS（受控注入） | 注入PermissionError；未更改系统NTFS ACL。实际不存在目录/非目录文件也测试 |
| SQLite初始化/完整性/Schema/关闭重连 | PASS | 真SQLite文件和Alembic版本 |
| 0001→0002迁移/保留数据/备份 | PASS | 实际旧版本数据库迁移后中文数据与revision存在 |
| 损坏或未知版本不重建/不覆盖 | PASS | 真实文件字节前后对照 |
| QUEUED/RUNNING/SUCCEEDED/FAILED/CANCELLED | PASS | 实际非AI后台队列与可控异常，后续任务继续 |
| 历史持久化/INTERRUPTED恢复 | PASS | 已完成历史保留；额外有意终止专属测试进程后重新打开真实数据库 |
| 资源互斥接口 | PASS | 并发线程争用同资源，未重叠；不是实际多GPU调度 |
| GUI响应与任务取消/日志复制 | PASS | Qt事件循环定时器继续触发，切换页面、点击取消/日志/复制按钮 |
| GPU检查后台执行 | PASS | 受控延迟检查时GUI定时器持续响应；真实GPU独立测试另列 |
| 未保存修改保护/GUI设置保存 | PASS | Qt弹窗返回取消/放弃，保存设置真实写入SQLite |
| 真实NVIDIA/CUDA可用/历史验证匹配 | PASS | P0解释器真实CUDA张量计算、实时nvidia-smi、匹配历史实际YOLO/ORT证据，device-live.json |
| Worker缺失/GPU不可用路径 | PASS | 指向缺失解释器后正确Error，物理GPU仍独立枚举；未物理拔除显卡 |
| 手动设备失效/CPU AI拒绝/Intel未验证 | PASS | 失效UUID拒绝，不静默切GPU或CPU；Intel显示Not Tested |
| P0资产及依赖保护 | PASS | 47个P0根文件、5份报告hash不变，包快照一致 |
| GUI环境依赖兼容 | PASS | pip check：No broken requirements found；P0未改包 |

## 高DPI与视觉检查

| 实际DPR | 窗口逻辑尺寸 | 导航宽度 | 中央宽度 | 结果 |
|---|---:|---:|---:|---|
| 100% | 1440×900 | 202 | 978 | PASS |
| 175% | 1433×710 | 201 | 973 | PASS |
| 200% | 1250×660 | 172 | 845 | PASS |

100%/200%通过仅测试进程QT_SCALE_FACTOR模拟，不改Windows缩放设置；175%为本机原生DPR。
截图gui-devices-native.png、gui-projects-native.png、gui-production-native.png、gui-*-100.png、gui-*-200.png已真实生成；原生与200%截图已视觉检查，未见严重重叠/裁切，较矮窗口导航可滚动。
Qt交互测试为真实Widget按钮/输入/服务操作；文件选择路径由测试夹具提供，没有声称人工点击Windows原生文件选择器已完成。

## 修复和限制

早期导航最小宽度失败已修复并重测；批处理UTF-8/LF解析问题修复为CRLF，实际一键启动PASS。正确性修复没有改动P0环境。
本轮不重新训练/推理YOLO；设备Backend Validated表示当前软硬件与原P0真实证据匹配，并非新AI模型验证。Intel/其他硬件/长期负载/生产业务/真实权限ACL/正式安装包为NOT TESTED或NOT IMPLEMENTED。
