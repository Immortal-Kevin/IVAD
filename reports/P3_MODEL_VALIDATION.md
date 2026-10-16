# P3 模型验收

日期：2026-10-16。Part A先完成训练GUI与模型/CUDA/ONNX验证PASS，随后才开发P3.5。没有重训YOLO11n，没有安装依赖或修改驱动/全局Python。

## 真实GUI

在真实项目独立副本上启动Windows Qt主程序，执行简易/高级切换、参数编辑、17个参数/按钮Tooltip事件（含禁用控件）、AMP支持状态与配置值、5按钮同行、Dataset/Version匹配、实际NVIDIA后端、历史7a01bcad任务、真实指标/原参数、训练日志存在性及诊断日志页面。完整配置预检真实通过。未点击启动新真实训练；事件防误操作另由隔离回归验证。

证据：artifacts/p35-offline-20261016/gui-a/p3-training-actual.png、diagnostic-logs.png、p3-gui-results.json、gui-a.xml。GUI验收1项综合用例PASS。历史epoch=21/epochs=20、actual_epochs=20的不一致原样保留，属于既有进度显示限制，未伪造修正。

## 模型及冻结引用

- 模型4a1c7df7-dec7-427b-8861-6b247ef3ebbd，YOLO11n Detection，EXPERIMENTAL。
- PT原文件SHA256：b878f79dbc83a78267c329671014e853147c26f260eb60691abbc289750a8b9f。
- Dataset 8525test1 v1：fd9a3ba2-ed9b-4698-8838-5002b036fef0，200张、LIMITED。
- 版本清单哈希及class_map与ModelRegistry逐项一致；类别沿用实际名称“压滤版破裂”。原始PT/历史ONNX存在且通过登记SHA256，不修改注册指针或指标。

## 实际CUDA和新ONNX

使用现有.venv-nvidia，torch2.9.1+cu128/CUDA12.8、RTX5070Ti。原PT只读，复制到新的验证目录后重新导出ONNX（opset17，FP32，640×640，原始[1,5,8400]输出+NMS）。onnx.checker及文件SHA256通过，不覆盖旧模型ONNX。

CUDA输入张量、CUDA参数、实际module forward及GPU输出证据；ORT禁止CPU EP回退，使用CUDA IO binding输入/输出，采集真实profile，三个输入每次239个计算节点均CUDAExecutionProvider。不是只看Provider名称。

| 输入 | 原始输出最大绝对差 | NMS结果 |
|---|---:|---|
| 冻结版本首张真实图 | 0.0023651123 | PT/ONNX均为空 |
| 既有异常标注时间的真实图 | 0.0014038086 | PT/ONNX均为空，不按人工标签强造预测 |
| 视频实际产生预测的7.6秒画面 | 0.0014343262 | 置信度阈值0.10，双方1框一致；置信度0.2747697 |

rtol=0.005、raw atol=0.05，NMS atol=0.1。最后一框还映射回1280×720原图坐标[726.6067,112.4589,790.9424,240.1948]，类别0，坐标/置信度有效。

三组纯PT CUDA张量前向约12.99–15.32ms（65.26–77.01 FPS），不含视频解码、图像预处理、NMS、传输、绘制或编码，不能当作视频播放实时FPS。PyTorch峰值分配120257536字节（约114.7MiB），不含CUDA上下文及ORT/驱动分配，不等于GPU总显存占用。第三组出现一次NMS冷启动时间限制警告；单图输出已生成并数值比较通过，未因此宣称长批次或实时稳定性。

完整原始结果、ORT profile、新ONNX/PT副本及SHA：gpu-validation/、gpu-validation-positive/、gpu-validation-detections/位于artifacts/p35-offline-20261016/。第三组新ONNX SHA256：8addaf5815d0b38439e6fe43518aa30afb1f81897d439ec3bda9bdcc6065d186。不同导出带独立元数据，按各自数值与哈希验证，不要求和旧ONNX字节一致。

## 保护与结论

起始盘点发现用户另有1cc172a1训练/dd2e7eec模型，也一并保护；原项目当前2训练、2模型、1冻结版本、251帧、217标注、720修订。前后全表0变化，1120个模型/数据集/训练工件及清单哈希0变化，额外256个选取帧/原视频/环境文件0变化。SQLite只读在线备份与对比见before/、after/、protection-results.json。

Part A模型完整性、实际GPU推理和导出一致性PASS；不代表独立工业准确率通过。真实回放截图中出现背景墙/门窗附近的低置信度框（约0.274），尚未经人工确认，必须复核预测及训练标注；不能将软件验收写成故障识别质量PASS。P3.5准入成立。PACKAGING_FREEZE=TRUE，无EXE/Portable/Setup，无P4开发。
