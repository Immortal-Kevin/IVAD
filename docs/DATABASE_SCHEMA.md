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
