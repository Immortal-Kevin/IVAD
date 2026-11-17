# RF-DETR Nano 离线演示候选验收

2026-10-19。独立演示模块 `demo_rf/`；原生产P2/P3代码、Git历史、环境及数据库未修改。基线HEAD仍为1204369ff65d9c7f969406916108fbfe366475bb。本轮不重新训练、不开发P3.7-B/P4、不上传或发送。使用computer-use技能完成Windows窗口操作。

## 实际产物

- EXE：`E:\IVAD Project\IVAD_Platform_v1.0_NVIDIA_Primary\dist\IVAD_RF_Demo_Candidate\IVAD_RF_Demo.exe`。
- 完整目录：5,204,300,436字节，5258文件。onedir，含独立worker、Qt、视频和CUDA运行文件；必须保留整目录。
- GUI EXE SHA256：`648b5295d1fcf2221a8ff15ca6dfd5fe8116f409fca523fdb7c8293a8632d9d4`。
- Worker EXE SHA256：`75f47a82824c72866927191fc8ad958bb2c90b4117d2775228e0e7dd9ff98543`。
- 打包权重SHA256：`cdaa15e7225daf5cca80788b4ab072afde519a164f4678a4e58ccb1095547027`；120780883字节。
- 原权重SHA256：`bc9d31e4457fe18c3306d3f567ff1fc6b0885a4bd3c233c867dcf865da1c52c6`，未修改。只导出466个完全相同的推理张量和最小模型信息，去除优化器、训练路径等元数据，无重新训练。
- 手册：`E:\IVAD Project\IVAD_Platform_v1.0_NVIDIA_Primary\dist\IVAD_RF_Demo_Candidate\IVAD_RF_Demo_操作手册.md`。逐文件哈希见候选目录SHA256SUMS.txt及artifacts/rf-demo-20261019/final-payload-manifest.json。

## 实测结果和边界

| 项目 | 结果 / 证据（均位于artifacts/rf-demo-20261019） |
|---|---|
| 授权Nano真实加载/单帧CUDA | PASS；frozen-ready-single.jsonl；cuda:0、eval、禁用梯度、真实forward钩子；无CPU AI回退 |
| 最终EXE视频与绘框 | PASS；frozen-final-success.json、final-exe-results.json；H.264合成MP4读取40帧、实际CUDA推理2帧，绘制10个真实低分框；原图320×180、原PTS、类别及置信度显示 |
| 最终EXE结果保存 | PASS；通过Windows原生保存框；运行阈值0，完成后UI改为0.9，JSON仍记录实际阈值0；final-exe-validation.json |
| 更密集视频、源/冻结结果坐标一致 | PASS；此前相同worker运行8帧/53框，frozen-coordinate-parity.json；不是现场准确率 |
| 暂停、继续、取消 | PASS；frozen-pause-start/stable.json、frozen-cancel-final.json；暂停274帧计数不变，继续后增加，取消worker退出。最终GUI仅修正图像收集、保存参数归属和诊断长度；未重跑整套长视频 |
| 空结果、VFR、320输入 | PASS（开发机）；frozen-final-vfr-320-empty.json；40帧解码/2帧CUDA、0框，真实PTS、明确空结果。320不是3050Ti实测 |
| CSV | PASS（导出定向测试）；csv-export-test.csv，53对象行；最终EXE实测保存JSON，未冒称又测CSV原生对话框 |
| 无CUDA拒绝 | PASS；no-cuda.json；CUDA_VISIBLE_DEVICES=-1时明确拒绝、无CPU AI回退 |
| 不依赖开发Python | 在开发机清除PYTHONHOME/PYTHONPATH/VIRTUAL_ENV/Qt路径、PATH仅System32后运行冻结GUI及worker；实际DLL映射无开发venv/Codex运行时路径，frozen-loaded-dlls.json。未等同干净目标机验收 |
| 正常退出 | 最终EXE正常Alt+F4退出，无遗留GUI/worker进程 |
| RTX3050Ti Laptop 4GB / 王波电脑 | NOT TESTED；需实际机器驱动/GPU检查、授权模型加载和短视频试验；不能以5070Ti或Torch分配峰值证明4GB可用。OOM处理已实现，未声称真实4GB OOM测试通过 |
| Qt历史异常 | PARTIAL；本轮未复现，原始根因仍未确定；IVAD-QT-001原证据与后续触发条件不变 |

实际开发机：RTX5070Ti，驱动617.42，Torch2.9.1+cu128/CUDA12.8。GUI视频解码可用CPU；神经网络仅CUDA。GUI/worker独立进程，逐帧背压，不将未推理帧计为已检测；无模型自动下载，拒绝网络连接。最终冻结检查暴露过Pillow隐藏导入遗漏，原失败证据frozen-final-pil-failure.json保留；补收集PIL.Image及完整GUI运行目录后最终真实推理通过，不改写失败记录。

## 模型与保密

仅包含用户授权的P3.7-A实验Nano推理权重，不含8525test1 v1数据集、真实视频、图像、标注数据库、历史YOLO权重或业务项目。模型界面和手册标注“实验模型 / 尚未经过现场验证”。200图、402目标、16正常负样本，无独立测试集；合成视频阈值0只用于验证框显示，不代表淖尔壕检测准确率。仅王波在金海泽地受控电脑展示，不交厂方副本。

## 增量许可证结果

只针对实际候选载荷补材料：RF-DETR Apache-2.0及上游署名、Torch/torchvision复合LICENSE/NOTICE、实际Python包原通知、两份缺失的pycocotools/tokenizers官方免费许可；保留Qt/PySide/Shiboken源码归档及可替换动态布局。23个实际NVIDIA DLL按SHA映射现有CUDA/cuDNN EULA，全部与既有审计SHA相符，未打包驱动；未用nvperf_host已排除，CUPTI硬依赖保留。OpenCV仅图像接口，独立videoio FFmpeg DLL和Worker PyAV19均不进入包。

没有Ultralytics/Plus实际包或运行调用。拒绝列表与第三方格式转换代码中的名称不等同携带旧引擎，未通过删名称规避。证据：payload-scope-check.json、真实worker模块记录和候选文件清单。

原有未决事项不伪报解决：
1. 七FFmpeg DLL实际静态依赖通知归属尚不完整，重点shaderc/glslang/SPIRV、libjxl/Highway、rav1e/Rust、GCC/MinGW及LAME/libiconv/soxr；现有顶层材料不能替代全部归属。Chromaprint->FFTW的GPL证据保留，不宣称全LGPL。内部运行与对外传递义务有别，不要求公开公司私有资产；对外源码闭包未批准。
2. Microsoft CRT同一公司员工电脑内部安装使用与向他人转移条款适用证据仍UNRESOLVED；不凭签名或Qt LGPL推定转移授权，也不推导必须重编译全部Python/Qt。
3. CPython基座libffi/liblzma实际版本及通知、若修改CPython的摘要尚未取得；PSF原文和已有第三方材料已保留，不推定来源哈希差异即需购买许可。

未要求再次批准已确认的法人/模型使用范围，未购买许可。此处保留可用本机候选，FIELD_DELIVERY_APPROVED=FALSE、GENERAL_DISTRIBUTION_APPROVED=FALSE；未将候选改标获准现场部署版本或复制至最终现场目录。常规材料缺口与实质转移权证据分别列明，不把全部功能工作停在材料审查上。

## 文件保护与停止

`E:/IVAD Project/IVAD_Demo`的387个文件与任务开始前逐项SHA完全相同；原公司权重SHA不变。两份历史未跟踪规划文档保留，历史证据不覆盖。只新增demo_rf源码/构建配置与本报告，产物、私有权重和运行证据在本地忽略目录；未修改原环境、驱动或全局Python，未改Git历史。PACKAGING_FREEZE=TRUE。本轮结束，等待用户审阅。
