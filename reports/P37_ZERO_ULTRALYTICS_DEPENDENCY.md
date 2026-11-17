# P3.7-A Ultralytics零依赖验收

日期2026-10-16。**PASS（RF正式训练运行闭包）**。不是整个IVAD已经移除Ultralytics，也不是法律分发认证。

正式链路：现有GUI → 中立training_router → RFDETRTrainingService → 独立 `.venv-rfdetr` / `-I` → rfdetr_train_worker → 官方RF-DETR Nano。没有继承旧DetectionTrainer，不使用YOLO参数、YOLO预训练权重或旧GPU解释器。

| 检查 | 结果与证据 |
|---|---|
| 环境安装清单 | PASS：96个包中无Ultralytics、ultralytics-thop/platform、RF-DETR Plus；全量清单 `license-audit/rf-all/inventory.json` |
| 实际GPU训练/评估模块 | PASS：最终GUI短训及固定权重40图重载的loaded_modules、forbidden_imports均无禁止模块；真实result.json保留 |
| GUI启动/服务装配 | PASS：独立子进程测试确认未导入旧training_service及Ultralytics；历史列表查询只读TrainingRun |
| 旧PYTHONPATH污染 | PASS：故意继承旧venv路径，-I解释器忽略；find_spec为空，sys.path无旧环境。见zero-dependency.json |
| 显式污染负测试 | PASS：独立测试目录放置带拒绝执行内容的假Ultralytics包，Worker检测即BLOCKED，未执行其代码/AI；未污染任何venv |
| 导入防线 | PASS：MetaPathFinder拒绝Ultralytics相关命名空间、thop、Plus；独立Python解释器拒绝旧YOLO/GUI环境路径 |
| 权重来源 | PASS：官方Nano PTH哈希固定，拒绝YOLO/ONNX/CKPT初始化；新登记RF模型类别UUID需匹配 |
| 故障/取消分支 | PASS：OOM、崩溃、协议错误受控注入均FAILED且未登记模型；实际取消无成功模型，无旧引擎回退 |
| 原始环境 | PASS：RF环境全部包版本及METADATA哈希与P3.6一致；未安装依赖、未改原CUDA/GUI环境 |

静态边界：旧实现仅在用户明确选择YOLO架构时延迟加载；旧服务额外拒绝RF架构，防止错误路由。GUI中的历史YOLO选项、旧离线演示、旧模型/权重/许可证均保留，未执行正式P3.7-B迁移。RF新Worker不导入GUI、SQLAlchemy或旧Worker。

实际CUDA证据：RTX5070Ti；模型参数/前向/梯度均在CUDA，发生真实权重更新；每帧预测由模型输出生成。COCO计分、数据加载与Windows不支持的匹配器SciPy计算可以在CPU完成，这不是CPU神经网络训练/推理回退。

未执行项目：未来安装包最小payload零依赖、RF离线视频缓存、全产品零Ultralytics验收均NOT TESTED/未授权。本轮仅A范围门禁通过；历史许可证和免费闭源发行缺口见 `legal/P37_FREE_PROPRIETARY_LICENSE_AUDIT.md`。
## 2026-10-19 收尾补充

当前Router不再延迟启动旧训练，所有普通新训练仅RF Nano。GUI/RF环境分别21/96包，无Ultralytics可导入；旧环境48包原样保留。当前GPU验证 `8da15e9d-d101-482f-a529-d3a689bbb5cf` / `949dd493-6465-48f6-a976-0236d65d6bf6` 成功，两次规范评估parity PASS，forbidden_imports为空；主进程导入阻断及-I旧PYTHONPATH污染探针通过。

本轮验证不是新梯度训练；既有P3.7-A短训证据保留。P3.5新旧引擎任务封禁，历史缓存只读，不声称RF已接管离线视频。全产品迁移PARTIAL、正式发行BLOCKED，Qt根因仍PARTIAL。
