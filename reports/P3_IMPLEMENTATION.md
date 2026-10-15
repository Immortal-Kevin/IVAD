# P3_IMPLEMENTATION

日期2026-10-15。源码1.0.0-P3-Dev.1，Schema0006。仅P2最终验收/P3；PACKAGING_FREEZE = TRUE。

## 实现

- 同一MainWindow替换P3占位页，新增TrainingPage/ModelsPage，保留P1/P2页面。简易默认20 epochs/640/batch4、SGD/.01/seed123/FP32；高级可调全部授权参数和初始模型，GPU选择来自本会话真实后端检查。没有可用CUDA则拒绝，不提供CPU AI选项。
- ModelAdapter协议与YOLO26n/YOLO11n独立能力声明，保留Intel/非YOLO契约，不重建GUI、任务或GPU环境。
- 复用JobService的p3_train/p3_validate、日志和任务中心；独立Worker+GPU UUID、进程字节锁、取消标志/超时终止。GUI不加载torch/Ultralytics/ORT。
- 训练前复核冻结版本、哈希/尺寸/图片可读性、审核/正常/异常/剔除/冲突、类别/几何、非空train/val及同源/重复泄漏。ROI或整帧异常不伪装检测目标。
- 实验训练/验证工作区不可覆盖；真实loss/指标/显存/曲线/混淆矩阵/环境/权重hash和日志归档；最新进度显示于GUI。OOM中文提示不改CPU，失败不登记成功模型，后续队列继续。
- Registry导入可信PT/ONNX、SHA校验、默认实验、可配置候选指标门槛、人工生产批准、历史指针回滚。状态操作等待刷新，CAS拒绝旧修订，项目内最多一个生产指针。不替换原模型文件，不部署厂区。
- 模型导出经GUI输出PT/ONNX及class map、预/后处理、数据集版本、hash和许可元数据。导入的未知结构不得直接声称训练兼容；独立验证检查实际模型类别映射。
## 数据与打包保护

Schema0006只新增training_runs/model_versions（id、details JSON、revision），0005旧表定义/行不重建，升级先备份。目标项目/任务绑定提交时root；只在独立P3测试项目升级与训练，原用户项目保持0005。训练数据复制到独立工作区，YOLO缓存不写冻结目录；训练前及结束复核冻结清单。

本轮会话保护14102文件，变化0；.venv-p1和.venv-nvidia包版本均一致，无安装/升级，无驱动/全局Python/其他AI项目变更。旧EXE、Beta1/Beta2 ZIP与SHA256SUMS保持。没有执行PyInstaller、EXE/Portable/Setup构建、签名、上传或分发更新；模型PT/ONNX导出是P3模型工件，不含应用程序。

跨日已有数据库/18项工具依赖差异保留在P2的prior-differences-audit.json，未回退人工修订；原库只读integrity ok、外键问题0、最近修订2026-10-14。本轮保护PASS不声称所有历史跨日哈希相同，更不改此前分发事故结论。
## 限制与未验证

- 仅RTX5070Ti 16GB、Windows11、驱动617.42、Python3.12.14、PyTorch2.9.1+cu128/CUDA12.8、Ultralytics8.4.176、ORT1.24.4。Intel XPU/OpenVINO只保留接口，其他RTX/跨机/长期负载NOT TESTED。
- 合成视频、人工测试夹具用于软件流程。未将指定真实录像自动判为堵煤；未训练真实工业生产模型，工业精度、误报/漏报及安全标准NOT TESTED。低mAP不能作工业验收。
- P3不包含时序堵煤判断、离线视频报警、RTSP、AI预标注、反馈学习、TensorRT、部署、Setup。未进入P4–P6。
- 候选默认门槛Precision/Recall/mAP50≥0.5、mAP50-95≥0.25，可由GUI设置并记录。测试夹具明确把门槛设0验证审批链路，不代表工业发布；PRODUCTION仅项目注册状态。
- 普通导入只读取文件/hash，不在GUI反序列化PT。来源可信须明确确认；用户声明架构仍须Worker核验。Detection仅支持YOLO26n/YOLO11n，非YOLO/其他版本需实现适配器，未假称已支持。
- 恢复需同模型和冻结数据集、已保存完整epoch的resume.pt；沿用原参数并另建目录。中途强杀可能丢失当前未完成epoch，GPU失联/OOM不可保证保存新检查点。OOM/进程异常路径通过明确软件故障注入测试，本轮没有再次把GPU占满制造硬件OOM。
- GPU跨进程互斥用Windows字节锁，单GUI串行队列已回归；两台主机/外部ComfyUI等不使用此锁的程序不受调度。本轮没有做两个独立GUI争用同GPU的压力测试。
- 旧原生UI自动化会话访问冲突根因未定位；本轮Qt GUI回归未复现，不宣称长期稳定。数据集的摄像头/原录像分组防泄漏较保守，独立组不足时拒绝训练。
- Ultralytics AGPL-3.0/Enterprise及此前FFmpeg/Qt对应材料/再分发义务仍未闭合，技术验收不代表商业或厂区部署授权。
