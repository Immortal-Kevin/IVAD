# P3.7-A / P3.7-B 实施计划（待批准）

日期：2026-10-16。输入：用户接受 P3.6 PARTIAL 工程可行性结论。

**本文件只做规划，不授权或启动正式迁移。PACKAGING_FREEZE=TRUE；不进入P4。** 不重复P3.6完整GPU训练，不删除历史Ultralytics源码、环境、模型、ONNX、缓存或许可证声明。

## 1. 基线与批准顺序

当前分支 `feature/p36-rfdetr-evaluation`，P3.6原始HEAD `48f912734ecafa972b90c41d11b816100c962b73`。用户确认本地Git身份后，25个P3.6文件已提交为 `b157e3e6be0cad9375917b88ab23927d060347d1`。仅设置本仓库local配置，global未改、原nvidia-first分支未改、未推送。本规划文档不属于该25文件提交，保留在工作区待审，不代表正式迁移已获授权。

建议分两次明确授权：批准A后接入训练/数据/Registry；A验收通过并得到B授权后接入离线检测。A通过不自动授权B，B通过不授权P4、生产发布或打包。实施分支名称在批准时确定，不在本轮创建实施分支。

已有Nano训练/推理/ONNX证据继续有效；现有权重只读保留。后续采用已验收权重进行加载、评估与GUI集成；若确需验证正式训练按钮到Worker的端到端路径，仅安排独立夹具上的极短训练/取消测试，列入后续批准范围，不再重跑现有12 epoch实验或历史YOLO训练。

## 2. 现状中必须处理的差异

| 当前实现 | 正式接入需要的处理 |
|---|---|
| model_adapters只注册YOLO11n/26n，统一参数以SGD、lr0、imgsz640为中心 | 使用后端能力描述及独立参数schema；RF的AdamW、encoder LR、AMP类型、分辨率约束等不得机械映射为YOLO参数 |
| TrainingService默认.venv-nvidia与artifacts/p0/<model>.pt，恢复路径run/weights/resume.pt | 按backend选择解释器/权重/恢复策略；RF不回落到旧环境或YOLO权重 |
| 正式exporters.py的COCO类别ID为class_id+1，P3.6实验副本为class_id | 显式维护UUID、内部ID、COCO ID、模型logit ID四者映射；不改历史冻结manifest |
| ModelService.register当前只接受.pt/.onnx | 支持经验证的RF .pth/训练.ckpt语义；不通过改扩展名绕过校验；GUI进程不反序列化权重 |
| 当前JobService有进程内ResourceGate；旧Worker还有跨进程GPU锁 | 复用并统一真实GPU UUID互斥，不能只改GUI锁或只添加第二套锁 |
| P3.5缓存身份含Ultralytics处理版本、NMS、imgsz640与旧环境哈希 | 新增RF缓存schema/后端身份；旧YOLO缓存不可命中新RF请求 |
| P3.6训练内EMA评估与独立重载评估口径不同 | 先统一并逐张归因，禁止只选较高指标；不能归因则阻断相关验收 |

## 3. 文件与依赖替换矩阵

下列均为**计划修改**，本轮不实施；新增路径为建议路径，批准实施时按现有模块结构最终确定。

| 文件/组件 | A/B | 计划与对应测试 |
|---|---|---|
| ivad_app/compute/model_adapters.py | A | 通用能力描述与RF Nano注册；不复用YOLO raw/NMS契约。测试能力矩阵、无效后端、旧记录只读解析 |
| ivad_app/compute/train_worker.py | A | 旧Ultralytics实现保留为历史路径；RF走独立新Worker，禁止继承DetectionTrainer或搬运其训练逻辑。测试导入隔离、CUDA证据与错误退出 |
| 新compute/backends/与rfdetr_train_worker.py | A | 从独立原型提炼可信、可校验的训练/评估入口；补足请求校验、数组长度、取消、日志、版本化结果。测试请求损坏、零类别、未知字段、设备不符 |
| ivad_app/services/training_service.py | A | 后端路由、RF参数预检、独立解释器、检查点语义、成功登记事务。测试不回落、失败不登记、取消竞态、重复点击 |
| ivad_app/gui/training_page.py、training_controls.py | A | 复用现有训练页面，按能力显示简易/高级参数、AMP实际支持、历史运行与日志；不建第二套GUI。真实GUI测试重载配置、不可用项禁用、高DPI |
| ivad_app/datasets/exporters.py、services/dataset_service.py、dataset_lifecycle.py | A | 复用冻结数据读取/准入，新增RF COCO目录与显式类别映射；来源独立旁车、哈希与负样本保留。测试200/402计数、0基/1基ID、多类、无框异常拒绝、polygon需复核 |
| ivad_app/gui/dataset_page.py、dataset_lifecycle.py | A | 数据任务/后端兼容提示与导出反馈；保留筛选/草稿/冻结流程。测试勾选与草稿分离、划分不变、LIMITED警告 |
| ivad_app/services/model_service.py、storage/models.py | A | 扩展backend/architecture/format元数据和校验；优先使用现有details JSON，不预设必须migration。测试可信导入、.pth/.ckpt区分、哈希、类别和数据集引用、不可变模型版本 |
| ivad_app/core/application.py、services/settings_service.py、device_service.py | A/B | 中立服务装配、按后端设置解释器、实际GPU预检；RF路径禁止默认导入旧实现。测试GUI启动/历史列表/诊断不加载Ultralytics |
| ivad_app/jobs/manager.py与现有Worker GPU锁 | A/B | 统一任务状态/取消/跨进程GPU租约，不实现P4多模型调度。测试队列取消、双进程、崩溃释放、关窗回收 |
| ivad_app/compute/offline_worker.py | B | 历史YOLO Worker保留，RF使用独立rfdetr_inference_worker.py；禁止YOLO.predict/NMS。测试真实预测、空结果、错误类别和CPU回落拒绝 |
| ivad_app/services/offline_demo_service.py | B | 后端路由、RF推理参数/坐标映射、后台预处理和取消；复用视频解码/时间服务。测试帧数量、非零PTS、片段映射、异常输入 |
| ivad_app/services/offline_cache.py | B | RF独立schema/签名/准入/完成标记；保留旧缓存只读。测试交叉后端拒绝、参数/权重变更、损坏/部分缓存、历史人工打开不执行旧引擎 |
| ivad_app/gui/offline_demo_page.py、offline_demo_layout.py、offline_demo_interaction.py | B | 保留三Tab，增加RF模型/后端实际状态；预处理回放、列表跳转及导出保持一致。真实GUI测试播放/暂停/定位/逐帧/取消及高DPI |
| ivad_app/video/reader.py、timestamps.py | B | 优先不改算法中立实现；仅补契约适配。测试相对时间、raw_pts/time_base、可变帧率与片段来源 |
| tests/test_p3_training.py、test_workflow_training_hotfix.py、test_dataset_*.py | A | 保留旧用例，增加后端参数化与RF专属测试；旧YOLO GPU测试不作为RF验收证据 |
| tests/test_offline_demo_service.py、test_offline_cache_identity.py | B | 增加跨后端缓存/输出/时间/取消/导出回归，不重训历史模型 |
| experiments/p36_rfdetr及artifacts/p36-rfdetr-20261016 | A/B | 作为只读原型/证据，不直接复制为已验证正式实现；历史文件保留 |

RF运行闭包需排除ultralytics、ultralytics-thop、ultralytics-platform、rfdetr_plus，以及旧YOLO PT/ONNX/NMS与其派生训练实现。原.venv-nvidia和相关依赖不卸载，只是不成为RF正式路径的依赖。YOLO文本数据格式本身与Ultralytics软件实现分开判断；RF转换直接取IVAD人工真值，不经过旧YOLO导出标签或伪标签。

## 4. P3.7-A：训练GUI、数据与Registry

| 顺序 | 工作包 | 产物与通过条件 | 人日估算 |
|---|---|---|---:|
| A0 | 封存P3.6与测试项目副本；确认中立接口/来源审查范围 | 输入清单、保护哈希、变更清单；真实项目只读，旧资产可追溯 | 0.5 |
| A1 | 后端能力、参数、运行环境及消息契约 | RF明确参数schema和解释器；不支持参数报错，不静默忽略/映射 | 1–1.5 |
| A2 | COCO转换、类别/来源映射、准入校验 | 保留160/40/0与16负样本，不把异常无框变检测真值；200/402与SHA一致 | 0.5–1 |
| A3 | 统一评估与检查点重载 | 同一个评估契约/预测后处理、逐张差异报告、统一GUI指标定义 | 1–1.5 |
| A4 | Worker/队列/取消/日志与Registry事务 | GPU真实执行；失败/取消不登记成功；.pth、可恢复.ckpt与ONNX分开保存 | 1–1.5 |
| A5 | 原训练/数据集GUI接入与针对性回归 | 真实GUI可选RF、预检、任务/历史加载、可信模型登记；A验收报告 | 1–1.5 |
| A合计 | | 含必要小规模集成验证，不含重复P3.6整训 | **5–7.5** |

拟新增交付：reports/P37_A_ACCEPTANCE.md、P37_EVALUATION_PARITY.md、P37_ZERO_ULTRALYTICS_DEPENDENCY.md（A范围）、必要Markdown操作说明和后端契约文档。未完成项使用PASS/PARTIAL/BLOCKED明确标记。

Registry保留既有模型UUID/权重/状态/验证历史。新RF登记创建独立UUID，绑定backend=rfdetr、architecture=nano、任务detect、框架/环境/许可版本、class_map及其hash、DatasetVersion/hash、weights/hash、训练参数、种子、评估协议/hash、训练来源与LIMITED状态。P3.6工件如需正式登记，按可信导入创建新记录并引用原始来源，不冒充GUI新训练；原实验文件不搬走/覆盖。

历史缺少backend字段的记录采用只读、可追溯的legacy分类，不批量重写。若发现JSON扩展不足或必须迁移，先提出增量migration及副本升级/回退测试方案，不重建数据库。原审核准入不放宽；LIMITED不自动升级候选/生产；任何正式生产状态变更不在A/B授权范围。

## 5. 训练与重载评估统一门槛

固定同一权重SHA（明确EMA/regular）、数据集及GT、类别ID映射、输入尺寸/resize方式、插值/归一化/RGB、精度、阈值、top-k/maxDets、背景与退化框处理、边界裁剪、COCO评估器版本、IoU范围与匹配规则。训练内指标和重载指标都记录protocol_id/hash；F1 sweep P/R不能与固定confidence .25的P/R混为一列。maxDets100/500结果作为不同协议保存。

先在不训练的情况下，用P3.6最佳权重与40张验证图比较训练评估入口和正式重载入口，保存每帧原始输出/后处理输出与差异。用批量/单图与BF16/FP32隔离变量，定位已知0.479388与0.465326差异；不能仅用宽容差掩盖未解释差异。

拟定通过门槛：同协议FP32同输入的框/分数逐项差异可解释，数值容差预先记录；确定性样本类别/框数一致，AP绝对差≤1e-4。仅当预先证明阈值边缘或浮点差异时单独列例外，经审阅才能放宽。无法归因或超过门槛则评估子项BLOCKED，不能把原训练高分写成重载成绩。工业泛化评估继续LIMITED，不将此技术一致性门槛当准确率门槛。

## 6. P3.7-B：离线视频、缓存与导出

前置：A的RF模型验证/类别/评估契约稳定并验收，用户另行批准B。

| 顺序 | 工作包 | 产物与通过条件 | 人日估算 |
|---|---|---|---:|
| B1 | RF推理Worker与模型选择路由 | 原GUI选择有效RF实验模型；CUDA真实预测，背景/零面积正确处理，禁止YOLO默认回退 | 1–1.5 |
| B2 | 现有解码/时间/结果与三Tab接入 | 当前媒体相对时间、原视频映射和原尺寸坐标一致；明确预处理回放 | 0.75–1 |
| B3 | 缓存schema、完整身份和取消恢复 | RF与YOLO严格隔离，部分/损坏缓存不可假成功，安全读取历史成品 | 0.75–1.25 |
| B4 | 视频/截图/CSV/JSON导出和追溯 | 实际预测与模型/来源/参数一致，导出取消/失败不覆盖旧文件 | 0.5–1 |
| B5 | 真实GUI/针对性回归/性能与保护检查 | 完整70.04秒样例回放与各操作验证，保留限制；B验收报告 | 1–1.5 |
| B合计 | | 不承诺25/30FPS，不重训模型，不加入RTSP/报警 | **4–6.25** |

拟新增交付：reports/P37_B_ACCEPTANCE.md、P37_CACHE_ISOLATION_TESTS.md、P37_GPU_SCHEDULING_CANCELLATION.md、零依赖报告B补充、必要离线演示Markdown指南。

### 缓存与导出契约

新RF缓存身份必须包含：schema、backend/architecture、模型UUID与weights SHA、class_map hash、DatasetVersion/来源、媒体UUID及文件SHA、Camera/片段父源、起止范围、精度、输入预处理/resize、阈值/后处理、解码器/时间协议、实现/环境版本hash。RF不得套用旧p35-pil-rgb-ultralytics-v1身份，不因同名视频/模型名称相同而命中。

结果字段：media/camera/model/dataset标识、Frame UUID（未持久化视频帧可null）、序号/raw_pts/time_base、当前媒体与源视频相对时间、class UUID/ID/name、confidence、原尺寸xyxy/raw_xyxy、过滤计数和inference parameters。RF输出不套用YOLO raw/NMS。结果应检查数组数量一致、有限值、合法类别、坐标/时间范围，不能依赖zip静默丢数据。

完成缓存先写独立暂存目录，校验manifest、结果/帧文件/哈希、最后原子发布完成标记；取消/失败保留日志并标记不可作为完成缓存，不误用部分帧为完整录像。旧YOLO缓存只读显式历史回放，不触发其Worker，不得冒充RF结果；若现有读取器本身依赖旧模型验证，则将安全的成品读取契约解耦，否则在RF路径禁用并说明。

导出视频/截图/CSV/JSON都取真实RF推理结果并保留完整模型/来源/参数追溯；不读取人工框伪装预测。流帧与已有抽帧Frame UUID区别明确，不能制造数据库Frame记录。覆盖同名文件必须显式处理，原录像/历史导出不受影响。

## 7. 中立API契约（A定义，B复用）

| 契约 | 关键内容 | 拒绝/测试 |
|---|---|---|
| BackendCapabilities | backend、architecture、任务、操作、参数schema、输出协议、许可与环境标识 | 不支持能力禁用；不能声称可训练/恢复而无实现 |
| DatasetSnapshot | version UUID/hash、task、admission、LIMITED、class_map、split、images/GT/provenance | 冻结校验失败、异常无框、未知/剔除/冲突、未准入样本拒绝；多边形转换需另行复核 |
| TrainRequest / EvaluateRequest | schema、job/run UUID、backend、dataset、weights/hash、operation、device UUID、参数、seed、protocol | 架构/类别/恢复版本不符、任意路径/非法参数/CPU AI拒绝 |
| JobEvent / JobResult | 有序事件、phase/progress、heartbeat、state、实际GPU证据、artifacts/hash、错误/日志 | 状态机、重复/乱序事件、缺失result、异常退出、保存失败不假成功 |
| ModelArtifact | format、architecture、class map、weights/hash、run/dataset引用、protocol、实验状态 | .pth权重与.ckpt恢复状态不可混用；GUI不unpickle，不静默覆盖旧模型 |
| InferenceRequest / DetectionFrame | 模型身份、源时间/帧身份、尺寸、参数、实际boxes/classes/scores | 空结果合法、数量不匹配/未知类/非有限值拒绝；背景/退化框记录过滤 |
| CacheManifest / ExportManifest | 完整请求签名、实现/环境、完成状态、文件清单/hash、来源 | 旧schema跨后端命中拒绝，损坏/取消/文件缺失拒绝完成态 |

契约需显式版本号；向后兼容通过只读解析与适配完成，不批量改历史工件。旧API保留可追溯历史语义，新RF路径禁止隐式调用旧YOLO入口。

## 8. GPU调度与取消验收

沿用现有任务系统，统一进程内gate与跨进程GPU UUID互斥；训练/验证/离线RF推理在同卡上按队列串行。仅保护运行资源，不扩展P4实时多模型调度。旧复现程序若不遵守锁，不假定它安全：启动预检告知并阻止已知冲突，不擅自结束用户进程。

必须测试：等待GPU时取消、初始化时取消、batch边界取消、评估时取消、视频解码/推理/写缓存/导出时取消、重复点击取消、最后一步成功与取消竞态、关窗、Worker崩溃与重启后INTERRUPTED恢复。软取消先设信号并确认；无法响应时按有记录的超时策略只终止本任务拥有的子进程树，不杀其他Python/GPU任务。

门槛：排队取消拟≤2秒确认；可中断边界取消拟≤5秒确认，耗时原生调用必须显示“正在停止”及日志，超时/强制停止标INTERRUPTED而非成功。取消不得登记新成功ModelVersion或完成缓存；部分检查点标明格式/完整性/是否可恢复，只有验证后才提供恢复入口；取消后GPU锁释放，后续排队任务可运行。两个GUI进程竞争同GPU时不得同时进入受保护计算区。

## 9. RF正式路径Ultralytics零依赖硬门槛

这是RF运行路径的技术门槛，**不是整个仓库/产品自动获得发行许可**。旧历史代码与资产继续保留，但不属于RF可达运行闭包。

| 层级 | 必须满足的证据 |
|---|---|
| 安装闭包 | GUI运行环境与RF Worker闭包均无ultralytics/thop/platform/Plus；锁文件和传递依赖清单可核验，不通过旧venv site-packages/PYTHONPATH获取包 |
| 静态可达路径 | RF入口/中立服务装配/参数校验/数据转换/Registry/缓存/导出无Ultralytics import、YOLO对象、私有Trainer/NMS及派生实现调用；C/D/E逐项标出处置，不以关键词零匹配替代来源审查 |
| 动态导入 | 在阻断ultralytics.*导入的测试环境，从真实GUI选择RF走预检、训练夹具、重载评估、登记、视频、回放、导出与诊断；完整子进程导入日志及sys.modules无禁用包 |
| 环境独立 | 在全新、无Ultralytics的隔离测试环境运行；测试配置将旧Worker解释器/权重路径设为不可用，RF路径仍完成；不删除或重命名真实旧环境来做破坏性测试 |
| 模型/数据来源 | 仅已核实Nano官方权重/RF训练检查点；拒绝YOLO PT/ONNX/伪标签/旧缓存作为RF输入或初始化，路径与hash可追溯 |
| 失败分支 | CUDA缺失、环境污染、权重缺失、OOM、未知模型/缓存均明确失败，不回落YOLO或CPU AI；RF失败不触发任何旧Worker子进程 |
| 业务与合规 | 原GUI/数据/历史模型可按既有约定读取，历史展示不需要导入旧引擎；许可证/源码出处与零依赖结论分别记录，未决项不隐藏 |

A范围门槛覆盖训练/数据/Registry/GUI启动/诊断；B补齐视频/缓存/导出。任一禁用包被安装/导入、旧Worker被启动、旧权重被用作RF模型，直接FAIL并阻断对应阶段验收；报告用BLOCKED记录门禁状态，不继续下一阶段。

## 10. 测试矩阵与数据保护

| 编号 | 验证范围 | 阶段门槛 |
|---|---|---|
| A-T01 | 原200图/402框、16正常、160/40/0；类别0/1基映射、多类别、合法坐标/尺寸/来源 | 计数/哈希/映射逐项一致，不新划分或伪造检测真值 |
| A-T02 | GUI简易/高级、有效参数、AMP、预检、历史与日志，1080p/高DPI | 真实GUI截图及操作证据；无静态效果冒充 |
| A-T03 | 训练入口夹具、已有权重加载、统一评估、保存/重载 | CUDA证据与协议一致；不重复P3.6完整训练 |
| A-T04 | 可信RF登记、拒绝不匹配权重、失败/取消事务、历史模型读取 | 新UUID、工件校验、历史记录不变；不自动晋升生产 |
| AB-T05 | 同GPU队列/跨进程锁、各阶段取消、崩溃、重启/关窗 | 无并行抢占/锁泄露/孤儿任务/假成功；无关进程不被结束 |
| B-T01 | 普通/非零PTS/片段/VFR样本；解码、类名/置信度/坐标与逐帧跳转 | 相对时间含义统一；VFR样本缺失明确NOT TESTED，不宣称覆盖 |
| B-T02 | RF与旧YOLO缓存、参数/模型/来源变更、损坏/中断/部分缓存 | 不跨后端命中；旧缓存文件哈希不变 |
| B-T03 | 三Tab、播放/暂停/拖动/指定时间/逐帧、空检测、输入异常 | 真实GUI操作不崩溃；预处理回放标识明确 |
| B-T04 | 带框视频/截图/CSV/JSON、取消、同名保护、来源核验 | 同一预测流可追溯，实际框/模型/时间一致，无旧文件覆盖 |
| B-T05 | 使用既有权重的完整70.04秒工程回放与性能 | 记录加载、预热、p50/p95、前向/流水线/GUI、显存/RSS；不承诺生产FPS |
| AB-T06 | 零依赖静态/动态/污染/故障分支 | 第9节门槛全部满足，对应阶段才能PASS |
| AB-T07 | 用户数据/环境保护与必要P1/P2/P3回归 | 独立项目副本；真实库全表/工件/图片哈希不变，不修改冻结版本/历史模型 |

每阶段先记录新的只读保护基线，不能按旧251帧/3模型数量覆盖用户随后新增数据。测试写入只发生在独立项目副本/新增测试目录；报告区分功能通过、标注真值、独立工业验证。旧Ultralytics复现需单独适用授权，不为验证RF而重新执行旧训练。

## 11. 许可证与产权跟踪

沿用legal/LICENSE_POLICY.md、THIRD_PARTY_NOTICES.md、ULTRALYTICS_ISOLATION_AUDIT.md与P3.6原始证据，保持Nano版本/权重许可可追溯，不自动升级模型包或下载Plus。跟踪C/D/E原实现出处与独立替代、IVAD产权主体、Qt许可材料及替换/重链接条件、两套FFmpeg构建/codec来源、NVIDIA运行库再分发清单、缺失通知及Rust/原生传递组件。

RF技术门槛PASS不等于以上法律问题PASS。内部工程集成与未来发行分别记录状态；若发现待接入实现来自受限/未知来源，先隔离并阻断该工作包，提交替代方案，不改名掩盖来源。不购买许可证、不删除声明、不修改根LICENSE或专有草案生效状态。

## 12. 工作量、风险与停止条件

A约5–7.5人日，B约4–6.25人日，合计约**9–14开发人日**（四舍五入，含分阶段验收）。相比P3.6的6–11人日粗估，本计划显式补入评估差异归因、GUI闭包零依赖、跨进程取消及完整缓存回归；不是日历交付承诺。法务/产权确认、独立现场数据、意外上游问题另计。优先固定现有已验收Nano环境，减少新增依赖。

| 主要风险 | 处理与停止点 |
|---|---|
| 训练/重载指标差异无法解释 | A3阻断；保留双方真实成绩，不重训掩盖差异，不选高值 |
| 源码或原生组件许可/产权不明 | 对应实现隔离，许可证状态PARTIAL/BLOCKED；不解除打包冻结 |
| Registry/导出隐含YOLO、.pth/.ckpt混用 | 后端/格式白名单、真实重载、事务与引用校验；不直接套旧路径 |
| 缓存错误命中、旧模型误用 | 后端签名、完成标记、跨后端负向测试；不自动复用旧缓存 |
| GPU锁/取消竞态或不可中断调用 | 任务状态机、跨进程锁、拥有者限定的终止策略和完整日志；有孤儿/假成功则阻断 |
| LIMITED同源数据与工业误报 | 保持实验提示；新日期/摄像头/故障独立样本另行准备，不能升级工业准确率结论 |
| 工作量明显超出估计、需要迁移真实历史数据 | 报告原因与具体变更方案，等待用户决定，不自动扩阶段 |

A验收需真实GUI与服务、数据/Registry、评估统一、A零依赖、取消/保护全部PASS；B验收再要求真实离线视频、旧缓存隔离、回放/导出、B零依赖全部PASS。未验证项不报PASS；阶段阻断不进入下一阶段。最终仍停在工程实验，无生产发布、RTSP/PLC/报警、P4功能或任何分发构建。

本轮仅完成Git收尾与此规划；正式开发需用户下一次明确批准。
