# 模型与权重许可登记

Full / NVIDIA：BLOCKED；Annotator无AI/模型依赖。

| 对象 | 固定依据 | 状态 |
|---|---|---|
| RF-DETR核心代码 | 官方tag1.11.2的LICENSE/README/pyproject与同版wheel核对 | Apache声明已取得；整栈尚未批准 |
| RFDETRNano/Small/Medium/Large检测权重 | 同tag README标为Apache；model_weights_source.txt保留官方映射 | 只列候选，未下载；具体权重hash/内容验证和本地运行NOT TESTED |
| rfdetr_plus与PML模型 | 官方明确区别许可 | 禁止引入，不下载、不安装 |
| 其他变体/权重 | 不从项目根许可证推断 | UNKNOWN/BLOCKED |
| 旧Ultralytics权重与实验权重 | 已退休 | 删除，非运行/分发依赖 |

来源：https://github.com/roboflow/rf-detr/tree/1.11.2 ，对应raw文件和wheel发布方URL/hash均保存在evidence/rfdetr。官方README的“Apache-designated model weights”不足以代替将来实际文件的SHA256和来源校验；当前没有任何获准加载权重。

自研RfDetrBackend.CanTrain=false，Train明确失败，不隐式下载，不降级CPU，不引入Plus。当前只实现IDS到COCO矩形检测快照适配与协议边界。
