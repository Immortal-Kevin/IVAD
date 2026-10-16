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


## P2 Hotfix during P3（2026-10-15）

Schema0007（P2 Hotfix during P3）：仅追加cameras.details JSON（code/location/equipment/enabled，旧{}按启用兼容）和media_assets.lifecycle JSON（hidden/removed/revision/history/copy_cleanup及隔离路径）。帧完成状态复用frames.handling.completion_state与completion_updated_at，UNLABELED/LABELED；缺失时按实际标注内容推导，EXCLUDED/UNKNOWN/CONFLICT不视为有效完成。GUI普通保存不改变旧Annotation.status；真值改变时handling.review_stale要求新数据集人工复审。数据集独立审核经CAS/事务追加审核修订，不自动批准。0006→0007前备份、不重建旧表；用户备份和P3副本所有旧列逐行相同。P3训练/模型及冻结快照不重写。


## P3 Dataset Management Hotfix（2026-10-15）

Schema仍0008，无新增表、列或migration；Camera/Media/Frame/Annotation/DatasetVersion UUID不变。数据集草稿和候选排除为GUI会话状态，不占用全局handling状态。全局无效帧继续复用is_excluded及历史。

新实验冻结manifest在现有format_version=1增加可选admission对象：policy=human-auto-v1、scope=EXPERIMENT_ONLY、validation_level=AUTO_CHECKED_HUMAN、independent_review=false、split_status、allow_limited、allow_multi_camera、camera_ids、source_groups、expected_counts、actual_counts、near_duplicate_cross_split。样本增加validation_level、media_parent_id、media_lifecycle；annotation_status原值完整保留。DatasetVersion.summary JSON附带admission，模型details登记dataset_admission。旧manifest没有此字段时按原审核政策解析；不会原地重写旧文件或改变旧hash。


## P3 Dataset Hotfix v2 时间语义（2026-10-15）

无Schema变更，仍0008。frames.pts_us保留为原始帧PTS已按time_base转换后的微秒，不是当前媒体相对秒，也不是UTC拍摄时间；原始PTS ticks仅能从真实解码证据读取，历史库未独立保存tick值，派生接口raw_pts缺省None，不伪造。frames.time_us是既有媒体相对微秒，两者不改写。

统一派生接口ivad_app/video/timestamps.py：media_relative_us=pts_us-media.video.origin_us；返回media_relative_seconds。origin缺失则显式使用历史time_us并给出待核验警告；时间不一致/越界保留诊断，不在读路径迁移。source_relative_us递归累加每级CLIP.clip_info.first_source_time_us（实际首帧在父媒体中的相对时间）；缺失映射返回未知，不用requested_start_us猜测。time_base保留流时间基；capture_datetime缺省None，没有从文件名推断拍摄日期。

DatasetService.screening和MediaService.frames/frame_image返回这些派生键；新冻结样本可选timing对象保留上述语义。旧DatasetVersion/manifest/SHA256不重写；TrainingRun和ModelRegistry结构不变。播放器经同一relative_time_us函数，标注页只增相对时间信息，不改标注内容。


## Schema0009：持久化Dataset草稿（2026-10-16）

0008→0009增量迁移只在datasets增加details JSON NOT NULL默认{}、revision INTEGER NOT NULL默认0，不重建表、删行或变更UUID；DatasetVersion/Sample、Frame、Annotation、Camera、TrainingRun/ModelVersion表结构不变。沿用迁移前SQLite backup及完整性检查，ProjectInfo.schema同步0009。

Dataset.details：project_id、task=detect、camera_ids、fault_ids、allow_multi_camera、updated_at；draft包含state DRAFT/VALIDATED、revision、members[{frame_id,annotation_id,annotation_revision}]、settings{preset,strategy,ratios,seed,allow_leakage,allow_limited}、saved_at、validation{signature,at,report}。引用和作用域通过业务事务校验；JSON不提供新增数据库外键。保存revision CAS并使旧validation失效；检查不改变内容revision。

冻结仍写既有DatasetVersion及DatasetSample，summary增加state=FROZEN、draft_revision及分集合statistics。新manifest可记录dataset_scope、draft_revision、draft_validation_signature、preset与实际statistics，旧文件和hash不改写。TrainingRun.details新增dataset_id，原version_id继续保留。

旧Dataset默认details={}、revision=0，保留原名称、版本和工件；列表不会因为没有Draft而隐藏它，也不自动猜原草稿成员。真实示例项目本轮只读，原Schema0008未升级；副本0009迁移/重启/冻结已验。下次用户通过新源码打开旧项目时先自动生成迁移备份，再新增字段。
