# Ultralytics 隔离与来源审计

日期：2026-10-16。原 HEAD `48f912734ecafa972b90c41d11b816100c962b73`；分支 `feature/p36-rfdetr-evaluation`。原工作区干净。

## 审计口径

本次读取实际 imports、调用、权重路径、导出和 Git 历史，不以文件名推定来源。Git 中首次提交只证明项目历史，不能单独证明独立著作权或不存在复制。A/B 为工程结构分类，不是产权认证；无法确认的实现列 E。未进行对全部第三方历史源码的相似度鉴定。

| 分类 | 模块/资产 | 实际关系及处理 |
|---|---|---|
| A（产权仍待确认） | 项目/摄像头管理、数据库、媒体导入、人工标注 GUI、任务队列 | 算法无关业务。正式模块本轮不修改、不引入实验流程 |
| B | 冻结 manifest 的像素 xywh、类别 UUID、时间和来源字段；通用 xyxy/confidence/class 输出 | 数据与公共交换契约独立使用；新转换器自行校验，不调用 YOLO exporter |
| B/C 分开 | `compute/model_adapters.py` | Protocol/能力字段属于通用接口；当前实际实现/ADAPTERS 仅 YOLO，实验不导入或注册它 |
| C | `compute/train_worker.py` | 导入 YOLO/settings/DetectionTrainer/non_max_suppression，继承训练器、回调、恢复、导出和 NMS 都绑定 Ultralytics；保持历史模块，不复用 |
| C | `compute/offline_worker.py` | YOLO 加载与 model.predict；新 NanoAdapter 完全独立 |
| C（间接） | `services/training_service.py`、`offline_demo_service.py`、`core/application.py` | 启动旧 Worker，默认 `.venv-nvidia`；正式 GUI 仍经这些服务运行。没有完成正式产品替换 |
| C（算法资产） | YOLO11n/YOLO26n 初始 PT、3 个历史 ModelVersion 的权重、历史 ONNX/检测缓存 | 均保留原许可与来源，禁止作为 RF 初始化或伪标签。RF 实验不读取这些模型 |
| C（测试） | 旧 P0/P3/P3.5 GPU 测试与导出脚本 | 含 Ultralytics 调用；完整匹配证据保存在本轮 artifacts；不拿旧测试成功冒充 RF 成功 |
| D（风险点） | train_worker 中训练器继承、恢复 save_dir 调整及非公开训练器接入 | API 集成已确认；是否存在复制/改写受保护实现不能由继承关系直接判断。迁移时独立重写流程，不移植旧代码 |
| E | 原有算法相关适配和测试的独立来源、所有权链 | Git 可追溯至 `275de69`、`77b3225` 等，但缺少完整开发/引用声明与逐段来源材料。待公司确认；不作“全自研”断言 |

搜索原始证据：`artifacts/p36-rfdetr-20261016/ultralytics-references.txt`、`service-boundaries.txt`、`provenance-git.txt`。这些记录包含真实路径与行号。

## 本轮隔离边界

新增代码仅在 `experiments/p36_rfdetr`；独立 `.venv-rfdetr`、独立 COCO 副本、实验权重与日志。启动使用该环境 Python `-I -X utf8`，不导入 `ApplicationServices`、旧 worker 或 Ultralytics NMS；用官方 RF-DETR API 和自身契约校验。`assert_isolated()` 在环境可找到 Ultralytics 或已有该模块加载时拒绝运行。

旧 `.venv-nvidia`、`.venv-p1`、GUI、服务和模型仓库均不删除、不替换。实验结果不会写入正式 Registry。正式软件尚有 AGPL 依赖，完整迁移未完成；新独立依赖实际检查结果见可行性报告及依赖通知清单。

## 后续正式迁移需批准的工作

独立训练/推理 Worker 路由、后端能力与模型元数据、非 YOLO 输出处理、P3.5 缓存版本/身份、取消与 GPU 调度、全链路回归及 C/D/E 来源复核。不能仅改 import、换权重或使用旧 YOLO ONNX 宣称授权问题消失。
## 2026-10-19 收尾补充

本补充替代上文“正式GUI仍可启动旧训练”的当前状态描述，历史审计原文保留。

正式GUI→training_router→RFDETRTrainingService→.venv-rfdetr -I→独立RF Worker。旧路由封禁，业务查询隐藏3旧训练/3旧模型；旧模型register/transition/configure_camera/record_validation拒绝，verify和文件复制导出仍可只读审计。P3.5新任务在JobService和OfflineDemoService双重拒绝，历史成品缓存可读。

本轮当前代码真实CUDA重载Job `8da15e9d-d101-482f-a529-d3a689bbb5cf`成功；主进程装配使用禁止Ultralytics导入的Finder，Worker保留其模块轨迹；旧PYTHONPATH污染探针通过。原始旧环境、YOLO权重、源码、通知和构建清单仍保留，不能声称全产品零依赖或版权链全部闭合。详细逐文件分类见 `reports/P37_LEGACY_YOLO_RETIREMENT.md`。

本轮未改依赖版本，不重新出具法律认证。沿用固定版本的P37_FREE_PROPRIETARY_LICENSE_AUDIT中未闭合项：Qt对应源码和可替换实测；FFmpeg/PyAV构建/codec对应；OpenCV捆绑视频库；NVIDIA逐DLL可分发清单/通知；部分包缺失通知、产权来源及最终payload审查。公司专有源码策略保持，未购买许可。`DISTRIBUTION_STATUS=BLOCKED`，`PACKAGING_FREEZE=TRUE`。
