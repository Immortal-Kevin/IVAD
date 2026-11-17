# NVIDIA 同步与本地保留索引

此次发布使用普通 Git。各组件和工件沿用原授权。

| 保留项 | 版本 | 字节 | SHA-256 | 原因 |
| --- | --- | ---: | --- | --- |
| [rfdetr-nano](https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth) | rfdetr-nano rfdetr 1.11.2 / COCO | 366,287,238 | `d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d` | Roboflow 官方 Apache-2.0 权重；超过普通 Git 100 MiB 上限 |
| [yolo11n](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt) | yolo11n v8.4.0 | 5,613,764 | `0ebbc80d4a7680d14987a577cd21342b65ecfd94632bd9a8da63ae6417644ee1` | 官方基座可定位，当前项目的再分发条件未确认 |
| [yolo26n](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt) | yolo26n v8.4.0 | 5,544,453 | `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef` | 官方基座可定位，当前项目的再分发条件未确认 |

- 工业微调权重、检查点、ONNX 导出、现场录像及真实 IDS 包的公开权限待核实。原路径、版本、大小、哈希和别名记录在本地完整索引。
- 历史自定义 YOLO 训练器及与其相关的低层测试版权来源待核实。旧 API 调用、适配代码和脱敏参数可在历史分支追溯。
- NVIDIA 专有 WPF 集成、原始现场报告和截图、原第三方网页、供应商依赖、运行环境及安装工件保留在本地。
- 公开源码提供 RF-DETR 训练与独立实验，以及 Qt 源码启动入口。安装包冻结。

[GitHub 普通 Git 文件大小限制](https://docs.github.com/en/repositories/working-with-files/managing-large-files/about-large-files-on-github)
