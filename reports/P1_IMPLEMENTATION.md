# P1 实施报告

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

GUI：Python3.12.14（独立.venv-p1），PySide6 6.8.3 / shiboken6 6.8.3、SQLAlchemy2.0.40、Alembic1.15.2、pytest8.3.5、pytest-qt4.4.0。完整传递依赖见artifacts/p1/requirements-lock.txt，官方PyPI文件直链/sha256见install.json。
计算：继续使用原.venv-nvidia，torch2.9.1+cu128 / CUDA12.8 / ORT1.24.4；GUI环境不安装Torch、YOLO或Intel运行库。

程序入口在源码目录运行，不需正式安装包。常规业务全部可GUI操作，不要求用户编辑JSON/YAML/数据库。
耗时服务IO在线程池，Qt信号更新GUI；JobService独立串行线程；GPU在独立环境子进程。关闭先请求取消作业，再后台等待IO/Worker并关闭数据库，GUI显示等待而不在主线程join。
数据库当前Schema0002；未来PostgreSQL需要单独实现Repository和迁移，本轮未安装。内部服务契约见docs/P1_SERVICE_CONTRACTS.md。
未来HTTP/登录/摄像头/视频标注/工业训练/推理/报警/PLC均NOT IMPLEMENTED。
