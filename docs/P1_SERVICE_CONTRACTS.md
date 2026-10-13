# P1 内部服务契约 v1

GUI调用应用服务，服务调用Repository/Worker；无HTTP监听或FastAPI进程。
公共错误为`AppError(code,message)`，message默认中文，技术trace写脱敏日志。业务DTO为`ProjectInfo`、`DeviceInfo`，不依赖Qt/SQLAlchemy。

| 已实现服务 | 实际操作 |
|---|---|
| ProjectService | create/open/save/check/close，ProjectInfo稳定UUID，save带expected_revision防止陈旧覆盖 |
| SettingsService | preferences/save_preferences/recent_projects，SQLite事务存储 |
| DeviceService | probe/snapshot/require_gpu，真实设备及独立Worker状态 |
| JobService | submit/get/history/cancel/request_shutdown/close，只接受非AI诊断类型 |
| LoggingService | write/exception/recent，结构化JSONL与SQLite索引 |

项目清单格式v1：`format=ivad-project`、UUID、相对数据库路径`project.sqlite`。清单不重复保存可变业务字段；名称/描述/厂区由项目数据库维护。
数据库Alembic当前版本0002；0001→0002真实迁移增加项目配置revision并保留旧数据。打开先进行只读版本/完整性校验；迁移前SQLite backup保存副本；禁止自动降级/清空。
应用目录的catalog.sqlite保存设置、任务、设备缓存和日志索引；每个项目独立project.sqlite保存项目实体。ORM数据访问集中在服务/存储层。后续PostgreSQL需实现Repository事务/完整性/关闭协议及对应迁移，当前未安装或认证。

WorkerRegistry允许注册nvidia_cuda、intel_xpu、intel_openvino工厂，禁止CPU-only注册。当前只注册NvidiaWorker。ComputeWorker协议独立于GUI，P0环境经固定脚本与受控subprocess调用，超时90秒、无自动安装。设备UUID用于选择，设备编号由实际枚举获得。
ResourceGate按资源ID提供互斥与取消等待；P1队列串行，不执行训练/推理。以后真实GPU任务仍需在执行前检查GPU并占用资源；本阶段没有实现AI作业。
任务持久化状态含INTERRUPTED；丢失Worker的RUNNING/QUEUED在启动时恢复为INTERRUPTED，不自动执行未确认的作业。

## 未来接口边界（NOT IMPLEMENTED）

| 服务与实体 | 阶段 / 计划操作 |
|---|---|
| MediaService / Cameras, Media, Frames | P2导入与抽帧，摄像头关联P4，RTSP未来 |
| AnnotationService / Annotations | P2标注、审核、版本与坐标 |
| DatasetService / Datasets | P2不可变快照、分组划分与导出 |
| ModelService / Models, ModelVersions, TrainingRuns | P3 GPU训练/验证、人工批准发布/回滚 |
| InferenceService / InferenceJobs | P4 GPU录像检测 |
| AlarmService / AlarmEvents, EvidenceRecords | P4规则与证据，P5人工反馈 |

不提前建立空业务类、表、摄像头连接或生产网络服务。未来FastAPI可适配v1服务契约，鉴权和服务部署另行验收；当前禁止直接PLC控制。
