# IVAD Platform v1.0 — 系统架构设计

版本 1.1.0 NVIDIA-first；2026-10-12；与 `SRS.md` 决策 D01–D10 一致。

## 1. 设计准则
**One UX, modular internals.** 单一 Windows GUI、开发/生产双工作空间、离线优先、API-Ready、GPU-only AI、插件式模型适配、数据与模型可追溯、训练和生产隔离。不在 P0 生成完整平台；P0 是有退出条件的硬件探针。

## 2. 逻辑拓扑
```mermaid
flowchart TB
  UI[PySide6 GUI\nDev + Production] --> APP[Application Services\nversioned contracts]
  APP --> MEDIA[Media + Annotation + Dataset]
  APP --> MODEL[Model Registry + Release Control]
  APP --> JOB[Persistent Job Scheduler]
  APP --> EVENT[Inference + Rule + Evidence]
  MEDIA --> DB[(SQLite metadata)]
  MODEL --> DB
  JOB --> DB
  EVENT --> DB
  MEDIA --> FS[(Video Frame File Store)]
  MODEL --> FS
  EVENT --> FS
  JOB --> GW[GPU Worker Adapter]
  GW --> NV[NVIDIA CUDA train / ORT CUDA infer\nPrimary P0 target]
  GW --> INTEL[Intel XPU train / OpenVINO GPU infer\nFuture independent validation]
  APP -. future authenticated REST .-> LAN[FastAPI + LAN Windows Client]
  LAN -. future .-> PSQL[(PostgreSQL)]
  LAN -. future .-> RTSP[RTSP Camera Sources]
```

## 3. 推荐代码结构（规划结构，非现有文件）
```text
ivad/
  app/                 # 启动、依赖注入、配置
  gui/                 # PySide6 GUI: development / production workspaces
  domain/              # 实体、事件、规则、状态机（不引用 Qt/数据库）
  services/            # 项目、视频、标注、训练、模型发布、报警
  contracts/           # 版本化 DTO、接口与错误码
  repositories/        # SQLite 实现；PostgreSQL 接口预留
  storage/             # 文件索引、哈希、相对路径、备份恢复
  video/               # FileVideoSource、未来 RTSPVideoSource
  annotations/         # bounding box, polygon, mask, ROI, frame/clip
  datasets/            # exporters、splitting、manifest
  ml/
    adapters/           # Ultralytics YOLO / non-YOLO abstract base
    runtime/            # torch_cuda, ort_cuda, future openvino, torch_xpu
    conversion/         # weights -> deployment artifacts
  scheduler/           # job persistence、GPU resource reservation、cancel
  detection/           # inference runner、tracking/time window、rules
  events/              # evidence writer、review queue
  api/                 # Future REST adapter (not exposed in v1)
  tests/
```

## 4. 关键设计契约
- `VideoSource.open/read/seek/close` → `VideoFrame(image, pts_us, frame_index, source_id, metadata)`；时间戳从可靠视频 PTS 获得；文件/流统一。
- `Annotation` → `(annotation_id, media_id, frame_pts_us, geometry_type, geometry, label_id, origin, reviewer_status, revision)`；geometry 用原始图像归一化/像素坐标并标识坐标系。
- `DatasetSnapshot` → 不可变 manifest；记录源视频/摄像头/采样与拆分策略、标签 schema 版本、每件文件哈希。
- `ModelAdapter` → `capabilities`, `load`, `predict`, `validate`, `train`, `export`（具体方法依能力可标为 unsupported）；不根据文件扩展名推测完整兼容性。
- `ComputeBackend` → `probe`, `verify`, `run`, `report_usage`; `gpu_required=true`，禁止 AI 运算 CPU fallback。
- `Job` → `QUEUED → RUNNING → SUCCEEDED/FAILED/CANCELLED`，重启后 RUNNING 转为 `INTERRUPTED`，提供可行的 Resume/Retry；幂等 job_id。
- `ModelRelease` → `EXPERIMENTAL → CANDIDATE → PRODUCTION → RETIRED`；生产发布需人审，保留 old artifact/rollback pointer。
- `Detection` 与 `AlarmEvent` 分开：模型产生检测，规则产生告警；存 `model_id`,`rule_revision`,`source_pts`,`wall_clock_if_valid`, `evidence_refs`。
- `EventEvidence` → 原始图片、叠框图片、前后片段（可失败并标缺失）、检测 JSON、人工复核历史。

## 5. 数据库概念实体
`Project, Site, Equipment, Camera, MediaAsset, FrameAsset, FaultLabel, Annotation, AnnotationRevision, DatasetVersion, ModelArtifact, ModelRelease, ComputeDevice, Job, JobLog, DetectionResult, AlarmRule, AlarmEvent, EvidenceAsset, ReviewAction, BackupRecord`。

规则：原始数据与审核结果可追溯；外部引用不随意复制/删除；模型/规则发布是事务性切换；数据库及文件之间使用 staging + hash + commit/cleanup 保持可恢复一致性。

## 6. 推理和时序规则
1. 视频来源输出帧及 PTS；根据模型启用检测/分割/传统 ROI 或运动分析。
2. GPU 后端执行模型推理；CPU 可解码、归一化、处理后处理与时间窗判定（不得进行 CPU-only 神经网络计算）。
3. 规则层按摄像头与故障类别融合 confidence、ROI、连续帧、持续时间、冷却；追踪同一事件避免逐帧重复报警。
4. 事件生成时持久化记录和证据任务；复核结果进入候选训练数据，不热更新生产模型。
5. 离线流使用视频事件时间；远期 RTSP 同时记录采集/接收/服务器时间及同步质量。

## 7. GPU 后端与隔离
- `worker_nvidia`（首要交付）：PyTorch CUDA train + ONNX Runtime CUDA infer；可选 TensorRT 加速须独立验证。
- `worker_intel`（后续验收）：OpenVINO GPU infer + PyTorch XPU train（两者独立验证）；保留旧 B390 P0 BLOCKED 记录。
- GUI 通过 IPC/受控子进程调用；不会因为工作进程出错而退出。
- 禁止自动降级到 CPU-only AI；如所选 GPU 后端不支持某架构，给出 BLOCKED/UNSUPPORTED 并建议经批准的替代设备；**不得擅自改为 CPU，也不得静默跨后端**。
- 同一 GPU 的高负载训练与生产推理默认串行；优先保障已部署模型任务；多 GPU 调度预留。

## 8. API-Ready 的边界
本地 v1 UI 直接调用 Application Service 接口；避免为了 API 先启动常驻 localhost HTTP 服务。可在 contracts 中定义版本号、DTO、统一错误结构和分页/任务异步语义。以后加 FastAPI 适配器、认证/RBAC、请求审计、LAN TLS 视厂区实际网络政策确定；服务器版 API **不应默认无鉴权**。

## 9. 包装与部署
本地模式：Windows 11 + 主程序 + GPU worker 独立环境 + SQLite + 文件仓库。安装包与推理运行时版本要锁定，签名/AV 误报/首次启动检查在 P6 测试。未来服务器模式：服务器保有计算/媒体/数据库，Windows 客户端连接 API；本地服务不直接依赖具体数据库实现。

## 10. 已知风险与控制
- NVIDIA CUDA 与具体 YOLO26n/YOLO11n 训练、ONNX Runtime CUDA 推理：P0-NVIDIA 必须实测，模型选型仅针对已测后端有效。
- Intel XPU/OpenVINO 与具体模型：P0-Intel 后续独立实测，保留 BLOCKED 历史记录。
- Intel shared memory 与 UMA：不能把系统 RAM 全计为 GPU VRAM；NVIDIA 以驱动实际报告 VRAM 为准。
- VFR 与多路摄像头时间：使用正确时间基及独立时钟字段。
- 同源视频相邻帧泄漏：按采集组划分 train/test。
- 模型序列化与恶意权重：仅可信权重，校验 hash，控制执行来源。
- Ultralytics AGPL-3.0/Enterprise：使用和商业闭源发布前需许可证评估；不可单凭部署模式判断豁免。
- PLC 控制：v1 不实现；远期需要独立安全工程审批。

## 11. 架构决策记录（ADR 摘要）
ADR-001 One GUI two workspaces; ADR-002 API-Ready without mandatory network; ADR-003 SQLite local, PG later; ADR-004 model and compute adapters; ADR-005 production release approval; ADR-006 GPU-only AI; ADR-007 full evidence and feedback; ADR-008 seven gated stages; ADR-009 copy/ref media hybrid; ADR-010 strict runtime verification.

## 12. P1 实施映射（2026-10-13）

经用户明确授权，实际包为`ivad_app/`：gui、core、services、storage、compute、jobs。GUI为PySide6/Qt Widgets，.venv-p1独立于P0 .venv-nvidia。
应用级catalog.sqlite与每项目project.sqlite分离；SQLAlchemy事务访问，Alembic0001/0002迁移，迁移前备份，稳定UUID与相对路径清单。
任务后台线程串行、服务IO线程池、Qt信号回GUI；设备检查固定脚本通过独立P0解释器执行。GPU枚举/可用/历史实测分别报告，Worker注册与资源互斥留真实接口。
具体v1服务契约与未来实体边界见`P1_SERVICE_CONTRACTS.md`。以上只实现P1基础，没有视频、标注、AI业务、报警、网络服务或P2–P6模块。

## 13. P2实施映射（2026-10-13，用户已批准）

P2在同一MainWindow替换media/annotation/dataset三个P1占位页，依旧由ApplicationServices持有服务、AsyncRunner承担IO、JobService串行后台任务记录进度/结果/取消/中断恢复。媒体/帧/标签/人工修订/ROI/片段/快照/导出登记统一保存在项目SQLite，Schema0003仅添加；模型见DATABASE_SCHEMA.md。

FileVideoSource基于PyAV15.1.0 wheel的FFmpeg库真实解码。QtMultimedia实际评估通过，但应用播放与抽帧共用PyAV实际显示帧PTS；视频播放使用独立解码线程和generation令牌防止切换后的旧画面，seek从关键帧解码到实际目标。普通视频CPU解码不属于AI降级；P0 GPU-only规范不变。

AnnotationCanvas场景坐标等于解码图片像素，显示变换不改真值；ROI独立按显示坐标归一化关联视频/camera，标注和ROI修订CAS事务保存。350ms自动保存和项目/退出flush避免静默遗失。数据集只冻结已人工审核图片，保存图片/类别/真值/ROI/片段快照；精确hash去重、来源分组、随机风险确认。

Export adapters输出YOLO detect/真实polygon segment/COCO/native；无法表达的语义保留native旁车，segment遇box整次拒绝。暂存文件校验后唯一目录rename，数据库异常可回退.partial；强杀跨资源窗口不作原子分布式保证，完整恢复后续阶段验收。P3–P6依旧未实施，未经批准不得进入。

## 14. P2补充修改（2026-10-14）

MediaPage保持同一页，改为左右QSplitter：左侧独立录像表，右侧QScrollArea共享起止范围及播放/抽帧/片段标签/保存视频片段四标签。新增p2_clip复用JobService，PyAV/FFmpeg实际PTS解码并H.264重编码，旋转落实到像素，完整解码/hash校验后登记COPY CLIP；源视频只读。媒体kind/parent_id/clip_info由0004添加，不重建旧表。原/片段共享source_group_id，camera优先，防数据集父子来源泄漏。没有P3–P6变更。


## 2026-10-15 v3实施更新

P3实施：原JobService注册p3_train/p3_validate，原ApplicationServices组合TrainingService/ModelService，同一MainWindow替换训练/仓库占位页。GUI .venv-p1经JSON请求/进度/取消文件调用.venv-nvidia独立进程，无网络服务器。CUDA UUID加Windows进程字节锁，AI前向守卫和ORT节点profile防CPU fallback。DatasetService快照复用并复制训练工作区；ModelAdapter协议区分能力，Registry CAS事务切换生产指针，不改权重。0006仅新增training_runs/model_versions，迁移前备份。P4–P6仍规划，打包冻结。
