"""P1报告生成：从真实pytest/设备/DPI/保护证据读取结论。"""
import json, re, xml.etree.ElementTree as ET
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/p1'
report_dir = ROOT / 'reports'
tree = ET.parse(OUT / 'pytest.xml')
suite = tree.getroot().find('testsuite')
count = int(suite.attrib['tests']); failures = int(suite.attrib['failures']); errors = int(suite.attrib['errors'])
seconds = float(suite.attrib['time'])
device_rows = json.loads((OUT / 'device-live.json').read_text(encoding='utf-8'))
gpu = next(d for d in device_rows if d['id'].startswith('nvidia:') and d['backend_validated'])
preserved = json.loads((OUT / 'p0-preservation.json').read_text(encoding='utf-8'))
dpis = [json.loads((OUT / f'gui-dpi-{label}.json').read_text(encoding='utf-8')) for label in ['100', 'native', '200']]
oneclick = [json.loads(line) for line in (OUT / 'oneclick-smoke/logs/application.jsonl').read_text(encoding='utf-8').splitlines()]
launch_ok = any('正常关闭' in row['message'] for row in oneclick) and any(row['category'] == 'device' for row in oneclick)
assert not failures and not errors and preserved['status'] == 'PASS' and launch_ok
assert all(d['visible'] and d['nav_width'] >= 170 and d['center_width'] >= 600 for d in dpis)
def write(path, text): path.write_text(text, encoding='utf-8')
environment = '''GUI：Python3.12.14（独立.venv-p1），PySide6 6.8.3 / shiboken6 6.8.3、SQLAlchemy2.0.40、Alembic1.15.2、pytest8.3.5、pytest-qt4.4.0。完整传递依赖见artifacts/p1/requirements-lock.txt，官方PyPI文件直链/sha256见install.json。
计算：继续使用原.venv-nvidia，torch2.9.1+cu128 / CUDA12.8 / ORT1.24.4；GUI环境不安装Torch、YOLO或Intel运行库。
'''
write(report_dir / 'P1_IMPLEMENTATION.md', '''# P1 实施报告

日期：2026-10-13（Asia/Shanghai），版本1.0.0-P1。范围仅用户批准的P1；P0全部资产保留，P2–P6未开始。

## IMPLEMENTED

- 真实PySide6/Qt Widgets主窗口，一键入口“启动IVAD.cmd”，开发/生产双工作空间、完整导航、右侧上下文、底部任务状态、中文通知。
- 总览/项目管理/任务中心/设备/设置/日志实际页面；其他页面明确Not Implemented及阶段，没有假生产数据或AI动作。
- 项目创建/打开/最近记录/保存/关闭/一致性检查，中文名称、UUID、配置revision，未保存修改可取消关闭。失败打开保留原当前项目，失败保存保留输入。
- 新项目完整暂存后同目录rename发布；配置只在SQLite事务保存，清单只含不可变UUID、格式版本及相对数据库路径；禁止项目删除。
- SQLAlchemy Repository与Alembic0001→0002实际迁移。项目数据库和应用catalog分离；只读校验、完整性检查、迁移前备份、未知版本拒绝打开、安全关闭。
- Project/Settings/Device/Job/Logging服务与v1 DTO/错误契约；GUI不承担数据库CRUD。未来实体仅文档契约，没有提前创建无用业务类或安装服务。
- 持久化非AI任务队列，进度、取消、可控失败、异常日志、历史，丢失Worker恢复INTERRUPTED；资源ID互斥接口真实实现。
- 独立NVIDIA Worker子进程，实时硬件/CUDA小型张量探针、P0历史验证匹配，后端与硬件状态分离。GPU UUID选择，CPU AI注册和使用被拒绝，IntelNot Tested。
- 脱敏JSONL与数据库日志索引、GUI日志详情与诊断复制；API-Ready内部接口、Qt翻译入口、高DPI/可缩放布局。
- 本地Git nvidia-first分支，源码白名单、忽略数据/模型/venv/日志及P0敏感路径历史。无远程、无推送。

## 主要文件

- ivad_app/__main__.py：启动/单实例/中文启动错误/退出。
- ivad_app/gui/：Qt页面、布局、异步服务桥、翻译入口。
- ivad_app/core/：DTO与API v1错误、组合根。
- ivad_app/services/：项目、设置、设备、日志；ivad_app/jobs/manager.py：JobService与ResourceGate。
- ivad_app/storage/：ORM、数据库、真实Alembic迁移；ivad_app/compute/：独立探针/WorkerRegistry。
- tests/：项目/数据库/任务/设备/Qt交互与实际进程崩溃重启测试。
- scripts/p1/：真实窗口截图、P0保护核对和本报告重现。
- docs/P1_USER_GUIDE.md、P1_SERVICE_CONTRACTS.md；阶段记录与架构更新；原用户授权指令保存prompts/P1_IMPLEMENTATION_PROMPT.md。

## 环境与设计

''' + environment + '''
程序入口在源码目录运行，不需正式安装包。常规业务全部可GUI操作，不要求用户编辑JSON/YAML/数据库。
耗时服务IO在线程池，Qt信号更新GUI；JobService独立串行线程；GPU在独立环境子进程。关闭先请求取消作业，再后台等待IO/Worker并关闭数据库，GUI显示等待而不在主线程join。
数据库当前Schema0002；未来PostgreSQL需要单独实现Repository和迁移，本轮未安装。内部服务契约见docs/P1_SERVICE_CONTRACTS.md。
未来HTTP/登录/摄像头/视频标注/工业训练/推理/报警/PLC均NOT IMPLEMENTED。
''')
rows = '\n'.join(f"| {d['device_pixel_ratio']*100:.0f}% | {d['window'][0]}×{d['window'][1]} | {d['nav_width']} | {d['center_width']} | PASS |" for d in dpis)
write(report_dir / 'P1_TEST_RESULTS.md', f'''# P1 测试结果

日期：2026-10-13（Asia/Shanghai）。真实Windows11桌面与RTX5070 Ti本机测试。
最终pytest：**{count} passed，{failures} failed，{errors} errors**，XML记录耗时{seconds:.2f}s。
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
| P0资产及依赖保护 | PASS | {len(preserved['root_files'])}个P0根文件、{len(preserved['reports'])}份报告hash不变，包快照一致 |
| GUI环境依赖兼容 | PASS | pip check：No broken requirements found；P0未改包 |

## 高DPI与视觉检查

| 实际DPR | 窗口逻辑尺寸 | 导航宽度 | 中央宽度 | 结果 |
|---|---:|---:|---:|---|
{rows}

100%/200%通过仅测试进程QT_SCALE_FACTOR模拟，不改Windows缩放设置；175%为本机原生DPR。
截图gui-devices-native.png、gui-projects-native.png、gui-production-native.png、gui-*-100.png、gui-*-200.png已真实生成；原生与200%截图已视觉检查，未见严重重叠/裁切，较矮窗口导航可滚动。
Qt交互测试为真实Widget按钮/输入/服务操作；文件选择路径由测试夹具提供，没有声称人工点击Windows原生文件选择器已完成。

## 修复和限制

早期导航最小宽度失败已修复并重测；批处理UTF-8/LF解析问题修复为CRLF，实际一键启动PASS。正确性修复没有改动P0环境。
本轮不重新训练/推理YOLO；设备Backend Validated表示当前软硬件与原P0真实证据匹配，并非新AI模型验证。Intel/其他硬件/长期负载/生产业务/真实权限ACL/正式安装包为NOT TESTED或NOT IMPLEMENTED。
''')
write(report_dir / 'P1_ACCEPTANCE.md', f'''# P1 验收报告

日期：2026-10-13（Asia/Shanghai）。阶段：P1。版本：1.0.0-P1。
结论：**PASS**（本机P1应用基础范围），没有进入P2–P6。

| 核心门槛 | 结论 |
|---|---|
| 一键入口真实启动和操作 | PASS，启动IVAD.cmd与真实Qt控件测试 |
| 开发/生产双工作空间与完整导航 | PASS |
| 中文项目创建、保存、重开与一致性 | PASS |
| SQLite基础及Schema迁移 | PASS，0001→0002真实保留数据/备份 |
| 后台队列与进度/取消/失败/历史/恢复 | PASS，含实际测试进程终止重启 |
| 真实NVIDIA硬件、CUDA可用、后端状态 | PASS，{gpu['name']} / 驱动{gpu['details']['driver']} / CUDA{gpu['details']['cuda']}，P0匹配验证 |
| GUI后台运行时不冻结 | PASS，Qt事件循环持续响应 |
| 核心自动化 | PASS，{count}项通过，0失败 |
| 未实现范围如实标识 | PASS，后续页面Not Implemented，无虚假AI/生产数据 |
| P0环境与资产保护 | PASS，47根文件/5报告hash和依赖包快照不变 |

已交付真实GUI、项目/设置/设备/任务/日志基础服务、SQLite/Alembic、Worker注册/资源互斥接口、中文用户说明、自动化测试、原始证据和本地Git源码仓库。详细实现与测试范围见P1_IMPLEMENTATION.md和P1_TEST_RESULTS.md。

''' + environment + '''
普通用户启动：双击项目根目录“启动IVAD.cmd”。项目管理、设置、任务和日志全部GUI操作。没有正式Windows安装包（P6目标）。

遗留问题与NOT IMPLEMENTED/NOT TESTED：
- 视频导入/抽帧/标注/数据集、工业AI训练/模型发布、检测/报警/复核、RTSP、PLC、网络服务、登录、PostgreSQL均未实现，本轮不开发。
- Intel独立历史P0 BLOCKED保留；本机Intel集显仅Hardware Detected，XPU/OpenVINO Not Tested。
- 无跨GPU/跨Windows机器认证、长期负载/多客户端/真实NTFS ACL更改测试。
- 基础数据保护与迁移备份已实现；完整备份恢复GUI与正式安装包后续阶段。P1任务历史显示最近200条，无分页UI；任务不能续接丢失Worker，需重新提交。
- 图形界面主要中文，Qt翻译接口已保留，英文语言包未交付。
- venv依赖基础Python路径，不是可移植安装；系统盘/项目目录必须可写。设备检查有超时，关闭可能等待正在检查的Worker。
- 当前版本已执行SQLite迁移与保护，但没有宣称任何断电/硬中断绝对零丢失。
- 生产许可与工业准确率未解决；P1不是生产模型发布或商业部署批准。

技术上具备进入P2的基础条件。**本轮在P1停止，进入P2仍必须用户明确批准。**
''')
write(ROOT / 'docs/PROGRESS.md', f'''# 进展

2026-10-13：P0-NVIDIA PASS，原始资产/环境/历史BLOCKED记录保留。
用户明确批准P1；已交付真实PySide6 GUI、项目/SQLite/任务/设备/设置/日志，{count}项自动化通过，一键启动及DPI检查完成，P1验收PASS。
本地Git nvidia-first，忽略用户数据/大型资产，无远程推送。
未开始P2–P6；Intel独立历史BLOCKED不变。
''')
write(ROOT / 'docs/CURRENT_TASK.md', '''# 当前任务

P1完成，验收PASS；查看reports/P1_ACCEPTANCE.md、P1_TEST_RESULTS.md、docs/P1_USER_GUIDE.md。
一键启动：根目录启动IVAD.cmd。代码ivad_app/，独立GUI环境.venv-p1；原GPU环境.venv-nvidia保留。
等待用户决定；未经明确批准不得进入P2–P6。Intel恢复同样需授权。
后续业务、正式安装包、完整备份恢复、生产许可/工业精度/长期稳定性尚未完成。
''')
print('P1 PASS;', count, 'tests; reports written')
