# P3 数据集准入与历史数据验证

日期：2026-10-15。Schema0008不变，无Migration。

## 真实项目只读核验

原项目：`[本地路径]`。使用SQLite mode=ro连接检查并通过backup API生成本轮独立备份，原库未通过应用服务打开或迁移。原库/备份PRAGMA integrity_check均ok，foreign_key_check无错误；iterdump逻辑SHA256一致，证据backup-verification.json。只复制project.json、SQLite和frames到本轮审计副本，不复制/扫描原始长录像，也不在真实项目创建数据集或更改状态。

| 项目 | 实际结果 |
|---|---|
| 总抽帧记录 | 251 |
| 已有Annotation | 217（全部DRAFT），其余34未保存 |
| 8525压滤机 | 200帧：16正常、184异常 |
| 8525实验检测候选 | 200帧，402个目标，文件/哈希/尺寸、坐标、类别、人工来源均通过当前检查 |
| 当前类别 | 数据库实际名称“压滤版破裂”，UUID 63b964c3-88d8-45ad-9bbd-a93487582d4d，revision2，未擅自改为“压滤板破裂” |
| 其他51帧 | 17未处理/冲突等不合格，34未保存人工真值；均未自动纳入 |
| 另外两个已注册摄像头 | 当前没有关联抽帧记录；未根据文件名猜测或重建关联 |
| 8525来源 | 全部来自“超高压车间8525压滤机_1026191715.mp4”，独立原视频来源组仅1 |

上述“通过”是结构和软件准入检查，原人工标签本轮未重新作工业故障判断，不能宣称故障定位经独立人工复核或达到工业精度。也没有假定用户提及“约100张”就是当前实际总数。

## 新旧准入政策协调

保留原candidates()/preview()/freeze默认reviewed政策，旧冻结版本继续走原REVIEWED/APPROVED及历史审核规则，未自动放宽或重写旧版本。

新GUI显式请求experimental政策。必须存在revision≥1且Human Generated的持久化真值；历史REJECTED不能直接放行；正常不含故障目标或整帧类别；异常必须有合法box/polygon、有效且启用类别、合法坐标和目标UUID；未知、冲突、剔除及整帧异常无框拒绝Detection。文件必须存在、SHA256正确、能够解码且尺寸一致；摄像头关联存在，片段来源链可追溯。正常无框不要求ROI。

新快照保留annotation_status/source/revision原值，每样本增加validation_level=AUTO_CHECKED_HUMAN；admission.policy=human-auto-v1、scope=EXPERIMENT_ONLY、independent_review=false。同时记录摄像头集合、来源组、划分状态、预计/实际数量和风险确认。自动检查不会写REVIEWED/APPROVED，不删除任何审核字段。

Training Dataset Validator先验证快照完整性和上述政策证据，严格区分实验政策与旧审核政策；没有实验政策标记的DRAFT仍拒绝。正常负样本空标签、异常真实框、多类别映射及整帧分类/Detection分离保持。Train与Val仍须非空；精确重复、非法坐标、无类别、剔除、未知、冲突均拒绝。模型登记元数据补充dataset_admission，默认仍实验模型，生产注册人工批准门槛保持。

## 冻结与导出保护

冻结重做校验，复制并校验图片，提交时比较标注/handling revision、摄像头/媒体生命周期、原视频来源链及类别revision；变化则拒绝提交。旧冻结文件保持不可变。选中版本完整性检查可验证清单哈希、图片哈希/尺寸、类别与坐标，并列出frame/media/root-source/camera UUID、PTS与标注修订；失败显示BLOCKED。导出继续使用原适配器及唯一目录，不生成假检测框。

测试中已验证冻结后再软剔除/恢复不修改旧manifest，训练仍拒绝当前已剔除样本；历史审核及正常/异常对象保存恢复回归通过。

## 文件保护证据

本轮选取163项真实项目SQLite、既有P0/P3模型/记录、历史报告与截图及只读备份做SHA256核验，0变化。范围和具体哈希见artifacts/dataset-hotfix-20261015/protection-final.json；不将选取核验描述为全盘逐文件核验。没有覆盖原始录像、现有标注、冻结集或历史证据。真实检查明细见real-readonly-audit.json、real-candidate-validation.json、real-source-split-preview.json。

未新增依赖，使用既有.venv-p1；未改CUDA/Python/GPU环境，没有真实GPU训练或重新生成模型。实验模型不等于生产批准。
