# P0 双模型基准报告（续行）

日期：2026-10-12。**尚无公平双模型计算基准，不能指定默认模型。**

| 模型 | 官方权重下载/hash | 模型加载/输出一致性 | OpenVINO GPU | XPU训练 | p50/p95、FPS、峰值内存 |
|---|---|---|---|---|---|
| YOLO11n | PASS（仅文件） | NOT TESTED | NOT TESTED | NOT TESTED | 无实测数据 |
| YOLO26n | BLOCKED（未完成下载） | NOT TESTED | NOT TESTED | NOT TESTED | 无实测数据 |

YOLO11n权重已完整下载并匹配官方release digest；YOLO26n部分传输后达到120秒墙钟上限，保留片段、暂停加载。两模型具体URL/大小/hash见 raw/model_download_manifest.json；结果见 model_segment_download.log。官方公开bus.jpg已取得137,419 bytes，原图来源与本地hash见 artifacts/p0/sources_resume.json；图像hash为本地计算，不伪称发布方提供。

OpenVINO基础简单图已PASS，不能替代YOLO实测。XPU核心运行库仍缺，不能加载模型做XPU参考前向或训练。没有生成任何模型计时JSON、有效训练权重或训练指标；没有以官方COCO FPS/mAP代替本机/工业结果。

## 后续实验方法（计算段尚未验证）

按既定脚本使用同一bus图、640×640、batch=1、FP32、10次预热和100次同步OpenVINO GPU请求。分开记录CPU解码/预处理及模型执行时间；FPS=1000/平均请求毫秒数，不含GUI、解码和后处理。p50/p95基于完整原始100条记录，不能用下载耗时代替。

XPU参考前向与显式GPU编译输出比较：原始框 atol=2像素/rtol=0.01，分数atol=0.02/rtol=0.02；最终检测数量/类别一致、框坐标容差同上。YOLO26的受控对照关闭end2end，因此后续还须补其默认路径；不能单凭此模式宣称默认部署能力通过。转换阶段有CPU前向守卫，禁止隐式CPU神经网络计算。

训练分为模型级loss/backward/optimizer.step，以及非敏感合成图单epoch短训；仅验证计算与权重生成，不评估工业精度。RSS采样峰值不等于系统RAM或GPU内存；GPU占用、峰值共享内存及持续稳定性均尚未测得。

结论：保持YOLO26n/YOLO11n两候选，默认模型未定。先取得并校验剩余文件，再恢复依赖、重跑门禁、开展公平比较；不改用CPU或其他GPU。

## 2026-10-14 VPN直连续行

Tailscale出口节点已启用，官方下载目标实际选择Tailscale路由。仅对下载进程禁用代理/绑定WLAN以及socket接口选择均未恢复连接；最后一种方式被WinError10013拒绝。未修改系统路由、VPN、代理、TLS或驱动；依赖下载尚未恢复，没有新增GPU/模型测试PASS。
详见P0_VPN_DIRECT_20261014.md及原始日志。等待用户手动停用出口节点，或单独授权临时停用并恢复，之后先做有界直连对照，再继续P0。不进入P1。
