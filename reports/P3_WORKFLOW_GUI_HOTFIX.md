# P3 数据集流程与训练界面 Hotfix

日期：2026-10-16。范围仅本轮P3 GUI/数据集工作流，PACKAGING_FREEZE=TRUE。未进入P4–P10，未打包、重装依赖、运行P0或重新训练。

## 结果

- 划分按钮原先由draft_dirty直接禁用，必须返回创建页保存。现采用指令允许的“点击检查先原子保存”方案：保存全部成员及配置，同一Dataset UUID/CAS修订成功后才检查。没有后台定时自动保存，界面明确提示此机制。
- 保存过程中禁用当前编辑区以串行化写入；失败保留内存修改、显示失败且不划分。资料完整且比例100%时按钮可用，缺项/保存中有明确说明。
- 两个风险复选框从界面移除，使用默认工程实验/严格验证。旧字段和历史快照兼容保留；新草稿的确认由服务层检查签名约束，不能用隐藏旧控件绕过。
- 训练基础/高级参数改为约40/60双栏，窄窗口上下排列；下方保留记录/实际参数/曲线。五动作宽窗口同排、窄窗口换行。
- 简易模式参数只读且提供中文说明，高级模式可编辑真实支持参数。预检覆盖数据/参数/GPU/权重/Worker路径，变更失效、启动复核、重复提交保护、取消指定TrainingRun确认。

## 保护与真实资产

真实项目：E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2。

只读SQLite在线备份及全表快照：artifacts/workflow-training-gui-20261016/before/；完成后after/。全表内容0变化，660个datasets/models/training/项目清单文件哈希0变化；5个选取的GPU环境/锁定文件哈希0变化（非整个环境逐文件审计）。结果见protection-results.json。

- Dataset 8525test1：5ea5cbb0-3e8e-4c45-a0bd-9ec7ae9e9782，200成员。
- v1：fd9a3ba2-ed9b-4698-8838-5002b036fef0；清单SHA256：5eecfe2509b89dd67ec0ecf6280654607f036599099d538d305e27c27798a8ac。
- TrainingRun：7a01bcad-4b18-4cec-a0f7-1a31f94d6a32，SUCCEEDED，YOLO11n。
- ModelVersion：4a1c7df7-dec7-427b-8861-6b247ef3ebbd，原权重、ONNX、指标和日志保留。
- 原项目251帧、217份标注、720条标注修订、3个Camera保持；Schema0009不变，无migration，无原项目写入。

独立副本验证保留200成员、同Dataset修订、160/40/0 LIMITED、新v2及重开；旧v1清单、TrainingRun、ModelRegistry未变化。仅副本生成新版本，未改写真实项目或工业标注。

## 架构与修改文件

Camera一对多故障Dataset；Dataset一对多不可变DatasetVersion；Version可多次训练并注册不同模型。保持Camera多模型关联接口，不增加推理调度。

修改：gui/dataset_lifecycle.py、gui/p2_controller.py、gui/training_page.py；新增gui/training_controls.py；services/dataset_lifecycle.py、dataset_service.py、training_service.py及针对性测试。均位于ivad_app/下。新增只读审计脚本scripts/audit_workflow_assets.py。保留现有Worker、队列及模型注册逻辑。

## 测试与证据

完整针对性回归61通过、0失败（排除两个需显式副本的用例）；另以现有8525test1独立副本完成1项200成员/旧v1/新v2/重开验证，合计62不同用例通过。末次100%训练专项2通过、200%专项3通过（重复复验，不重复计入62）。原始证据pass.xml、accepted100.xml、accepted200.xml及final-gui/real-copy-results.json位于artifacts/workflow-training-gui-20261016/。

真实Qt GUI截图（Windows平台，非生成界面）：

- ../artifacts/workflow-training-gui-20261016/pass-gui/dataset-validation-mode.png
- ../artifacts/workflow-training-gui-20261016/accepted-controls-100/training-1920.png
- ../artifacts/workflow-training-gui-20261016/accepted-controls-100/training-920.png
- ../artifacts/workflow-training-gui-20261016/final-gui/real-copy-200.png
- ../artifacts/workflow-training-gui-20261016/accepted-controls-200/training-920.png

100%实际1920×1080，5按钮y坐标一致；请求920宽受既有MainWindow最小宽度1040限制，实际1040×720，按钮2列换行。200%允许纵向滚动。真实175%系统缩放也完成GUI操作。geometry JSON记录实际尺寸及DPR。最初offscreen截图缺少字体回退产生方块字，不作为中文显示证据；改用Windows Qt平台截图后中文正常。

首轮出现1个旧行为测试断言失败（要求dirty时按钮禁用），已按本次需求更新；扩大回归的旧测试清理等待未保存确认，终止本轮测试进程后显式丢弃其临时草稿进行清理，重新执行。没有终止用户原有软件实例。恢复参数新增断言的两个DPI试跑曾因后台刷新移除软件假GPU而各有1个夹具失败；显式等待刷新并重建独立假设备后复验通过。所有初始失败/中断证据保留，不计作最终通过。

## 限制与阶段

未做真实AMP训练、优化器对比训练、长期训练稳定性或工业准确率评估。Worker配置传递/失败注入证明接口，不冒充GPU性能实测。历史混合Qt原生访问冲突未定位限制继续保留，本轮串行验证未新增该故障。

只读盘点发现历史progress.epoch=21而epochs=20，result.evidence.actual_epochs=20；本轮保持原记录，不擅自修正历史证据，列为后续进度显示调查项。

已有P3成果保留；当前进度记录没有需重做的训练任务，因此不重启P3或重复训练，停止待审。打包冻结持续有效。
