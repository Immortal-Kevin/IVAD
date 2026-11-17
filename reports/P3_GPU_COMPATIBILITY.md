# P3_GPU_COMPATIBILITY

日期2026-10-15。源码1.0.0-P3-Dev.1，Schema0006。仅P2最终验收/P3；PACKAGING_FREEZE = TRUE。

## 实际CUDA训练

经现有GUI配置/按钮提交JobService，由独立.venv-nvidia进程训练。两模型均2 epochs、160×160、batch1、SGD、lr0=.01、seed123、FP32，train2/val2/test2（3个媒体UUID来源组；自制同场景的容器变体，不是工业独立场景）；此对照全部为目标测试夹具。CUDA前向守卫禁止CPU神经网络，记录真实CUDA梯度/权重更新、重载。后处理与文件操作可用CPU。

| 模型 | 优化器更新 | Worker秒（含启动/训练/验证，导出前计时） | Precision | Recall | mAP50 | mAP50-95 | ONNX形状 / 最大绝对差 / NMS数 |
|---|---:|---:|---:|---:|---:|---:|---|
| yolo26n | 4 | 36.18 | 0.004819 | 1.000000 | 0.005279 | 0.002243 | [1, 5, 525] / 0.000488281 / NMS 1 |
| yolo11n | 4 | 36.85 | 0.007194 | 1.000000 | 0.745000 | 0.114300 | [1, 5, 525] / 0.000656128 / NMS 0 |

独立正常负样本测试：YOLO26n同2 epochs，train/val/test各1目标+1正常空标签，CUDA与权重更新/ORT对齐PASS，4次更新。准确率只是合成测试结果，见negative-final/yolo26n下job和run/results.csv。

AMP训练运行中取消后，完整检查点恢复：从epoch索引1继续至原计划10 epochs，新增优化器更新18次，CUDA梯度/参数/权重变化/重载PASS；原检查点hash不变。恢复/验证/GUI审批详见lifecycle-accepted-result.json。训练曲线、混淆矩阵、train/val loss和epoch指标真实保存在各run/results.csv、results.png、confusion_matrix.png。显存为PyTorch allocator采样/峰值，不等于整卡所有进程独占峰值。

所有ONNX为各自模型raw non-end2end + NMS、FP32、batch1、opset17；原始张量allclose rtol=.005/atol=.05，最终检测rtol=.005/atol=.1。输出结构显式验证4+nc通道；ORT profile实际节点仅CUDAExecutionProvider，关闭CPU EP fallback。YOLO26原生端到端输出未验收。
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

补充限制：本轮YOLO11n随机输入在conf=.25时NMS为空，已比较空结果与原始张量；不把该例当作非空最终检测的单独证明。近似重复场景仍需人工复核，本轮不声称用合成组验证了工业泛化。
