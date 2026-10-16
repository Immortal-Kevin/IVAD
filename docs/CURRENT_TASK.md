# 当前任务

2026-10-16 P3 Model Validation + P3.5 Offline AI Video Demo已完成源码与软件功能验收，停止待审。用户仅授权P3.5离线演示，未授权完整P4–P10，PACKAGING_FREEZE=TRUE。

Part A先执行真实P3 GUI检查/现有4a1c7df7完整性/真实CUDA前向/新ONNX导出及ORT CUDA节点验证，PASS后才实现P3.5。3个实际输入均raw/NMS一致，239个ORT计算节点均CUDA，无CPU回退；原PT SHA b878f79dbc83a78267c329671014e853147c26f260eb60691abbc289750a8b9f不变。

新增主程序“离线AI识别演示”：项目视频或复制导入MP4、EXPERIMENTAL模型、NVIDIA/阈值/范围、GPU后台预处理、带框缓存、结果定位、逐帧/播放/暂停/拖动、历史恢复与视频/CSV/JSON/PNG导出。复用解码/PTS/任务/资源锁；GPU环境没有PyAV，采用GUI解码与单帧PNG有界交换，不安装依赖。没有新数据库schema或正式摄像头模型配置写入。

真实0–2秒50帧0预测、7–9秒50帧31预测；缓存阶段2.56–3.13FPS，模型调用5.46–7.23FPS，不含前置GPU检查，不宣称实时。PyTorch峰值分配约66.2MiB，不是GPU总占用。两段均训练来源回放，LIMITED；尚无独立工业识别质量验收。导出截图中有背景区域低置信度预测，必须人工复核，不能把软件PASS当成正确故障识别。

48不同pytest通过、0最终失败，3实际CUDA/PT-ONNX验证PASS；200%首轮11及最终界面1复验通过。保留初始name字段失败/Qt事件错误、测试按钮等待与深色继承问题记录；均已修正复验。历史Qt原生访问冲突/epoch21与20差异保留，单图NMS冷启动警告记录。

真实项目现在有2组训练/模型（包含用户后来生成的1cc172a1/dd2e7eec），全表及1120工件hash0变化，额外256选取文件0变化；原视频、251帧/217标注/720修订/冻结v1/Worker环境保留。所有测试写入独立副本。本轮无新训练、完整P0、依赖安装或应用打包。

交付reports/P3_MODEL_VALIDATION.md、reports/P3_5_OFFLINE_DEMO_ACCEPTANCE.md、docs/P3_5_OFFLINE_AI_DEMO_GUIDE.md；证据artifacts/p35-offline-20261016。无RTSP、PLC、正式报警、规则引擎、多摄像头/多模型生产调度、部署或自动发布，停止等待审阅。


2026-10-16 P3.5 GUI重构：两页/统一视频选择/真实探测/双手柄原片预览/大回放与详情导出，57不同用例及100%/200%复验通过；必要10帧CUDA及schema2精确缓存通过。真实项目全表、1120工件、12历史缓存文件0变化，无schema/Worker/TrainingService/Registry修改，无新训练或打包。PACKAGING_FREEZE=TRUE，P4–P10未授权，停止待审。详见reports/P3_5_DEMO_GUI_HOTFIX.md。
