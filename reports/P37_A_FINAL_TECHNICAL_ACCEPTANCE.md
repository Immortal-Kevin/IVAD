# P3.7-A 最终测试契约与技术验收

日期：2026-10-19。基线 `b0d56b7ea12b071f7e1a7f51182f1dc84e0adf2c`，分支 `feature/p37a-rfdetr-training`。本轮仅修改测试、验收脚本及报告；没有修改产品功能、训练新模型、进入P3.7-B/P4、打包或上传远程。最终本地Commit见本轮最终回复及 `git log -1`。

## 分项结论

| 验收项 | 状态 | 范围与理由 |
|---|---|---|
| P3.7-A 功能与迁移验收 | **PASS** | 现行Native/COCO契约、真实200图冻结版本、来源保护、RF历史筛选/旧归档、Registry、真实GPU加载及原生GUI打开/切换/关闭全部通过；没有以跳过代替必需契约 |
| Qt 原生历史异常 | **PARTIAL** | 本轮未复现，原始根因仍未确定。独立问题IVAD-QT-001仍OPEN，不能据功能PASS宣称已根治 |
| 整体 Ultralytics 迁移 | **PARTIAL** | A范围RF训练链路已独立；历史代码/环境/资产仍保留，RF离线推理及最终发行闭包尚未完成，不自动启动B |
| 软件发行合规 | **BLOCKED** | 沿用尚未闭合的Qt对应源码/替换验证、FFmpeg/PyAV及OpenCV编解码来源、NVIDIA逐DLL再分发和部分通知/产权材料问题；本轮不进行新的许可认证 |

`PACKAGING_FREEZE=TRUE`；`DISTRIBUTION_STATUS=BLOCKED`。功能PASS不表示无保留的全产品稳定性、工业效果或正式发行批准。

## 测试原意与契约修正

`test_four_tabs_filter_sort_draft_batch_freeze_and_export` 原意是验证四页筛选、草稿、冻结、导出及恢复剔除帧的完整GUI流程；原来等待 `*-yolo_detect-*` 仅代表当时的默认导出格式。现行产品已按用户要求默认 `IVAD Native（完整）`，另一选项为 `COCO JSON`。本轮用户明确授权更新此过时断言，产品GUI没有恢复YOLO入口。

保留全部原有关键断言、8张尺寸/分页截图检查和最后的恢复剔除帧步骤。导出部分现在断言选项恰为Native和COCO、默认Native，并通过真实按钮先导出Native，再明确选择COCO。小样本夹具仍是5图/3目标/2正常，不冒充200图。

新增 `test_real_frozen_200_native_coco_gui`，必须显式提供准备好的真实项目副本，没有合成回退或条件跳过。读取 `8525test1 v1`，分别通过GUI生成Native和COCO，重新解析、逐项验证：

- 200张图片、402个目标、16张正常负样本；正常样本在COCO中无annotation且不丢图。
- Native快照除导出路径/旁车字段之外与原快照逐字段相等，包括Camera、Media、Frame、来源组、时间、类别UUID及原人工框。
- COCO图像集合、对象UUID、类别映射（正式通用导出为内部ID+1）及每个矩形框与真值一致；不将此映射与RF专属转换器混用。
- 所有导出图片SHA、完成manifest及其文件清单SHA通过；没有YOLO `labels` 或 `data.yaml`。
- 冻结manifest逐字节不变，原版本列表、标注状态及8个来源/真值表不变；Camera→Media→Frame关系正确。

只替换目录选择对话框返回路径，没有mock导出服务、生成假文件、删关键断言或跳过失败用例。

## 实际运行结果

证据目录 `artifacts/p37a-contract-20261019`。

| 验证 | 实际结果 |
|---|---|
| 修正后的原四页GUI测试单独运行 | 1 PASS，6.30秒；原来因默认格式等待而未到达的恢复剔除帧步骤也执行通过 |
| 真实200图GUI导出首轮 | 1 PASS，24.59秒；随后在合并批次执行强化后的来源表保护断言 |
| 最终P2/P3/P3.7-A合并原生回归 | **88 PASS，1 SKIP，0失败**，115.68秒；`regression-native.log` |
| 真实CUDA模型加载/两次重载评估 | SUCCEEDED；CUDA前向及checkpoint重载为true、无CPU AI回落；40验证图parity PASS |

合并批次包含GUI导航/关闭、P2画布及真实操作、数据集生命周期/管理、RF契约、历史与Registry隔离、队列/取消及新增真实导出契约。实际为win32/PySide6 6.8.3，原生测试打印 `Qt platform: windows`；没有用offscreen替代本轮结果。独立运行与合并批次有重叠，不相加为独立用例数。

保留的SKIP：`tests/test_dataset_lifecycle.py:99` / `test_real_copy_200_restart_versions_and_training_picker`，原因为 `Requires explicitly provided independent real-project copy`，即未提供该旧用例专用的 `IVAD_LIFECYCLE_REAL_COPY`。该用例包含历史草稿/版本创建初态要求，本轮没有把当前冻结集副本冒充其专用初态，也没有改写其SKIP为PASS。当前必需200图导出与保护契约由新增真实用例独立执行通过。

GPU Job `7f7e6723-61a5-4b0c-8882-60400a410a00`，副本验证Run `b03cb055-77c6-49b2-a49d-bc5e27e489da`，模型 `0d48a0e4-8fef-4ed9-953f-b84f9736976b`。`optimizer_steps=0`、`cuda_gradients=false`、`weight_changed=false`，没有重训或新增模型。P/R/mAP50/mAP50–95为0.9285714/0.5492958/0.6369260/0.2698905，仅为现有模型规范重载结果，不代表独立工业质量验收。

## 数据与历史保护

真实原项目使用只读SQLite连接和文件读取，不通过业务服务打开；所有写操作仅在独立副本或临时夹具。原项目仍为5训练/5模型（3条旧YOLO训练及3个旧模型、2条RF训练及2个RF模型）、251帧、217标注、721修订、1冻结版本。

本轮重新采集 `before.json` / `after.json`，所有SQLite表及2,328个保护文件SHA一致。两份用户已有未跟踪规划文档、原始Qt崩溃日志、Windows Event JSON和WER文字证据SHA均一致；见 `integrity.json`。真实GUI生成的两份导出另外原样复制至 `verified-exports` 并复核manifest文件SHA，原临时输出路径与保留位置分别见 `export-gui-final.json` / `retained-exports.json`。

## 独立Qt问题与后续边界

[IVAD-QT-001](P37_QT_NATIVE_ISSUE.md) 保留OPEN/PARTIAL，登记了重新调查的触发条件与证据要求；[原调查](P37_A_QT_CRASH_INVESTIGATION.md)及上一轮失败历史均保留。本轮只修正已获授权的过时测试契约，不将“未复现”写成修复。

P3.7-A功能验收可以单独PASS。P3.7-B仍需另外授权，P4与安装包未授权；本轮完成后停止。

## 本轮文件

- `tests/test_dataset_management_hotfix.py`：保留原完整流程，更新默认格式并增加双格式内容保护断言。
- `tests/test_p37a_export_contract.py`：双格式实物校验与真实200图GUI测试。
- `scripts/p37a/final_contract_check.py`：只读前后保护、独立副本准备、真实GPU验证、实际导出证据保留。
- 本报告、`P37_QT_NATIVE_ISSUE.md`，以及最新摘要更新后的 `P37_A_ACCEPTANCE.md`、`P37_A_ACCEPTANCE_CLOSURE.md`、`P37_A_QT_CRASH_INVESTIGATION.md`。

复验需先用脚本prepare创建新的独立证据目录；prepare拒绝覆盖已有副本。pytest真实用例需设置 `IVAD_P37_FROZEN_COPY` 指向此副本，`IVAD_P37_CONTRACT_EVIDENCE` 指向本轮证据JSON。完整实际命令与合并用例顺序保留在本轮执行记录及 `regression-native.log`，不改变旧SKIP环境变量。
