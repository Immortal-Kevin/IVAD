# P2 摄像头、样本、数据集和模型关系

日期：2026-10-15；基线 c79d50d；Schema 0008 保持；PACKAGING_FREEZE = TRUE。

## 复用的数据关系

Project → Camera → MediaAsset / Clip → Frame → Annotation → DatasetVersion。Frame 不新增重复 Camera 字段，按可信媒体外键继承。故障类型复用 LabelCategory，模型版本复用 ModelVersion / 既有 Model Registry；逻辑模型家族由既有模型元数据表示，不新造第二套模型仓库。

DatasetService.camera_samples(camera_id, image_tag, fault_id, root, include_excluded) 查询已持久化样本及来源、故障 UUID、审核和完成状态。NORMAL 查询得到该摄像头自身参考库；ABNORMAL 可再按故障 UUID 查询。参考库不代表已审核训练真值。未关联有独立筛选，剔除默认排除。

不同摄像头的正常样本不会因同类故障自动合并。训练仍通过用户明确勾选样本及现有来源分组策略组合；没有新增“禁止跨摄像头训练”的数据库限制。冻结版本原本已有 camera_id、media_id、source_group_id、标注修订及来源信息，继续保留，不重写旧 manifest。跨来源分组与泄漏校验仍由 P3 执行。

## 多对多模型配置预留

ModelService.configure_camera(camera_id, model_version_id, fault_ids, root, roi_scope) 在项目 SettingRecord 的 camera_detector_configurations 中追加独立配置 UUID；camera_configurations 查询。校验摄像头、模型版本、类别和可选 ROI 均属当前项目；被配置引用的故障类别不能物理删除，可禁用。

一台摄像头可有多个配置，一个配置可对应多个故障 UUID；同一 ModelVersion 可被多个摄像头配置复用，另可配置专用版本。没有 camera 或 fault 的单模型唯一限制。现有模型状态、模型权重、模型版本和发布记录不改。

本轮只实现经验证的元数据接口；记录 enabled=False、purpose=configuration_only。没有正式配置 GUI、在线推理、报警调度、自动选模或自动生产发布；这些不能当作已完成的 P4 功能。

## 存储与兼容

无新增表、无 Migration，Schema 保持 0008。批次状态复用 Frame.handling，配置复用项目 SettingRecord。摄像头创建完整性快照同时保护这些项目配置。测试验证同一模型跨机共享、同一摄像头双模型、故障筛选、非法关联拒绝及旧模型记录不变。P3 训练、审核、候选/生产发布门槛不变。
