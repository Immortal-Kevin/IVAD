# P3.7 Legacy YOLO Retirement

日期：2026-10-19。正式训练仅Nano；旧事实与资产完整保留。共处置7个普通界面选项/操作：2个YOLO数据导出选项、2个YOLO基础模型选项、1个旧手工权重导入流程、离线新推理按钮与按配置复用旧引擎身份按钮2项。归档查询同时移除其派生模型选择项，不另按历史行数重复计入口。标注工作台未发现需删除的独立YOLO入口，保留box/polygon/ROI等人工功能；Nano仅目标检测，不宣称实例分割。

## 源码/调用与依赖矩阵

| 分类 | 实际文件/资产 | 可达关系、运行依赖与证据 |
|---|---|---|
| ACTIVE_RFDETR | compute/rfdetr_contract.py、rfdetr_probe.py、rfdetr_train_worker.py、rfdetr_evaluation.py、rfdetr_weights.py、gpu_lock.py | 正式Nano、独立解释器-I、官方RF API；实际CUDA Job及模块轨迹见Closure |
| ACTIVE_RFDETR | services/training_router.py、rfdetr_training_service.py、core/application.py | GUI→Router→RFService→RFWorker；旧路由方法直接拒绝，无动态旧import；预检拒绝旧初始化/环境 |
| ACTIVE_RFDETR | datasets/rfdetr.py | 从冻结人工真值直接产生COCO；类别UUID/内部ID/模型ID映射，未经过YOLO标签 |
| REPLACED | gui/training_page.py、training_controls.py | 新训练选择仅Nano，旧模型/恢复不可启动；排队/5状态/取消/重启测试 |
| REPLACED | gui/dataset_page.py | Native默认、COCO第二项；底层导出器未删 |
| LEGACY_READ_ONLY | datasets/exporters.py 的yolo_detect/yolo_segment分支 | 自身文本/坐标导出，无Ultralytics import或运行库；仅开发兼容工具，普通GUI不列出。YOLO格式不等于AGPL库 |
| LEGACY_READ_ONLY | services/model_service.py、TrainingRun/ModelVersion details | 服务默认查询只RF，显式归档读；原SHA/UUID/审核历史/数据集/Run关联不变；历史verify/export为文件校验/复制 |
| REMOVABLE_LATER | services/training_service.py、compute/train_worker.py、compute/model_adapters.py旧条目 | 旧训练服务启动/预检封禁；Worker保留YOLO/DetectionTrainer/NMS imports及历史证据，正式Router无调用；Adapter只描述符不是库 |
| BLOCKED | services/offline_demo_service.py历史run、compute/offline_worker.py | 普通提交和服务run均DEMO_MIGRATION_PENDING；历史实现保留，未启动；RF离线待P3.7-B |
| LEGACY_READ_ONLY | services/offline_cache.py、offline_demo_service.load/export/screenshot、demos目录 | 5完成缓存哈希核验；load仅读取manifest/成品视频，不导入Ultralytics；真实GUI历史回放验证，保留所有检测缓存 |
| REPLACED | jobs/manager.py、gui/main_window.py | 新旧YOLO提交拒绝；活动任务不按后端/项目丢弃，显示分类；完成AI历史按项目/正式后端过滤；cancel/get不按界面过滤 |
| LEGACY_READ_ONLY | .venv-nvidia、artifacts/p0、原YOLO PT/ONNX及训练目录 | 历史运行库和权重未删除/改名/卸载；普通GUI不使用此解释器；RF污染探针通过 |
| REMOVABLE_LATER | scripts/validate_p3_model.py、旧P0/P3/P3.5 GPU验证脚本 | 开发历史入口直接依赖Ultralytics；本轮未运行旧AI，不计入RF闭包，也未认证为可发行 |
| BLOCKED | packaging/nvidia/requirements-cuda.inventory.txt、packaging/requirements-distribution-lock.txt、packaging/ivad.spec及BUILD_PLAN | 未来构建方案/旧依赖材料仍有旧库；未构建最终payload，不改旧包、不宣称发行零依赖 |
| LEGACY_READ_ONLY | 旧报告/指南及licenses通知 | 保留真实历史与版权，不因字符串匹配就删除 |
| UNKNOWN（记录级） | backend缺失且架构不明确/冲突 | 默认排除正式选择，禁止新操作；当前真实0条；测试验证冲突不猜测 |

项目完整静态引用和动态导入检查在dependency-references.txt；检查直接imports、动态find_spec/模块阻断、Worker subprocess路径和三个环境实际包清单，不只查字符串。GUI21包、RF96包均find_spec无Ultralytics；旧环境48包保留。旧PYTHONPATH污染在-I下不可见；实际Worker forbidden_imports为空，主进程未导入旧training_service。

真实库3条旧YOLO训练和3个旧模型只读归档、2RF训练与2RF模型默认可见。归档明细与SHA见P37_LEGACY_TRAINING_ARCHIVE.md。活动GPU任务即使旧或UNKNOWN也保留可见；不重排旧任务，不终止无关GPU进程。已取消任务不会登记成功模型，沿用同事务门禁和GPU锁。

## 验收限制

1 failed, 86 passed, 1 skipped in 104.62s (0:01:44)，旧GUI默认YOLO断言失败保留，专用旧副本用例条件SKIP不计成功。新行为由独立原生GUI与200图导出验证。Qt根因未定，总体PARTIAL；不是全产品零Ultralytics发行认证。RF离线Worker、RF缓存身份与RF离线导出仍待B。

历史数据前后全表及2328文件SHA不变；没有删除、迁移原数据库、重训YOLO、改系统环境或模型改名。`PACKAGING_FREEZE=TRUE`，`DISTRIBUTION_STATUS=BLOCKED`。
