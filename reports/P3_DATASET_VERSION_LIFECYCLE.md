# P3 Dataset版本生命周期

日期：2026-10-16。限定范围PASS。

## 状态边界

DRAFT是可编辑的已保存草稿；未保存修改另有GUI状态。VALIDATED表示该保存修订通过文件/标注/引用检查，可能同时有LIMITED独立性限制，不等于生产批准。修改成员、目标关联、名称或划分设置使旧检查失效；重新保存后回到DRAFT，再检查。FROZEN属于不可变DatasetVersion，与仍可编辑的当前草稿分开。

Project→Dataset（稳定UUID）→嵌入DatasetDraft→DatasetVersion→TrainingRun→ModelVersion。0009复用现有Dataset表而非重复建表，DatasetVersion原外键/唯一版本号约束保持。当前版本页仅显示选中Dataset UUID的历史，包含日期、图片数、目标数、划分和校验状态；无版本显示明确指引，不显示空白误导。

## 检查并冻结

GUI要求已选择Dataset、无未保存修改、当前保存修订已VALIDATED，再确认提交后台任务。服务只以数据库已保存的身份/成员/设置构造冻结请求，不信任客户端替换成员。重新做完整候选/划分检查，与保存的检查签名核对；源标注修改、剔除、摄像头/类别/来源变化或草稿revision不一致都会拒绝。

提交阶段用事务再次比较Dataset内容revision、VALIDATED状态/签名、标注/handling及来源与类别。生成所属Dataset下递增v1/v2，复制并hash校验图片，保存完整Annotation payload、类别映射、实际split、来源和Manifest SHA256，SQL写入DatasetVersion/Sample。新快照还可记录dataset_scope、草稿修订与检查签名、预设、统计及实验准入；旧manifest原样读取、不自动升级。

## 实测版本与训练入口

真实独立副本：保存200张并重启恢复→小样本LIMITED检查→冻结v1（200图片/402目标）→移除一成员→保存同一Dataset UUID的revision2→重新检查→冻结v2（199图片）。v1 manifest逐字节不变，v1/v2分别有版本UUID/哈希，Dataset总数仍1。

![同一Dataset的v1和v2](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-lifecycle-20261016/real-gui-final/06-v1-v2-independent.png)

训练页新增“所属数据集”选择，版本列表跟随Dataset。只从实际DatasetVersion中列出Train/Val非空、清单hash可校验的项；只有草稿或只有Train的版本不能作为该入口的训练数据。启动前仍必须全量校验图片、标注和来源。TrainingRun保留version_id并补充dataset_id，架构与Worker调用不变；不同模型可以引用同一版本。

![训练入口选择冻结版本](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-lifecycle-20261016/real-gui-final/05-training-version-picker.png)

实测LIMITED工程v1通过训练前数据检查且在训练页可选；这不等于真实GPU训练或工业批准。本轮没有运行新的YOLO26n/YOLO11n实验。旧数据集没有Draft时仍列出并保留其历史版本，继续创建版本前要明确配置和保存草稿，不猜旧成员。

并发保存CAS、检查失效、源修订改变阻止冻结、图片损坏/类别/导出回归及原版本不变均见测试结果。永久删除、人工拖动调整及生产性能认证不在范围内。保持打包冻结，不进入P4–P10。
