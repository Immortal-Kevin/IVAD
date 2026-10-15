# SQLite Schema 0003（P2）

应用级 runtime/catalog.sqlite 保留设置、最近项目和全部非AI任务历史。项目级 project.sqlite 保留项目配置，新增下列业务表；GUI通过服务访问，不直接执行SQL。

|表|内容与约束|
|---|---|
|projects / settings / jobs|P1原表；jobs增加payload/result JSON，不移除旧字段|
|media_assets|UUID、项目、COPY/REFERENCE、原路径/可访问路径、大小/SHA256、实际解码元数据、摄像头/厂区/设备、导入状态及任务|
|frames|媒体外键、实际PTS/相对时间微秒、可确定帧序号、尺寸、相对路径、SHA256/dHash、参数/参数hash、任务；媒体+PTS+参数hash唯一|
|label_categories|稳定UUID、名称/描述/设备/父类、默认类型、启用状态、修订；父类外键|
|annotations|每帧唯一文档，原图像素坐标objects、整帧标签、DRAFT/REVIEWED/APPROVED/REJECTED、修订、Human Generated|
|annotation_revisions|标注文档外键+修订唯一，保留每次保存的完整真值|
|rois|media:UUID或camera:编号作用域唯一；归一化几何、修订历史，与训练目标分开|
|clip_labels|媒体外键、相对时间起止、标签/类别/审核、人工来源、修改历史、逻辑删除|
|datasets|数据集UUID/名称/创建时间|
|dataset_versions|数据集外键+版本号唯一、清单相对路径/hash、统计/类别快照；已提交版本不可覆盖|
|dataset_samples|版本外键+帧UUID唯一，划分、图片hash、标注快照|
|exports|版本外键、格式、外部输出目录、导出清单hash、创建时间|

0001→0002→0003迁移先只读检查并使用SQLite backup API备份，再事务升级。未知/损坏数据库拒绝打开，不重建原数据库。0003只添加表与任务列。外键启用、busy_timeout=5000；每次业务操作独立Session。使用稳定UUID、原图像素坐标，ROI单独归一化；播放器/抽帧相对时间=实际PTS减流起点，不根据FPS估算。

目录提交顺序为暂存→文件校验→同盘rename→数据库提交。可捕获数据库失败回退至.partial；进程在两步之间被强杀可能留下孤立目录，必须人工核对，不自动删除。项目一致性检查扫描.partial、媒体/帧/快照及已登记导出清单；完整备份恢复工具不在P2。

## Schema0004：人工保存视频片段（2026-10-14）

当前HEAD=0004，0003仍是历史业务基线。新增media_assets.kind（ORIGINAL/CLIP，旧行默认ORIGINAL）、parent_id（来源媒体UUID，可空）、clip_info JSON（旧行默认{}）。来源为应用层关系，不重建现表；完整性检查验证父记录、来源hash与有效范围。clip_info保留请求start/end微秒、实际first/last源相对时间微秒、生成时间、源hash、帧数、编码、旋转、备注。路径/媒体UUID/任务/导入时间使用原列，片段COPY存media/。0003迁移前自动备份，原列和值真实测试保留。


## Schema0005 P2 UX v2

当前HEAD=0005。新cameras表含稳定UUID id、可重名name、旧编号别名legacy_key、revision、history。media_assets.camera_id、rois.camera_id是服务验证的项目内关系；新增可空列，不重建旧SQLite表创建外键。旧camera文本保留，旧camera ROI scope迁移为camera:UUID，几何/修订不动。项目本身从独立数据库限定Camera所属范围。

frames.handling JSON默认{}：is_excluded、exclusion_reason、excluded_at/by、previous_state、restored_at、revision、history。Annotation.image_tag及AnnotationRevision复用，未处理/正常/异常/待复核/冲突推导，EXCLUDED覆盖；审核状态独立，旧文档不重写。Frame/Annotation/Media主键及来源不删除。

0004→0005使用既有SQLite backup API先备份，只增加表/列及关联映射，不清空/重建。已达目标版本的只读服务访问仍检验完整性/版本，不重复运行Alembic upgrade；实际升级仍受MIGRATION_LOCK与事务保护。回滚/降级拒绝，保留备份供后续人工恢复。

批量预览+提交以revision核验；late failure全事务回滚。冻结发布再次检查handling版本；新候选排除未处理/未知/剔除/冲突，旧dataset manifest、样本和历史导出保持不可变。


## 2026-10-15 v3实施更新

Schema0006（P3）：新增training_runs/model_versions两表，均id UUID、details JSON、revision CAS。训练记录保留operation、state、项目内path、dataset version、参数/初始hash/GPU/job/指标/错误；模型记录保存实验/候选/生产、权重hash/ONNX/类映射/验证/历史。无永久删除API、原表不重建；旧0005升级前备份，旧表SQL一致测试通过。生产切换同项目事务，历史模型降为候选，旧工件与冻结集不变。原用户项目本轮未升级；旧Beta2不能打开0006。
