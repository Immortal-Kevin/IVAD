# NVIDIA 工件下载及核验

[GitHub Release](https://github.com/Immortal-Kevin/IVAD/releases/tag/nvidia-archive-20261118)。以下文件从公开下载端实际读取并核对 SHA-256 和大小。

| 附件 | 类别 | 字节 | SHA-256 |
| --- | --- | ---: | --- |
| [rfdetr-nano-0d48a0e4.pth](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/rfdetr-nano-0d48a0e4.pth) | 项目登记权重 | 120,889,621 | `bc9d31e4457fe18c3306d3f567ff1fc6b0885a4bd3c233c867dcf865da1c52c6` |
| [rfdetr-nano-50de2cc6.pth](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/rfdetr-nano-50de2cc6.pth) | 项目登记权重 | 120,889,749 | `639f7f99903cd86c3ce44bd9ee48e238b35e94c185eba925d3032c72d9a9c7ad` |
| [yolo11n-4a1c7df7.pt](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/yolo11n-4a1c7df7.pt) | 项目登记权重 | 5,505,105 | `b878f79dbc83a78267c329671014e853147c26f260eb60691abbc289750a8b9f` |
| [yolo26n-2814763f.pt](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/yolo26n-2814763f.pt) | 项目登记权重 | 5,459,503 | `d4498ee7934dbe8074f7da637a16c331a13f73586652fd560ff6909f6d92a1b0` |
| [yolo26n-dd2e7eec.pt](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/yolo26n-dd2e7eec.pt) | 项目登记权重 | 5,459,759 | `277e090da1e4b3f72cb0a874f02e10ab18e116250f1ce6473a080e83af133f84` |
| [ids-full-1a6fba2d.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-full-1a6fba2d.ids) | 真实 IDS 完整包 | 797,223,140 | `1a6fba2d8a53115eec597ce1a544f3869cca9acd699d9af3824fbb8bca367780` |
| [ids-full-4dd25e9f.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-full-4dd25e9f.ids) | 真实 IDS 完整包 | 797,281,675 | `4dd25e9f7cd96823369b6d4f06fb6fc2e6ec3d54b66dc90b0a24d7f009a5be86` |
| [ids-full-5ca106a6.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-full-5ca106a6.ids) | 真实 IDS 完整包 | 388,444,183 | `5ca106a6d082ef671cfb6c42277d5f97b0d8323d2a178f0dcc8a78f078026b16` |
| [ids-full-c563bcb1.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-full-c563bcb1.ids) | 真实 IDS 完整包 | 797,281,845 | `c563bcb1ac66bf2c60df5e07b0d8b7d6d05bc0eb39bf4fe3503585149dbfa4fb` |
| [ids-delta-7575f1a8.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-delta-7575f1a8.ids) | 真实 IDS 增量包 | 2,330,029 | `7575f1a8b246741b392d14b766dc90c2993a2e5136dfd57c404292c3305605c9` |
| [ids-delta-bedbe81b.ids](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/ids-delta-bedbe81b.ids) | 真实 IDS 增量包 | 196,722 | `bedbe81bcd278d14ae5c7355ea69ca7973ae89e1fe09ab6e401e17c572c64d0c` |
| [roboflow-rfdetr-nano-coco-1.11.2.pth](https://github.com/Immortal-Kevin/IVAD/releases/download/nvidia-archive-20261118/roboflow-rfdetr-nano-coco-1.11.2.pth) | Roboflow 官方基座 | 366,287,238 | `d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d` |

Roboflow RF-DETR Nano COCO 原版采用 Apache-2.0。版权和授权原文见 [固定版本 LICENSE](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/LICENSE)，[模型授权](https://roboflow.com/model-licenses/rf-detr)，[官方 COCO 权重](https://storage.googleapis.com/rfdetr/nano_coco/checkpoint_best_regular.pth)。
历史 YOLO 权重由项目训练，基座由 Ultralytics 发布。见 [官方授权说明](https://www.ultralytics.com/license)、[固定框架源码](https://github.com/ultralytics/ultralytics/tree/v8.4.176)及 [项目的历史配置和适用声明](https://github.com/Immortal-Kevin/IVAD/tree/nvidia-public-history-20261118/archive/yolo)。

原始 YOLO 官方基础权重链接保留在 [Ultralytics Assets v8.4.0](https://github.com/ultralytics/assets/releases/tag/v8.4.0)。全量检查点和现场原始文件按本地归档索引保留。当前训练仍使用 RF-DETR。

源码变更见 [历史映射](ADDITIONAL_SOURCE_HISTORY.tsv) 和 [遥测清理](TELEMETRY_REMOVAL.md)。
