# P3.7-A 统一评估与重载一致性

日期2026-10-16。结论 **PASS（本轮固定环境/权重/40图验证集）**。不是工业泛化验证；保留LIMITED。

## 对象与控制条件

原P3.6最佳EMA权重SHA256：`2d5940c25447b5be8d94180635f815feb16cbbfd645e699e32e7548e8d6b8f5f`，未改写。冻结版本 `fd9a3ba2-ed9b-4698-8838-5002b036fef0`，manifest SHA256 `5eecfe2509b89dd67ec0ecf6280654607f036599099d538d305e27c27798a8ac`，40验证图/71框/3正常，160训练图不参与本次验证指标。

正式协议 `ivad-rfdetr-eval-v2`：同权重、同GT、RFDETR.evaluate、FP32且TF32关闭、官方DataModule方形BILINEAR抗锯齿/RGB/ImageNet、384、batch4、maxDets500、faster-coco-eval1.8.0、COCO IoU .50:.95、官方F1 sweep P/R。Torch2.9.1+cu128、Torchvision0.24.1+cu128、Lightning2.6.6、Pillow12.3.0均固定并校验。

协议SHA256：`89d040d05b4151b8e4366215eda7e80666262fa21a54dda118e433501cbcb4af`。最终真实结果：`artifacts/p37a-20261016/sealed-parity-v2/result.json`（增加真实PTH布局门禁后的最终代码复验；与final-parity-v2结果一致）。两个新实例各保存每帧raw logits/normalized boxes及官方后处理boxes/scores/labels，不读取人工标注冒充预测；GT仅用于评估。

| 指标 | 第一次重载 | 第二次重载 | 绝对差 |
|---|---:|---:|---:|
| Precision（F1 sweep） | 0.9852941036 | 0.9852941036 | 0 |
| Recall（F1 sweep） | 0.9436619878 | 0.9436619878 | 0 |
| mAP50 | 0.9637941122 | 0.9637941122 | 0 |
| mAP50–95 | 0.4788966179 | 0.4788966179 | 0 |

40帧完整预测序列两次SHA均为 `92f8709f7debdc52e70d86ad0e048555b479545a5f097da02ee037ef9c85895e`。AP门槛预设1e-4，预测额外采用逐字节相等门槛，本次通过。JSON序列留在 `eval-in-memory/predictions.json` 与 `eval-reload/predictions.json`；CUDA前向由真实hook检查，非Provider名称推断。

## 原差异调查与归因

1. 原训练最佳值0.47938793898来自BF16官方验证、maxDets500；P3.6公开predict独立评估0.46532599586来自FP32、不同预处理和maxDets100、confidence截断。二者不是同一协议，不能选较高值登记。
2. 同一原权重经官方验证入口按BF16重载，**精确复现0.47938793898**。见 `parity/official-evaluation.json`。
3. 源码确认官方验证在PIL/uint8阶段抗锯齿缩放，公开predict采用GPU浮点resize且antialias=False。仅在独立调查进程将predict抗锯齿打开，mAP50–95由0.465326变为0.479183；残差涉及量化/精度、maxDets和截断，不能当作同协议结果。
4. 调查还发现RF的build_trainer会设置float32_matmul_precision('high')。只在调用前关闭TF32会被该工厂覆盖。正式v2在工厂之后、验证开始时再次设置highest/禁用TF32，固定所有版本。v1调查结果保留，不冒充最终v2结果；最初FP32调查0.478348及v1数值均不能直接等同最终v2。
5. 最终采用同一官方入口，避开两个不同predict预处理/后处理路径的混用。原生训练BF16日志单独保留；模型登记使用选定最佳PTH的v2规范评估，不宣称原生BF16和规范FP32日志应数值相等。

## 最终GUI短训链路

为验证正式v2流程，真实GUI执行1轮短训（不是重复12轮实验）：TrainingRun `fdeee654-0e2a-48a2-9c45-9abbcb2198ea`，40次优化器更新。自动登记模型 `fd9f9bf2-3b69-45b9-b713-242c06783711`，SHA256 `666fa0553d7793a160dc7c142b21db70626a266f6a72854c66096fedd958fa43`。

规范评估P=0.4893617034、R=0.6478873491、mAP50=0.5496996045、mAP50–95=0.2185004354；新模型两次重载四项差均0，40帧预测序列SHA均 `9438e30cccdf4c0128685167f9102c893932c06be0ffb547326080fe2c106355`。它是短训集成夹具，不能替代P3.6最佳模型的效果结论，也不据分数高低选择实验。

早期v1服务短训及调查文件全部保留，可追溯其协议哈希；不覆盖历史实验。重新训练之间并未开启CUDA完全确定性模式，不承诺不同训练运行逐位复现；本验收约束是同权重、同数据、同协议的重新评估一致性。
