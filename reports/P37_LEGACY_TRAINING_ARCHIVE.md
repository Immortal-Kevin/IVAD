# P3.7 Legacy Training Read-only Archive

日期：2026-10-19。分类来自当前真实SQLite快照，不改写训练事实。明确架构yolo11n/yolo26n且无冲突backend的历史记录，作为LEGACY_READ_ONLY；backend缺失但明确架构作为分类证据，不能把未知架构猜成YOLO。冲突或信息不足返回UNKNOWN；当前真实记录UNKNOWN=0，合成冲突测试已覆盖。

只读归档是服务查询的派生分类，不新增migration、不更新details/state/revision，不改变任何UUID或已有关系。默认runs/versions仅返回ACTIVE_RFDETR；开发审计显式include_archived=True可查全部，verify仅读文件哈希，不反序列化历史权重。

| TrainingRun UUID | 架构 | 原状态 | DatasetVersion | ModelVersion | 查询分类 |
|---|---|---|---|---|---|
| 7a01bcad-4b18-4cec-a0f7-1a31f94d6a32 | yolo11n | SUCCEEDED | fd9a3ba2-ed9b-4698-8838-5002b036fef0 | 4a1c7df7-dec7-427b-8861-6b247ef3ebbd | LEGACY_READ_ONLY |
| 1cc172a1-6d8b-434b-99ab-20e433535ca2 | yolo26n | SUCCEEDED | fd9a3ba2-ed9b-4698-8838-5002b036fef0 | dd2e7eec-2d1a-4840-8df4-4f6112ce805e | LEGACY_READ_ONLY |
| 37aa67d8-3d61-4f37-92ad-7b23cea2bf64 | yolo26n | SUCCEEDED | fd9a3ba2-ed9b-4698-8838-5002b036fef0 | 2814763f-1877-40b4-96e2-bccb396fbb6c | LEGACY_READ_ONLY |
| 75ede84e-4426-4928-9665-14df3f878328 | rfdetr-nano | SUCCEEDED | fd9a3ba2-ed9b-4698-8838-5002b036fef0 | 0d48a0e4-8fef-4ed9-953f-b84f9736976b | ACTIVE_RFDETR |
| f9237c67-8559-475d-b6ca-9ac06bea7121 | rfdetr-nano | SUCCEEDED | fd9a3ba2-ed9b-4698-8838-5002b036fef0 | 50de2cc6-6106-4df0-8362-d27761b26728 | ACTIVE_RFDETR |

正式列表2条RF、隐藏3条YOLO。真实库开始和结束均5条；本轮验证只在独立副本新增验证TrainingRun，非新增训练或新模型。所有状态均通过后端过滤，不限定成功状态。排队时使用持久JobRecord投影及时显示，创建TrainingRun后按job_id去重；取消/预检失败没有TrainingRun时仍能看到真实Job状态，投影ID明确来自JobRecord，不伪造TrainingRun UUID。

## 7a01bcad-4b18-4cec-a0f7-1a31f94d6a32

原路径 `training/7a01bcad-4b18-4cec-a0f7-1a31f94d6a32`；参数 `{"epochs": 20, "imgsz": 640, "batch": 4, "lr0": 0.01, "optimizer": "SGD", "weight_decay": 0.0005, "augment": true, "patience": 10, "seed": 123, "amp": false}`；Epoch `21`。日志、Checkpoint、验证指标及模型SHA仍在原目录和数据库，未归一化覆盖；缺字段不补猜。

## 1cc172a1-6d8b-434b-99ab-20e433535ca2

原路径 `training/1cc172a1-6d8b-434b-99ab-20e433535ca2`；参数 `{"epochs": 30, "imgsz": 640, "batch": 8, "lr0": 0.01, "optimizer": "auto", "weight_decay": 0.0005, "augment": true, "patience": 10, "seed": 123, "amp": true}`；Epoch `23`。日志、Checkpoint、验证指标及模型SHA仍在原目录和数据库，未归一化覆盖；缺字段不补猜。

## 37aa67d8-3d61-4f37-92ad-7b23cea2bf64

原路径 `training/37aa67d8-3d61-4f37-92ad-7b23cea2bf64`；参数 `{"epochs": 20, "imgsz": 640, "batch": 4, "lr0": 0.01, "optimizer": "SGD", "weight_decay": 0.0005, "augment": true, "patience": 10, "seed": 123, "amp": false}`；Epoch `21`。日志、Checkpoint、验证指标及模型SHA仍在原目录和数据库，未归一化覆盖；缺字段不补猜。

## 模型与SHA256

| UUID | 架构 | 状态 | SHA256 | 关联Run |
|---|---|---|---|---|
| 4a1c7df7-dec7-427b-8861-6b247ef3ebbd | yolo11n | EXPERIMENTAL | b878f79dbc83a78267c329671014e853147c26f260eb60691abbc289750a8b9f | 7a01bcad-4b18-4cec-a0f7-1a31f94d6a32 |
| dd2e7eec-2d1a-4840-8df4-4f6112ce805e | yolo26n | CANDIDATE | 277e090da1e4b3f72cb0a874f02e10ab18e116250f1ce6473a080e83af133f84 | 1cc172a1-6d8b-434b-99ab-20e433535ca2 |
| 2814763f-1877-40b4-96e2-bccb396fbb6c | yolo26n | EXPERIMENTAL | d4498ee7934dbe8074f7da637a16c331a13f73586652fd560ff6909f6d92a1b0 | 37aa67d8-3d61-4f37-92ad-7b23cea2bf64 |
| 0d48a0e4-8fef-4ed9-953f-b84f9736976b | rfdetr-nano | EXPERIMENTAL | bc9d31e4457fe18c3306d3f567ff1fc6b0885a4bd3c233c867dcf865da1c52c6 | 75ede84e-4426-4928-9665-14df3f878328 |
| 50de2cc6-6106-4df0-8362-d27761b26728 | rfdetr-nano | EXPERIMENTAL | 639f7f99903cd86c3ce44bd9ee48e238b35e94c185eba925d3032c72d9a9c7ad | f9237c67-8559-475d-b6ca-9ac06bea7121 |

5个权重及其登记ONNX均校验通过。逐文件SHA、完整原始details及所有表在本地before/after.json；不把审计分类写回原数据库。
