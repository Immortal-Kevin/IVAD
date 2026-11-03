# IVAD Dataset Standard 1.0

权威模型：src/Ids/Ids.cs 的 Document、Entity、Asset 及 Rules.Validate。内部与交换包共用同一模型，不用模型类别编号当工业故障身份。自研协议/实现Apache-2.0，用户数据不因此成为开源数据。

## 基本结构

Document含schema=`ids/1.0`、project_id、递增sequence、entities、assets。所有实体使用UUID、kind、revision和data。一个Document只有一个Project；设备与相机通过稳定ID关联。

| 实体 | data关键字段 |
|---|---|
| Site | name |
| Project | name, site_id |
| Equipment | name, project_id |
| Camera | name, equipment_id |
| Video | camera_id, asset_path, original_name |
| Frame | video_id, asset_path, width, height, pts_us, source_timestamp_100ns, time_source, decode_index, sampling_interval_seconds, state |
| Fault | name, taxonomy_version；id是工业故障身份 |
| Annotation | frame_id, fault_id, shape, points, coordinate_space；deleted用于保留历史的撤销 |
| ROI | frame_id, camera_id, shape, points, coordinate_space |
| Review | frame_id, status, reviewer, utc |
| Revision | entity_id, entity_revision, actor, utc, snapshot |

state四种：normal、abnormal、unknown、unannotated。审核状态：confirmed、rejected、needs_work、unknown。两者独立存储，不自动将未知或未标注当负样本。数据集适配读取最后一条审核状态。

几何用原图像素，box=[x1,y1,x2,y2]，polygon=[x1,y1,...]。校验边界、有限数值、点数和正面积。支持矩形编辑、移动、调整及多边形/ROI顶点位置修改，软删除保留修订。ROI摄像头必须与帧的源视频一致，(video_id, source_timestamp_100ns)唯一，pts_us必须等于100ns时间向下除10。当前尚未实现复杂自交多边形拓扑检查；ROI保留相机关联，跨帧自动投影未实现。

时间：Windows Media Foundation返回样本时间，原样保存100ns单位，同时换算pts_us；不使用frame_index/FPS伪造PTS。decode_index仅辅助追踪，不作为时间真值。范围为[start,end)，从start锚定间隔网格选择首个达到阈值的真实样本；不把网格时间写成PTS。VFR不按固定FPS重建时间。接受同可见尺寸的首帧重协商和已声明的编码填充裁切（1080/1088），拒绝实际可见尺寸/像素类型变化。旋转元数据与非常规封装仍需验证。

## 文件与持久化

媒体复制到assets/<SHA256>.<ext>，Asset记录path、sha256、bytes。保存前校验实体和资产。JSON使用UTF-8；project.ids.json原子替换，保留.backup；独占写锁内验证资产和原始清单hash，阻止并发覆盖及清理竞态。复制临时文件和导出流还校验实际读取长度/hash。文件不主动删除，引用变更不会自动清理业务资产。

## 完整包与增量包

ZIP包含package.json、document.json、assets/。Envelope字段：format=`ids-package/1.0`，mode=full/incremental，base_sha256，target_sha256，included_assets。

完整包携带全部资产；增量包携带目标完整实体清单及相对基线新增/改变的资产。它是“全量元数据+增量文件”，尚不是最小实体补丁。完整包可导入空项目或相同状态；不同现有状态拒绝。增量要求基线指纹完全匹配；若目标指纹已等于包的目标指纹，则按幂等重放校验，不重复创建实体。其他状态报告冲突，不自动最后写入覆盖。

支持A→B完整包，A→B增量，再B→A增量。分叉双方都改动时整体拒绝并保留原项目；人工逐字段合并UI未实现。包名不可覆盖，快照不可变。基线可由GUI单独保存；快照不因后续项目编辑改变。

导入先检查路径、重复/大小写冲突、保留文件名、符号链接、数量与总大小上限、声明文件集合、schema、引用、完整哈希；staging全部通过后提交。失败不替换项目清单，并回滚本次新增文件。上限：100,000条ZIP entry、总解压20GiB、元数据16MiB。不是任意规模工厂录像分发方案，需按场景调整。

当前指纹是本实现稳定序列化JSON的SHA256，不宣称兼容RFC 8785或任意第三方JSON属性重排。跨语言实现需遵守约定或在下一版本引入标准canonical JSON并配迁移测试。

## 模型适配

Full侧COCO检测适配将Fault UUID映射为临时category_id，并在导出中保留ids_fault_id。只导出normal/abnormal且最新审核confirmed的帧。当前矩形适配；多边形明确拒绝，不能静默丢标签。训练/验证/测试按源录像分组划分、分割导出和工业准确率尚未实现。

验证覆盖见build/test-data/*/results.json及governance/RELEASE_READINESS.md。
