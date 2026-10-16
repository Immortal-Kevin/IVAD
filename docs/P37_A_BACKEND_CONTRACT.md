# P3.7-A RF-DETR契约

无数据库migration；沿用TrainingRun/ModelVersion.details JSON。路由 `training_router.TrainingService` 显式根据model选择RF服务；旧实现仅在明确选择旧架构时延迟导入。旧服务显式拒绝RF，RF无旧引擎fallback。

RF请求沿现有 `p3_train` / `p3_validate` 任务：root、version_id、device_id、model=rfdetr-nano、parameters、initial_model_id、operation。独立 `.venv-rfdetr` 用 `-I` 启动，参数schema见 `compute/rfdetr_contract.py`，不能接受YOLO键。CUDA UUID对应任务资源ID和跨进程字节锁；取消sentinel绑定单次工作目录。只有成功结果和一致性检查均通过才登记。

冻结数据经 `datasets/rfdetr.py` 导出COCO和provenance旁车，保留所有UUID、原class_id、图片SHA及来源时间。模型槽位按原class_id排序映射0..N-1，Registry同时保存model_class_id/coco_category_id/类别UUID；正常图片保留空annotations，异常无框/冲突/剔除/未准入与本轮不支持的polygon均拒绝，不静默转换。

评估统一 `RFDETR.evaluate`、FP32、384（或显式RF分辨率）、RGB/ImageNet、官方DataModule方形抗锯齿缩放、maxDets500、COCO IoU .50:.95、faster-coco-eval。P/R是官方F1 sweep，不是固定confidence=.25的P/R。关闭TF32；固定依赖环境及同权重/同验证集。协议JSON及SHA写入结果。

登记前两次全新重载同一最佳PTH，AP差≤1e-4，并核对每帧raw logits/normalized boxes及官方后处理boxes/scores/labels的完整序列哈希；当前采用逐字节相等，比容差更严格。预测跟踪只在测试/训练目录，Registry保存其哈希与帧数，不复制人工框作模型输出。任何差异停止登记，不选择较高指标。

保存路径：project/training/独立UUID，Worker请求/日志/取消CKPT/正式PTH/统一评估及预测证据分别保存。Registry独立模型UUID，保留权重和SHA、冻结集版本与SHA、类别映射和SHA、专属参数、架构、评估协议/哈希及LIMITED来源，默认EXPERIMENTAL。登记与成功TrainingRun在同一事务，外部复制未登记工件可以保留作故障证据。

新API结果PASS含metrics、evidence、parity、weights/sha、protocol/sha、环境版本和loaded_modules；CANCELLED/BLOCKED不进入成功登记。检查点恢复未开放，RF Small仅可沿Adapter协议扩展，没有在GUI中伪称已支持。许可证审计独立，不由runtime PASS放行分发。
