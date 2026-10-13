# IVAD Platform v1.0 — P1 正式开发指令
## Phase 1: Application Foundation, Unified GUI & Project Infrastructure

### 0. 授权范围

用户已审阅 P0-NVIDIA 验收结果，现**正式批准进入 P1**。

本轮只允许实施 P1。未经用户再次明确批准，不得进入 P2–P6。

你是 IVAD Platform 的主要软件开发工程师。用户不具备系统性的 Python 编程能力，因此软件操作必须面向 GUI，不得要求用户手动修改 Python、JSON、YAML 或数据库才能完成常规业务操作。

本轮优先使用 NVIDIA RTX 5070 Ti 计算环境，同时必须保留 Intel GPU 和未来厂区服务器的兼容架构。

使用 GPT-6.1 Light，采取小范围、可测试、可恢复的增量开发方式。

---

## 1. 首先读取现有项目

请在当前 IVAD 项目根目录内工作。

首先检查并阅读：

- `docs/SRS.md`
- `docs/ARCHITECTURE.md`
- `docs/DECISIONS.md`
- `prompts/CODEX_MASTER_PROMPT.md`
- `prompts/P0_IMPLEMENTATION_PROMPT.md`
- 现有 P0-NVIDIA 验收报告
- `artifacts/p0/requirements-lock.txt`
- `scripts/p0_nvidia/README.md`
- 当前进度文件及其他已有开发规范

以现有文件为主要设计依据。

如文档内容与已经确认的 NVIDIA-first 方案冲突，请记录差异，只做必要的文档修订，不得擅自改变已确认的十项产品需求。

原 Intel B390 验证状态保持 BLOCKED，不得将 NVIDIA 的测试结论套用到 Intel。

保留 P0 的所有真实测试日志、权重文件、环境与历史报告。

## 2. P1 总体目标

开发 IVAD Platform v1.0 的统一 Windows 桌面软件基础框架。

P1 最终交付必须是一款可以真实启动和操作的 GUI 应用，而不是静态界面图或仅有命令行功能的 Python 脚本。

系统内部采用模块化、API-Ready 架构，保证后续 P2–P6 可以持续扩展同一套应用。

P1 不要求正式训练工业 AI 模型，不要求接入摄像头，不要求完成报警业务。

---

## 3. 统一 GUI — PySide6

优先使用 PySide6 / Qt Widgets 构建原生 Windows 桌面软件。

建立统一主窗口，包含：

1. 软件名称、版本信息与当前项目。
2. 左侧固定导航栏。
3. 中央主工作区。
4. 可扩展的右侧属性面板。
5. 底部状态栏。
6. 全局任务状态及错误通知。
7. 开发模式与生产监控模式切换。

### 开发模式

导航结构包含：

- Dashboard / 总览
- Projects / 项目管理
- Media / 视频管理
- Annotation / 标注工作台
- Dataset / 数据集管理
- Training / AI 训练
- Model Registry / 模型仓库
- System Settings / 系统设置

### 生产监控模式

导航结构包含：

- Monitoring / 监控总览
- Cameras / 摄像头管理
- Detection / 视频检测
- Alarm Center / 报警中心
- Event Review / 事件复核
- System Status / 系统状态

本阶段只需实现完整导航和真实的基础设施页面。

尚未开发的 P2–P6 功能应显示：

- 功能名称。
- 计划所属开发阶段。
- 当前状态：Not Implemented。
- 简要功能说明。

不能出现无响应按钮、虚假检测数据、虚假的 GPU Ready 状态或伪装成真实运行结果的示例。

### GUI 设计要求

- 默认使用简体中文界面。
- 保留国际化接口，未来可增加英文。
- 界面适合 1080p 及以上分辨率。
- 支持 Windows 高 DPI 缩放。
- 主窗口可缩放，布局不得严重重叠或裁切。
- 保持统一按钮、表格、弹窗、导航和状态提示风格。
- 耗时操作不得阻塞 Qt 主线程。
- GUI 退出时正确关闭后台任务和数据库连接。

本阶段不要求制作复杂工业监控大屏，也不需要引入额外的前端框架。

---

## 4. 项目管理系统

实现真正可操作的 Project Manager。

通过 GUI 支持：

1. 新建选煤厂项目。
2. 输入项目名称、描述及可选厂区信息。
3. 选择项目存储目录。
4. 打开已有项目。
5. 显示最近打开的项目。
6. 保存项目配置。
7. 关闭当前项目。
8. 检查项目目录与数据库一致性。

项目应使用稳定的 UUID 作为内部 ID，不依赖可变的项目显示名称。

采用相对路径或受控资源引用，避免未来迁移项目时因硬编码绝对路径失效。

项目创建应具备基本原子性：创建失败时不留下被误认为有效的半成品项目。

不要实现自动删除项目或永久清理用户文件的功能。

---

## 5. SQLite 数据库与存储接口

使用 SQLite 建立 P1 基础数据库。

建议使用：

- SQLAlchemy
- Alembic

通过统一 Repository / Service 层访问数据。

P1 至少实现：

- 项目基本信息。
- 应用设置。
- 项目与数据库 Schema 版本。
- 后台任务状态。
- 已知硬件设备记录。
- 应用操作与错误日志索引。

需要为后续以下实体保留架构设计：

- Cameras
- Media
- Frames
- Annotations
- Datasets
- Models
- Model Versions
- Training Runs
- Inference Jobs
- Alarm Events
- Evidence Records

本阶段可仅定义必要接口或轻量数据模型，不要提前实现 P2–P6 的完整业务。

数据库必须支持后续 Schema Migration。

SQLite 作为当前实际后端，PostgreSQL 只需预留兼容性接口，不必在 P1 安装 PostgreSQL。

增加数据库完整性检查及安全关闭机制。

---

## 6. 统一业务服务层与 API-Ready 设计

GUI 不应直接承担数据库 CRUD、GPU 任务执行或文件处理业务逻辑。

请设计统一的 Service Layer，包括：

- ProjectService
- SettingsService
- DeviceService
- JobService
- LoggingService

为后续功能预留：

- MediaService
- AnnotationService
- DatasetService
- ModelService
- InferenceService
- AlarmService

P1 只实现当前需要的服务，其他服务保留明确接口或架构定义即可，不要制造大量没有实际用途的空类。

未来应可以通过 FastAPI 将相同业务能力暴露给厂区局域网客户端。

但本阶段：

- 不启动对外网络服务。
- 不要求部署 Docker。
- 不安装 PostgreSQL 服务。
- 不实现用户登录系统。
- 不实现真实 RTSP 摄像头接入。

---

## 7. GPU Device Manager

建立 GPU 硬件抽象接口。

### 当前 NVIDIA 设备

目标硬件为 RTX 5070 Ti。

优先通过已在 P0 验证的环境获取：

- GPU 名称。
- GPU 数量。
- 驱动和计算后端信息。
- 总显存与可用显存。
- 当前 GPU 使用情况（能力允许时）。
- CUDA 是否可用。
- 已验证推理后端状态。

区分：

- Hardware Detected：检测到物理 GPU。
- Backend Available：计算后端可用。
- Backend Validated：通过对应实际测试。
- Unsupported / Error：不兼容或出错。

不能仅通过 GPU 型号判断计算后端已经通过验证。

### Intel 兼容性

保留 Intel XPU 与 OpenVINO 的后端适配接口。

当前 5070 Ti 电脑若没有受支持的 Intel GPU，不要求测试 Intel GPU 推理与训练。

Intel 后端状态应真实显示为 Not Tested 或 Unsupported，不得伪造通过结果。

### CPU 规则

CPU 可以承担 GUI、数据库、视频 I/O、日志及普通业务处理。

**AI 模型训练和推理严格禁止 CPU-only fallback。**

GPU 不可用时，AI 任务应被拒绝，并产生明确错误信息。

### 环境隔离

不得将 Intel XPU 相关运行库强行安装进 NVIDIA CUDA 环境。

运行环境应通过独立后端进行管理，并允许未来注册多个计算 Worker。

---

## 8. 后台任务管理器

建立 P1 的基础 Job Manager。

目标是为 P2–P6 的抽帧、训练、推理与数据处理提供统一任务机制。

支持：

- 创建任务。
- 任务排队。
- 查询任务状态。
- 进度更新。
- 取消任务。
- 捕获异常。
- 保存任务历史。
- GUI 查看任务详细日志。

统一任务状态建议：

- QUEUED
- RUNNING
- SUCCEEDED
- FAILED
- CANCELLED
- INTERRUPTED

需要特别区分取消和意外中断。

应用重启后，不能把之前正在运行但已丢失 Worker 的任务继续显示为 RUNNING。

P1 使用可控制、可复现的非 AI 测试任务验证队列功能。

不需要为了测试任务管理器而启动实际 YOLO 训练。

支持基本 GPU 任务资源互斥接口，后期再实现复杂多 GPU 调度。

---

## 9. 日志、错误提示与数据保护

实现统一日志系统。

至少包含：

- GUI 操作日志。
- 应用异常日志。
- 任务执行日志。
- GPU 设备检查日志。
- 数据库错误日志。

GUI 应能查看日志摘要并复制诊断信息。

错误信息默认使用中文。

必须保留详细技术日志，便于后续交给 Codex 诊断。

涉及路径、密钥、系统账户或未来摄像头凭据时，需要避免在普通日志中泄露敏感信息。

应能处理：

- 项目路径失效。
- 数据库打开失败。
- GPU 检测失败。
- 后台任务异常。
- 配置文件格式错误。
- 应用意外退出后重新打开。

不得在错误恢复过程中擅自删除用户项目。

---

## 10. 软件工程与目录结构

优先建立清晰、可维护的 Python Package 结构。

建议逻辑模块：

- `ivad_app/`：应用入口与初始化
- `ivad_app/gui/`：统一 GUI
- `ivad_app/core/`：配置、事件、异常及基础接口
- `ivad_app/services/`：业务服务
- `ivad_app/storage/`：数据库与存储适配
- `ivad_app/compute/`：GPU 后端与 Worker 接口
- `ivad_app/jobs/`：后台任务队列
- `ivad_app/models/`：业务数据模型
- `tests/`：自动化测试
- `docs/`：需求、架构与用户文档
- `reports/`：验收报告

实际目录可根据现有工程结构调整，避免重复建立相似目录。

禁止：

- 把全部功能写在单一巨大 Python 文件中。
- 在 GUI 事件回调中直接编写大量业务逻辑。
- 硬编码 CUDA 设备编号。
- 硬编码当前电脑用户名和绝对路径。
- 用模拟 GPU 检测结果代替真实硬件信息。
- 为未来功能提前安装大量无关依赖。

### Git 管理

当前项目尚未建立 Git 仓库。

请检查项目状态，并说明建立 Git 仓库的收益。

允许在确认不会纳入敏感文件和大型二进制文件的前提下初始化本地 Git 仓库。

必须配置 `.gitignore`，排除虚拟环境、缓存、运行日志、模型权重、临时数据和用户项目数据。

不要自动创建远程仓库、推送代码或上传数据。

如果无法安全确定 Git 应纳入的文件范围，请先报告并征求用户批准。

---

## 11. 运行环境保护

P0 已通过的 NVIDIA 环境是当前项目的重要技术基线。

禁止：

- 无理由升级或降级 PyTorch。
- 修改系统 GPU 驱动。
- 修改全局 Python。
- 覆盖 ComfyUI 或其他 YOLO 项目。
- 删除 P0 原始日志。
- 重建已有 P0 CUDA 环境。
- 擅自清空 pip 缓存或模型仓库。

新增 PySide6、SQLAlchemy、Alembic、pytest 等依赖时，应先检查与现有环境的兼容性。

优先使用独立的 P1 GUI 环境或经验证的隔离方案，并保证计算 Worker 能够调用原有 P0 GPU 环境。

记录所有新增依赖、版本和安装来源。

如需对已通过验收的 P0 环境进行重大修改，先征求用户批准。

---

## 12. P1 测试要求

至少完成：

### GUI 测试

- GUI 可启动。
- 主窗口与双工作空间可切换。
- 主要导航可正常打开。
- 高 DPI 下布局基本正确。
- 未实现页面明确显示状态。
- 后台任务运行时 GUI 不冻结。

### 项目测试

- 新建项目。
- 保存项目。
- 关闭并重新打开项目。
- 项目名称包含中文。
- 非法或不可写路径的错误处理。
- 项目配置和数据库一致性。

### 数据库测试

- 初始化数据库。
- 创建与查询项目记录。
- Schema 版本检查。
- 数据库关闭与重新连接。
- 数据库异常时不破坏已有数据。

### 任务系统测试

- 提交任务。
- 状态转换。
- 任务取消。
- 异常捕获。
- 任务历史持久化。
- 应用重启后中断任务的状态恢复。

### GPU 管理器测试

- 真实检测 RTX 5070 Ti。
- 确认 CUDA 后端可用。
- 显示设备信息。
- GPU 不可用时产生正确状态。
- Intel 未测试时不显示为已通过。
- 不存在 CPU-only AI fallback。

### 自动化测试

优先使用 pytest。

凡可以自动化的核心业务逻辑，应提供可重复执行的测试。

GUI 可以使用 Qt 测试工具或可复现的交互检查。

不要把模拟测试通过等同于真实硬件验证通过。

---

## 13. P1 验收门槛

P1 只有在以下条件满足时才可以申报 PASS：

1. 应用能够从项目提供的启动入口正常运行。
2. 开发模式与生产监控模式均可进入。
3. 项目创建、保存和重新打开成功。
4. SQLite 数据库初始化和基本迁移机制正常。
5. 后台任务队列通过测试。
6. GPU 管理器可正确报告当前 NVIDIA 设备及后端状态。
7. GUI 不因普通后台任务而冻结。
8. 核心自动化测试通过。
9. 已知限制和未完成模块明确列出。
10. 原有 P0 测试资产与环境未遭破坏。

若存在影响以上核心要求的阻断问题，P1 状态必须为 BLOCKED 或 FAIL，不得虚报 PASS。

### 特别说明

本阶段不要求完成 Windows 正式安装包。

最终 Windows 安装包属于 P6 交付目标。

P1 应提供可靠的一键启动方式，用户不需要自行输入 Python 启动命令。

---

## 14. 阶段交付内容

完成后生成：

- `reports/P1_IMPLEMENTATION.md`
- `reports/P1_TEST_RESULTS.md`
- `reports/P1_ACCEPTANCE.md`
- `docs/P1_USER_GUIDE.md`

同时更新项目进度、决策文件与相关架构说明。

最终报告使用中文，包含：

1. 完成的实际功能。
2. 新增和修改的主要文件。
3. 使用的 Python 环境与新增依赖。
4. GUI 启动方式。
5. 数据库与任务系统设计。
6. NVIDIA GPU 检测结果。
7. 自动化测试结果。
8. 遗留问题。
9. P1 验收结论。
10. 是否具备进入 P2 的技术条件。

报告中应明确区分：

- IMPLEMENTED
- TESTED
- PASS
- FAILED
- NOT TESTED
- NOT IMPLEMENTED

---

## 15. Codex 执行方式

本轮允许你在 P1 范围内自主编写、运行、测试和修复代码。

执行顺序：

1. 读取现有项目与 P0 验收结果。
2. 检查依赖、环境和现有目录。
3. 确定最小可实施的 P1 文件结构。
4. 建立应用入口、GUI、数据库和基础服务。
5. 实现项目管理、设备管理和任务管理。
6. 运行自动化测试。
7. 修复 P1 范围内的问题。
8. 生成验收报告和使用说明。
9. 停止，等待用户批准。

不要为了节省 Token 而跳过测试。

不要反复输出大量无关的源代码或完整安装日志；只汇报关键变更、测试结果和错误。

如发现架构冲突，先分析并执行不改变已确认需求的最小修复。涉及产品范围或高风险系统操作时，必须向用户请求批准。

**最终要求：完成 P1 后停止。不得自动开始视频标注、YOLO 工业训练、视频推理或报警系统的 P2–P6 开发。**