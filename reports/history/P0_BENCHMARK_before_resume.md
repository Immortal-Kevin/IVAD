# P0 双模型基准报告

日期：2026-10-12。**无法公平对照，未产生性能数据或默认模型胜者。**

| 模型 | 权重加载 | 输出一致性 | OpenVINO GPU | XPU 最小训练/短训 | p50/p95 | FPS | 峰值内存 |
|---|---|---|---|---|---|---|---|
| YOLO26n | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | 无数据 | 无数据 | 无数据 |
| YOLO11n | NOT TESTED | NOT TESTED | NOT TESTED | NOT TESTED | 无数据 | 无数据 | 无数据 |

共同前置条件 BLOCKED：GPU 运行库未安装，GitHub release API 响应截断，可信官方权重与公开样例图未成功下载。未将网页上的官方 COCO 性能当成本机测试。

## 保留的实验方法（尚未执行）

scripts/p0/yolo_probe.py 规划在两模型相同公开 bus 图上，640×640、batch=1、FP32、10 次预热、100 次同步 GPU 请求；分别记录 CPU 解码/LetterBox 预处理与模型执行时间。FPS 定义为 1000 / 平均请求毫秒数，不含解码、后处理和 GUI，也不是视频端到端 FPS。

参考前向在 PyTorch XPU；转换阶段设置前向设备守卫，禁止转换器静默执行 CPU 神经网络前向。OpenVINO 显式 GPU 编译与实际设备检查。原始框容差 atol=2 pixels / rtol=0.01，类别分数 atol=0.02 / rtol=0.02；最终 NMS 检测数量和类别相同，框容差同上。YOLO26 的比较路径设 end2end=False，若执行须明确这是受控比较模式，并补测其默认 end-to-end 路径；不能据此完整宣称默认部署能力通过。

训练分为 640×640 合成检测 batch 的模型级 loss/backward/step，以及六张非敏感合成矩形图（train=4，val=2）的框架单 epoch 短训；合成样本仅验证执行与权重生成，不代表精度或泛化。

设计中的资源指标为每次推理后的进程 RSS 采样峰值，不是系统 RAM 峰值或 GPU VRAM。GPU 利用率、共享显存与持续稳定性本轮均 NOT TESTED；未把全部系统 RAM 当显存。

## 原始记录与局限

本轮没有模型计时 JSON、训练权重或训练日志。仅有依赖下载、环境核查与基础探针导入失败日志，位于 reports/raw/。未来执行 yolo_probe.py 将生成 reports/raw/yolo26n.json 和 yolo11n.json；当前它们不存在。

脚本通过 Python AST 语法检查，但模型 API、转换与训练段未通过运行验证，恢复环境后必须验证并按真实堆栈有限修复。单图 100 次方法仅属微基准，不能替代多样本、视频、多轮温度/功耗控制与长时间稳定性测试。

模型决策：保留两款候选，不指定最终默认模型；先恢复完整官方依赖/权重下载，重跑 GPU 门禁，再开展公平比较。没有改用其他 GPU 或 CPU 的授权执行。
