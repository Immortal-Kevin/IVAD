# P0 决策（2026-10-13）

五份指定文件无实质冲突。README 的先阅读/授权步骤已由本次用户明确执行 P0 的指令满足。
当前目录是设计包，无 Git 仓库、实现代码或 Intel 历史报告。保留原文件，不虚构分支和历史报告。
采用独立 `.venv-nvidia`，Python 3.12.14，训练与推理可合并；不引用原环境的 site-packages。
选择官方 CUDA 12.8 PyTorch 2.9.1 / torchvision 0.24.1；2026-10-13重试已实机安装并完成核心P0测试，全部依赖固定版本与安装来源已记录。
不升级系统驱动或 CUDA Toolkit。无 nvcc 不阻止 wheel 自带运行时方案。
双模型比较完成后初选YOLO26n为NVIDIA默认候选：ORT CUDA、640、FP32、raw输出+NMS，本次ORT p95为4.926ms，YOLO11n为5.440ms；两者GPU/短训/对齐/短时稳定性均通过。该初选来自单次本机流程测量，性能差异受运行噪声影响，不代表工业精度、跨GPU或原生YOLO26端到端模式结论。Intel兼容性保持后续独立验证。

## 契约审计

现有 ModelAdapter/ComputeBackend 规划可分别承载 NVIDIA/Intel，无需在 P0 实施平台代码。
后续建议能力矩阵增加 model/version/task/backend/artifact/precision 维度，并记录已测试状态。
verify 应返回实际执行 provider、算子分配、驱动/运行库版本和证据路径；禁止只以枚举结果通过。
train/export/infer/validate 独立声明；导出期间模型前向同样需 GPU。
YOLO26 与 YOLO11 输出与 NMS 分别适配；原始张量对齐和最终检测对齐必须分别验收。
阶段边界不变：不得自动进入 P1。

## 官方资料（访问日期 2026-10-13）

- https://pytorch.org/blog/pytorch-2-7/ ：Blackwell 与 CUDA 12.8 支持说明。
- https://pytorch.org/get-started/locally/ ：Windows 安装入口；网页静态版本信息与当前包索引存在差异，不据此宣称当前最新版本。
- https://docs.ultralytics.com/models/yolo26/ ：模型与官方权重说明。
- https://docs.ultralytics.com/integrations/onnx/ ：ONNX 导出说明。
- https://onnxruntime.ai/docs/execution-providers/CUDA-ExecutionProvider.html ：CUDA/cuDNN 兼容性、DLL preload；provider 注册不等于节点执行。
  其中use_tf32默认启用；本次ORT/PyTorch均关闭TF32，使用相同FP32进行正确性对照。
商业生产许可尚未解决，AGPL-3.0/Enterprise 需部署前评估。

## P1 已批准的实施决策（2026-10-13）

- 用户粘贴的正式P1指令授权当前阶段，原“初始仅P0”约束不再阻止P1，但P2–P6仍需再次明确批准；十项产品需求不变。
- PySide6 6.8.3 / SQLAlchemy 2.0.40 / Alembic 1.15.2，独立.venv-p1；不安装Torch或Intel运行库到GUI环境，不修改P0。
- ProjectService将新项目暂存完成后同目录原子rename发布；失败只清理自己创建的已知暂存文件/空目录，不删除用户项目。清单只含UUID/格式版本/相对数据库路径；可变配置在SQLite事务保存。
- Repository和ComputeWorker协议、WorkerRegistry保留未来服务器/Intel接口，不创建空的未来业务类。GPU选择使用设备UUID，不硬编码编号。
- JobService仅接受明确标注的非AI诊断任务，串行队列、可取消、可控失败、崩溃恢复为INTERRUPTED，真实GPU作业不在P1实施。
- 本地Git初始化为nvidia-first分支。Git可用于审阅变更和回滚已提交源码；它不替代项目数据备份。采用源码白名单，排除venv、日志、模型、缓存、用户数据及含本机路径的P0历史报告/脚本。不建远程、不推送。
- UI中文，Qt翻译入口保留；显示时间为Asia/Shanghai（UTC+8），存储时间UTC。正式安装包/备份恢复GUI/长期负载/商用许可后续单独验收。

官方工程参考（2026-10-13访问）：Qt线程/高DPI文档 https://doc.qt.io/qtforpython-6/overviews/qtdoc-highdpi.html ，Alembic迁移/共享连接 https://alembic.sqlalchemy.org/en/latest/cookbook.html 。版本安装来源与文件hash保存在artifacts/p1/install.json。

## P2已批准的实施决策（2026-10-13）

- 用户提供P2正式指令，授权当前阶段增量业务；P3–P6继续严格门禁。P0/P1报告原址保留，当前进展以P2报告说明。
- GUI原venv仅追加av15.1.0、Pillow11.2.1、numpy2.2.5、PyYAML6.0.2；原有版本与P0 GPU清单全部一致，pip来源hash见P2_DEPENDENCIES.md。
- 已真实评估QtMultimedia播放；选共享PyAV时间戳解码保证播放/逐帧/抽帧一致。拒绝缺/倒退/重复PTS和未知时长，真实拍摄日期未知保留，不以FPS推算；不安装系统ffmpeg或改PATH。
- 人工真值使用原图像素，ROI独立归一化，稳定类别UUID与修订快照，简单多边形真实分割，不用box伪Mask。Detection转换polygon外接框显式警告并完整保存旁车。
- 冻结只接受已人工审核，来源组划分优先于精确比例。正常空目标可以是负样本，未知/异常空目标不得默认为正常；SHA256重复去重，近重复只警告，避免自动删除关键异常。
- 文件和数据库不是分布式事务。可捕获异常回退.partial，保留中断证据；强杀窗口人工核对，绝不自动删除未知用户资源。不存在工业准确率/大规模稳定性承诺。
- PyAV资料：https://pyav.basswood.io/docs/stable/api/video.html；Qt6.8 QMediaPlayer毫秒position：https://doc.qt.io/qt-6.8/qmediaplayer.html；真实YOLOpolygon规范：https://docs.ultralytics.com/datasets/segment/ 。仅以实际输出与测试宣布兼容。

## P2补充修改决策（2026-10-14）

- 用户仅批准视频管理UI与人工保存片段，本轮不进入P3。
- 左表保留六列，可选导入信息默认折叠；右区可滚动，海蓝白字未选标签、白底黑字激活/悬停。参数以可见中文辅助说明为主，tooltip为补充。
- 裁剪选择重新编码而非关键帧粗略流拷贝；区间[start,end)以实际帧PTS截取、首帧归零，输出帧边界与来源记录透明。只保存视频，不含音频；最短100ms且两帧，拒绝片段再裁片段。使用现有PyAV/FFmpeg/libx264，无新增依赖。
- Schema0004只加媒体kind、parent_id、clip_info，旧媒体默认为ORIGINAL。parent_id为应用层来源关系，服务和一致性检查验证；不为新外键重建SQLite表。
- 失败/取消清理本次UUID暂存与未提交文件，不登记错误READY；已发布完成的片段不因末尾取消误记为未完成。源录像只读，REFERENCE裁剪产物仍COPY落项目内。
- DatasetService只增加必要source_group_id关联，避免父子录像进不同来源划分；原真值模块未重写。旧P2报告先完整存history，原artifacts/p2不覆盖。当前84项全部通过，原环境包版本与历史hash不变。


2026-10-15 Development Directive v3：PACKAGING_FREEZE = TRUE。暂停所有EXE/Portable/Setup构建、签名与分发，旧包保留。P2最终验收PASS后已获准自动进入P3，若P2阻断则停止；P3完成后停止，P4–P6未授权。只维护源码和现有隔离环境，不重制Word/PDF。


## 2026-10-15 v3实施更新

2026-10-15 P3：P2最终101+真实副本回归PASS后按v3条件授权启动。采用固定既有CUDA/GUI环境，无新依赖；GUI不导入torch。候选指标默认.5/.5/.5/.25可显式设置，记录门槛；生产需GUI确认，测试夹具门槛0不当作工业批准。恢复沿用原参数、同数据版本、完整epoch检查点，另建输出目录；正常背景空标签，未知/未审核/剔除/冲突及异常无框拒绝Detection。PACKAGING_FREEZE = TRUE；不进入P4–P6。


## P2 Hotfix during P3（2026-10-15）

2026-10-15 P2 Hotfix during P3：P3已验收完成，本轮只修P2。完成状态与审核分离，不改旧审核；真值变动保留旧审核并对新冻结要求复审。摄像头资料在项目页、关联在视频页，显式/不同片段关联保留。媒体依赖包括活动任务/冻结集/训练/模型，默认保留文件或隐藏，不做级联清理，REFERENCE禁止删外部。Schema0007只加两个JSON列。PACKAGING_FREEZE = TRUE；Hotfix PASS后因原P3已完成而停止，不重启P3/P4–P6。


## 2026-10-15 标注与摄像头数据关系补充

1. 剔除为保留文件/真值/审核/冻结历史的软状态；已标注或冻结引用不阻止安全软剔除。新快照排除剔除图。批量正常仍保护既有真值，不因本轮放宽剔除而放宽正常覆盖。
2. 项目默认工作列表复用 handling.worklist_hidden，可移出/移回；不等同剔除，无永久物理删除。暂不实现多个命名批次。
3. 标注完成由有效持久化内容自动同步，不能提前显示完成；与审核、P3 准入独立。异常无框且无整帧故障类别不算完成。
4. ROI 自动优先视频，其次当前摄像头；来源来自可信媒体关系，不猜文件名。主界面隐藏作用域下拉，提供独立管理入口；几何不匹配不自动应用。
5. Camera/故障/模型配置为多对多元数据接口，复用项目设置和既有模型仓库，默认禁用，不进入 P4 调度。支持独立摄像头样本查询；跨摄像头组合需明确选样。
6. Schema 保持0008，无迁移，真实项目只读；不安装依赖，不重做训练，不打包。历史两张测试夹具截图被旧测试固定输出覆盖的例外详见 P2_HOTFIX_REGRESSION.md，已修正后续输出路径，不将全部历史证据宣称为未变。


## 2026-10-15 P3 Dataset Management UX & Data Integrity Hotfix

- 用户本轮授权优先：移除重复人工审核UI；原审核字段和历史记录不改。旧版本沿用reviewed政策；新GUI明确使用human-auto-v1实验政策。准入必须为持久化人工真值、图片哈希/解码/尺寸有效、合法检测对象和有效启用类别；正常无框负样本可用，未知/冲突/剔除/拒绝/整帧异常无框不可入Detection。
- 新快照附加admission及每样本validation_level，scope=EXPERIMENT_ONLY、independent_review=false，保留annotation_status原值；不新增数据库列，Schema0008不变。训练前校验明确识别政策，旧版本绝不自动升级；模型元数据记录实验准入，生产注册仍需要人工批准。
- 来源视频分组递归追溯根视频；摄像头分组独立；随机图片始终LIMITED并要求双重风险确认。跨集合SHA重复拒绝，近重复警告并标LIMITED。来源组不足如实报告空集合，训练仍需Train/Val非空；LIMITED冻结只用于工程管线验证。
- 四Tab共享项目/筛选/数据集上下文。勾选随筛选变化清空；草稿和候选排除按Dataset UUID隔离但仅会话保留；全局EXCLUDED复用带历史的既有软状态服务。无永久删除，不改旧快照。
- 当前真实项目仅SQLite只读备份及副本检查，不重新关联摄像头或确认工业故障。保持PACKAGING_FREEZE，不改CUDA、不重训，不进入P4–P6。


## 2026-10-15 Dataset Hotfix v2

用户授权仅数据集UX及必要时间服务：六筛选两行行内布局，选择只在当前可见且严格合格候选上执行；Tab切换/同范围刷新保留临时选择，主动筛选清空；会话草稿与临时选择分离，多摄像头仍需明确授权。

8525实际70.040秒，原PTS带52241.877778秒偏移。历史time_us正确，采用统一派生时间服务修复显示，不迁移或覆盖旧PTS/time_us/冻结版本。原视频映射用片段实际首帧时间，不用申请起点猜测；摄像头拍摄日期未知。历史报告错误表述由新调查报告更正而不覆盖旧证据。Schema0008不变，GPU/模型/训练保留，打包冻结。
