# NVIDIA WPF 开发集成

状态：技术部分通过，完整架构/许可验收未完成。PACKAGING_FREEZE=TRUE，DISTRIBUTION_STATUS=BLOCKED。

Intel 基线为 main / 5e157141c51f8f0885a7c46de05a30865ceede73；复用 H1–H5、StableIdsConverter、Rules.Validate、Exporter/Importer 和 925 帧资格筛选。源码在 wpf_intel/src，原 Apache-2.0 LICENSE/NOTICE 保留。NvidiaBridge、NvidiaMedia、NvidiaWorkspace 及 Python 集成服务属于私有集成代码，不授予公开发布许可。

默认 `python -m ivad_app --workspace <独立数据目录> [--project <项目目录>]` 启动 WPF。先执行 `wpf_intel/scripts/build.ps1 -OutputDirectory build/final`。这是开发构建，不是发行包。旧 Qt 源码入口在 `ivad_app/history/qt_main.py`，不从新入口加载；历史环境原样保留。旧打包配置尚未迁移，禁止用它构建新发行载荷。

WPF 通过继承的 stdin/stdout 管道连接 Python 服务，不监听 TCP。协议 ivad-local/1 使用进程随机 token；写入目录必须位于显式 workspace。该隔离不能替代 Windows 用户 ACL 或真正的业务角色授权。Intel 原有“审核人名称显示管理员控件”仍不是权限系统。

SQLite 沿用 Schema 0009 的 projects/cameras/media_assets/frames/annotations/annotation_revisions/rois/settings 表。IDS 文档存入 settings 作为完整来源和修订证据；业务投影行保存指纹以拒绝其他服务修改后的静默覆盖。project.ids.json 是 WPF 可重建缓存，SQLite 为提交权威。新建或包导入仅允许受控新库，不自动迁移原工业库。包基线、资产及规范 JSON 由 Intel 原实现校验，Python 层补充顺序、UUID/修订及本地编辑冲突检测。

MF 桥接使用原 windows_source.py，IDS pts_us 保留 MF ticks/10，原始 MPEG-PES 90kHz 时间及相对时间另存 timestamp_evidence，不用帧序号重造时间。

IDS 训练适配仅取确认正常/异常且未软删除的帧；矩形转换到 NVIDIA xywh，多边形取原图顶点 min/max 外接框并记录规则。ROI 单独存储。默认按摄像头分组划分，少于两组拒绝自动训练，并拒绝跨划分同哈希图片。冻结到已有 DatasetVersion/样本表后复用原任务队列、RFDETRTrainingService、CUDA Worker 与 ModelService。WPF 提供 GPU、训练、验证、任务状态、取消、Registry 及单帧推理入口；当前指标为服务结果文本，尚未完成完整交互设计验收。

回滚：保留当前未提交用户文件；另建工作树检出 rollback/pre-intel-h1h5-20261104，不使用 reset --hard。原数据库不需要逆向迁移。测试库、备份及真实 IDS 均保存在程序目录之外。可选 ml_dtypes 仅从 RF 候选环境移入本地 optional-quarantine，按其 manifest 原路径恢复；不改原 .venv-rfdetr。
