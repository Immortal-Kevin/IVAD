# P3.6 RF-DETR Nano 隔离与迁移可行性

日期：2026-10-16。工程评估，**不是正式迁移、工业验收或软件发行批准**。

## 1. 分支、边界与结论

原 HEAD：`48f912734ecafa972b90c41d11b816100c962b73`，原分支 nvidia-first，开始时工作区干净。新分支：`feature/p36-rfdetr-evaluation`。

25个新增源码/许可/报告文件已暂存，`git diff --cached --check`通过。尝试本地提交时Git因未配置作者身份拒绝创建Commit；没有擅自设置作者或全局Git配置，当前HEAD仍为原Commit，修改保留在上述新分支的暂存区。原始许可/NOTICE通过局部.gitattributes关闭换行转换，Git索引中的原文字节已核对一致。

仅新增独立实验代码、法律审计材料和本报告；正式 GUI、旧训练/推理服务、数据库 schema 与 Registry 均未替换。只测试 Nano Detection，未安装 Plus，未下载 Small/XL/2XL，未重复 YOLO 训练或完整 P0。`PACKAGING_FREEZE=TRUE`。

Nano 已在本机实际 CUDA 微调与重载推理，可继续评估替代方案；**整个 IVAD 尚未完成 Ultralytics 去依赖，不能作为可分发闭源版交付**。

| 验收项 | 状态 | 依据/边界 |
|---|---|---|
| License Audit | PARTIAL | Nano 包/指定权重 Apache 依据已核对；完整产权、捆绑原生库与部分依赖发行材料待确认 |
| Ultralytics Isolation | PARTIAL | 新实验环境/入口不含 Ultralytics/Plus/旧 venv；正式产品仍调用 YOLO，C/D/E 来源问题未自动解决 |
| RF-DETR Installation | PASS | 独立 .venv-rfdetr，pip check 无冲突，96 包快照与 95 个运行归档哈希 |
| GPU Training | PASS | 1 epoch 短训与修正种子后的完整 12 epoch 工程实验，480 次实际 CUDA 更新 |
| GPU Inference | PASS | 官方预训练图、最佳权重40张验证图、正常/异常双图批量及真实录像30帧执行；非工业质量结论 |
| Model Export | PASS | 固定尺寸 ONNX checker、实际717个CUDA节点及同输入PT原始输出比较通过 |
| IVAD Adapter Compatibility | PARTIAL | 独立原型与实际预测契约通过；正式服务、Registry、缓存、调度尚未接入 |
| Dataset Compatibility | PASS | 200 图/402 框独立 COCO 副本，原划分与 16 张正常负样本保留；质量仍 LIMITED |

## 2. Ultralytics 实际依赖与隔离

`compute/train_worker.py` 直接使用 YOLO/settings、DetectionTrainer 和 Ultralytics NMS；`compute/offline_worker.py` 直接加载 YOLO。TrainingService、OfflineDemoService 和 ApplicationServices 经旧 Worker 间接依赖，正式 GUI 仍使用这一链路。旧权重、ONNX 和检测缓存不是 RF 初始化/预测来源。

新增 `experiments/p36_rfdetr` 通过自己的 NanoAdapter、COCO 转换和结果验证运行；不 import ApplicationServices/旧 Worker/旧 exporter/NMS。`-I` 独立 Python 的检查确认没有旧 venv 导入路径、Ultralytics 或 rfdetr_plus。旧环境/资产保持原位，不把“独立进程”当成整个产品法律问题的解决方案。

A/B/C/D/E 分类、实际文件和未确认产权见 `legal/ULTRALYTICS_ISOLATION_AUDIT.md`。Git 首次提交只证明开发历史，不能单独证明全部代码独立来源。旧算法接入点必须独立替代或经适用授权处理，不能简单改名或使用旧 YOLO ONNX。

## 3. 官方版本、权重与许可

- 官方仓库：https://github.com/roboflow/rf-detr 。固定 tag `1.11.2`，Commit `7433d5919d0f7e72cc6cb78663e0a731afd499e0`。
- 实际包：rfdetr **1.11.2**；wheel SHA256 `2f23589567123b59302f1cfa9d14d23630f9f583ee6f3468c5891e33fb103b2a`，与 PyPI 发布摘要一致。
- wheel 中 LICENSE 和权重地址表与上述固定 Commit 的文件逐字节一致。不是只参考 develop 分支说明。
- 该版本 README 明确开源包与标为 Apache 的权重采用 Apache-2.0，模型表中 Nano Detection 标为 Apache；Plus 使用另一许可。官方说明：https://roboflow.com/licensing 。
- Nano 权重：https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth 。文件 366,287,238 bytes；MD5 `fb6504cce7fbdc783f7a46991f07639f` 与包内发布值匹配；SHA256 **`d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d`**。
- 未用任何 YOLO 权重、ONNX 或伪标签初始化。

Apache 官方完整原文 `legal/licenses/Apache-2.0.txt` 来自 https://www.apache.org/licenses/LICENSE-2.0.txt ，11,358 bytes，SHA256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`。Roboflow 版权版 LICENSE 单独原样保存。没有修改根 LICENSE、版权头或批准项目开源。

## 4. 环境与可复现输入

独立 `.venv-rfdetr`，CPython 3.12.14，Windows 11；RTX 5070 Ti 16GB，Driver 617.42，Compute Capability 12.0，PyTorch 2.9.1+cu128 / TorchVision 0.24.1+cu128，CUDA Runtime 12.8。nvidia-smi 总显存 16,303 MiB；torch 设备属性为 17,066,033,152 bytes，两种 API 口径分别保留。

从既有可信 wheel 缓存安装到新 venv，没有复制/引用旧 site-packages，没有升级旧环境。RF-DETR 1.11.2、Transformers 5.20.0、Lightning 2.6.6、Supervision 0.30.9、ONNX 1.20.1、ORT-GPU 1.24.4 等实际版本见锁文件与完整依赖索引。

`pip check`：No broken requirements found。96 个安装包（含 pip），154 份原始许可证/通知副本；95 个运行依赖记录版本、下载来源与 SHA256，见 `experiments/p36_rfdetr/requirements.lock.txt`。安装日志、pip --report、环境元数据、原生 DLL 清单保存在本轮 artifacts。锁定的是 Windows CPython3.12 amd64 实验，不是安装包批准。

训练请求完整保存 batch/lr/seed/AMP/EMA/增广/评估等配置。种子 **20261016** 在模型构造前及训练配置中设置；没有开启全部确定性算法，也没有重复完整训练验证逐位一致性，因此不承诺不同机器/驱动上逐位重现。

首次训练脚本导入 Matplotlib 时产生字体缓存提示；后续训练显式使用本轮 MPLCONFIGDIR/HF_HOME。没有改系统 Python、驱动、全局 CUDA、ComfyUI 或旧 YOLO 环境。

## 5. 数据副本与来源

原项目：`E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2`。冻结数据：8525test1 v1，Version UUID `fd9a3ba2-ed9b-4698-8838-5002b036fef0`。

冻结 manifest SHA256 `5eecfe2509b89dd67ec0ecf6280654607f036599099d538d305e27c27798a8ac`。从 manifest 中自有人工标注的原像素 xywh 独立生成 COCO，不从 YOLO 文本标签或模型预测还原。

| 划分 | 图片 | 目标框 | 正常无框 |
|---|---:|---:|---:|
| train | 160 | 331 | 13 |
| valid（原 val） | 40 | 71 | 3 |
| test | 0 | 0 | 0 |
| 合计 | 200 | 402 | 16 |

实际类别原名 **“压滤版破裂”**、ID0、UUID `63b964c3-88d8-45ad-9bbd-a93487582d4d`，未私自改成另一字形。Camera UUID `6cfade53-2a3d-4a78-b27b-415b567ab60d`，来源媒体 `12a11464-0581-4bf1-8977-47fbcd5364b7`。

200 张副本均验证文件 SHA256、真实可解码尺寸（1280×720）与来源；402 个对象均为人工矩形框，坐标/类别有效。转换器拒绝非人工、未知/冲突、越界真值和未经复核的 polygon->bbox，不把正常图丢弃。完整原始 sample 字段、时间、来源与人工修订信息保留于副本 provenance.json。

未重新划分。仅 **1 个来源组**，跨 train/val 最近帧相隔 **0.2 秒**，仍存在同源/近重复泄漏，**LIMITED**。没有独立工业 Test，不以验证集分数表示跨日期/摄像头泛化。

## 6. 训练与取消

1 epoch 短训：40 次 CUDA 前向、40 次优化更新、CUDA 梯度及实际权重变化通过；耗时 58.325s，分配显存峰值 2,170,979,840 bytes，已保存检查点。

早期 12 epoch 尝试发现构造前随机种子未明确设置，运行至早期后请求安全取消；保留整个 engineering-run、日志与 483,159,552-byte cancelled.ckpt，没有把它当成功结果。另测启动后立即取消，无模型加载/假成功。最终采用构造前设种子的独立新目录重跑完整计划。

正式工程实验：**12/12 epochs，batch4，累积1，384×384，lr1e-4，encoder lr1.5e-4，BF16 AMP，EMA开启，workers0，固定输入尺度，关闭多尺度/scale jitter，原160/40/0划分**。480 次真实 CUDA 前向/梯度更新，耗时 **190.751s**。分配显存峰值 **2,296,032,768 bytes（2.138 GiB）**，保留峰值 **2,464,153,600 bytes（2.295 GiB）**；这些是 PyTorch 分配器统计，不等于整卡进程/桌面总显存峰值。

Windows 匹配器提示 Triton 不可用，匈牙利匹配使用 SciPy CPU；解码、数据处理和 COCO 指标也在 CPU。神经网络参数、前向与反向实际在 CUDA，未采用 CPU-only 模型训练/推理冒充成功。

最佳 EMA 出现在第7个 epoch。训练日志口径：P=1.0000、R=0.929577（F1 sweep 选择点），mAP50=0.964795，mAP50–95=0.479388（maxDets500）。保存的最佳权重为 `engineering-seeded-run/checkpoint_best_total.pth`，120,896,611 bytes，SHA256 **`2d5940c25447b5be8d94180635f815feb16cbbfd645e699e32e7548e8d6b8f5f`**。另保留 best EMA、last EMA、epoch 检查点与 training_config.json。

12 个 epoch 的真实 loss/指标在 metrics.csv、training-summary.json 和 training-curves.png/svg。未计算验证 loss（官方 compute_val_loss=auto 未启用），没有编造对应曲线。断点续训与跨机器确定性未实际验证。

## 7. 最佳权重重载与独立指标

最佳权重实际 CUDA 重载，类别映射与冻结类别一致。40 张验证图逐张推理，并选择一张真实正常样本和一张有框样本进行双图批量推理，结果数量/坐标/置信度/类别与来源契约检查通过。双图测试中正常图无框，有框图产生1个真实预测，置信度约0.4774；这不是人工审核或工业真值确认。

独立 pycocotools 评估（预测 cutoff .001、maxDets100）得到：**mAP50 0.959234，mAP50–95 0.465326**。在 confidence .25 / 同类 IoU .5 贪心匹配下，**TP68 / FP6 / FN3，Precision0.918919，Recall0.957746**，GT 共71框。

独立重载评估与训练内 EMA 指标存在差异；评估入口/后处理/阈值/maxDets与数值精度口径不同。本轮未完成同配置逐张归因，**不把训练内较高值与重载结果混为一个成绩，不据此宣称优于 YOLO**。正式迁移前应统一评估路径并复核差异。

最初结果转换器将低阈值下的零高度候选视为整批错误；已改为记录并排除零面积预测，保留原始坐标，对有效框裁至图像边界，不修改真值。显式背景槽可排除，未知真实类别、非有限值和反向坐标仍报错。此前失败日志和目录均保留。没有制造预测框/置信度或用人工标签替代预测。

## 8. 性能与视频流水线

官方 README 示例图 https://media.roboflow.com/dog.jpg 的 Nano 预训练推理通过，真实输出包括 dog/person 等；不能要求 COCO 初始模型直接识别工业故障。该测试图仅本机验证，未作为发行素材。

FP32、未做 inference 优化、batch1、384×384、预热5次：

| 测项 | 实际结果 | 范围 |
|---|---:|---|
| Adapter 加载 | 31.037s | 包含首次 RF 导入/哈希检查/构造及权重加载，不是纯磁盘读权重时间 |
| GPU 前向 p50 / p95 | 7.856 / 21.019 ms | CUDA Event；30次计时加1次空结果控制前向，31个样本 |
| 纯模型平均 FPS | 97.839 | GPU 前向均值的倒数，不含预处理/解码 |
| 图片流水线 p50 / p95 | 12.990 / 28.818 ms | 30次，已解码 PIL RGB -> 预处理 -> CUDA -> 后处理/CPU输出 |
| 图片流水线 FPS | 63.505 | 不含录像解码、GUI、显示与落盘 |
| 推理分配/保留显存峰值 | 176,425,472 / 195,035,136 bytes | torch allocator；不是整卡使用量 |
| 进程 RSS | 2,512,502,784 bytes | 该时点 CPU 内存，不是全过程峰值 |

8525 原录像为25fps、1280×720、70.04s，time_base=1/90000，start_pts=4701769000。以当前媒体起始PTS为基准换算视频相对时间，未把52,241秒误作视频内时间。首轮真实录像30帧流水线约44.822 FPS，p50/p95=18.550/37.458ms。

补齐唯一权重SHA256、raw_pts与time_base后的复验：**46.116 FPS，p50 19.370ms / p95 33.346ms**（`video-probe-identity/video-result.json`）。包含连续PyAV解码、PIL转换、CUDA预测、后处理和JSON序列化，不含加载、预热、GUI渲染和文件写出。首帧作预热，实测视频相对区间约0.04–1.20秒；**仅30帧，未跑完整70秒录像，不在严格隔离系统负载下测量，不能承诺GUI端25/30 FPS**。未持久化为数据库Frame的解码帧，其frame_id为null，来源由Media UUID/raw_pts/时间基追溯；验证图结果则保留真实Frame UUID。

## 9. ONNX 导出与重载

官方 RF-DETR exporter 已生成固定 batch1/384×384 的 FP32 ONNX。Torch tracing 的静态形状警告保留；不宣称支持任意动态尺寸/批量。

ONNX 为107,641,169 bytes，SHA256 **`d006d7765f704d41857d9af38469578887491619e1aad6e26eb752bc7a3d9a1a`**。checker PASS；实际profile记录 **717个CUDA执行节点，执行Provider集合仅CUDAExecutionProvider**，CPU fallback被显式禁用。输入[1,3,384,384]，输出[1,300,4]与[1,300,2]。

同一CUDA随机输入的PT/ONNX原始张量比较PASS，框最大绝对差 **5.5611e-5**，logits最大绝对差 **2.7657e-5**（rtol .005 / atol .02）。证据 `onnx-export/export-result.json` 与 ort-profile；不是仅凭Provider名称宣称成功。未测试动态尺寸、量化、TensorRT或完整ONNX视频后处理部署。

## 10. IVAD 最小接口与正式接入差距

独立 Adapter 覆盖模型身份/加载/恢复/显式GPU、COCO验证、训练子进程启动与状态、取消、检查点、图片/批量推理、结果转换、导出和日志。真实输出保留 Frame/Camera/Media UUID、视频相对 time_us、类别、confidence、原像素 xyxy、原始坐标与权重 SHA256 身份。

这些语义可映射到 IVAD 通用检测结果；独立缓存使用 `ivad-rfdetr-experimental-v1`，不冒充旧缓存。原 P3.5 schema2 身份含 `p35-pil-rgb-ultralytics-v1`、imgsz640/Ultralytics NMS、Worker/服务/环境哈希，不能直接复用。RF-DETR 不是 YOLO 输出格式，不能复用旧 raw tensor 解码/NMS。

Registry 目前 details JSON 可容纳通用元数据，但服务准入仍限 YOLO。单摄像头多故障、追加图片训练、新版本、实验/候选/生产/回滚在设计上可支持；**本轮没有向正式数据库注册、实现这些产品状态或发布生产模型**。GPU跨后端队列/互斥、完整断点恢复、缓存落盘/回放和正式 GUI 路由仍待实现/验证。

## 11. P4 兼容评估

通用时间、来源、类别、置信度和坐标可供未来 ROI/连续帧/持续时间规则消费；RTSP、多模型调度、丢帧/时钟、工业报警和证据存档还需要独立设计、实现与现场验收。本轮没有实现完整 P4 或生产报警接口。

## 12. 许可证交付与未决项

已生成 LICENSE_POLICY、官方 Apache 全文、THIRD_PARTY_NOTICES、ULTRALYTICS_ISOLATION_AUDIT、专有声明草案，另有96包依赖索引及原文证据。草案未认定权利主体，不修改根许可/版权头。

Nano 的 Apache 依据明确，**新 Python 依赖检查没有发现 Ultralytics/Plus**；但不能据此保证所有原生捆绑或来源未明代码完全无约束。旧正式系统仍含 AGPL 路径。C/D/E 源码来源、Qt LGPL材料/重链接、PyAV/OpenCV各自FFmpeg构建、NVIDIA许可文件清单等仍需核实。

RF 环境 PyAV19.0.1 的 avcodec63.1.102 报 LGPLv3+，配置同时含 x264/x265；与旧 GUI avcodec61 分开留档，构建/下游授权未确认。部分 wheel 无完整通知文件，已从确切版本 sdist 补采 ONNXsim/Tokenizers，其他缺项如实记录。没有购买许可证、删声明或改变开源状态。

网络方面：COCO 测试图 HTTPS 主机证书不匹配，已留错误后改用官方 RF 示例；FlatBuffers 候选官方 tag URL 404，已留档。未关闭 TLS、修改代理/VPN或系统设置。

## 13. 历史保护与测试限制

真实项目前后只读比较PASS：251帧、217标注、720修订、3摄像头、8媒体、3训练、3模型、1冻结数据集版本，**全部表内容相同，1,578个历史训练/模型/数据集/配置文件哈希零变化**。251张原始抽帧逐一匹配数据库登记SHA256，200个实验成员当前均LABELED且没有is_excluded/CONFLICT。原8525录像SHA256 `8571e8b37fee5456c39d25523a90eb95b686fa69dbbd9c95cab196ad14c856a9`匹配；3个旧环境共97项解释器/配置/包元数据保护检查通过。证据 protection-result-verified.json。

6个独立边界测试通过，覆盖空/多类别、非法预测、边界裁剪保留原坐标、背景与未知类区分、零面积，以及非法真值/哈希错误/polygon拒绝。真实工业数据不因夹具测试而被自动审核。本轮未运行大型 GUI 回归，正式业务源码保持未修改；不将其表述为重新验证所有 P0–P3.5 功能。

## 14. 迁移建议、工作量与停止

建议下一轮在用户批准后做受控正式接入，先统一重载评估口径并处理来源/许可缺项，不直接替换生产引擎。粗估开发工作：独立 Worker/能力路由2–3人日，Registry/训练GUI与版本元数据1–2人日，P3.5预处理/缓存/导出1–2人日，取消/调度/集成与针对性回归2–4人日，共约 **6–11开发人日**；为工程估算，源码来源、法律审查和现场独立数据验证另计，不能作为交付日期承诺。

未做同条件 YOLO 对照，不比较厂商 T4/TensorRT 宣传值与本机 FP32 数字；未重复历史训练。仍需不同日期、正常/故障独立录像验证，现有 LIMITED 数据不能给出工业泛化准确率。

本轮结束后停止，等待用户明确批准才能接入正式 P3/P3.5。保留旧环境/权重/全部历史记录；不启用生产推理、不进入P4、不生成EXE/Portable/Setup、不发布软件。

### 主要证据目录

`artifacts/p36-rfdetr-20261016`：before/after、coco/provenance.json、weights/download.json、sources、dependency-audit、安装reports与日志、isolation-check.json、short-run、engineering-run（取消）、engineering-seeded-run、training-summary.json、training-curves、pretrained-probe-final、best-evaluation-verified、onnx-export、video-probe及video-probe-identity、contract-tests-final.log、protection-result-verified.json、final-validation.json。
