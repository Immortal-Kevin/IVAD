# P3.7-D Lite 内部交付判定

日期：2026-10-19。范围仅北京金海泽地智能科技有限公司同法人研发部内部演示；接收方授权已确认，不再要求重复确认。本轮遵循新的Lite授权，先生成本机候选再审实际载荷。

源码/构建提交：`26dd8bcf10490384bcb993df4e0d38d35a9f9f8a`（其父工程提交`3fff1f734a2454f501a5b695f1adb8b76827a9aa`）；最终报告提交由本报告所属Git提交确定，提交后回执`artifacts/p37d-lite-20261019/closeout.json`和最终回复记录完整SHA。分支`feature/p37d-lite-demo`，基线`8b064b5e5fa8711e75293f189266aad99d92c502`。

**已经得到真实生成且实测可运行的IVAD候选EXE；当前不能发送给研发部领导。** 本轮核心工程交付完成，内部交付许可证门禁未完成，不能把二者合并为全部PASS。

| 状态 | 本轮结论 |
|---|---|
| BUILD_STATUS | PASS，真实onedir候选 |
| EXE_LAUNCH_STATUS | PASS，本机正常入口及独立进程重启 |
| VIDEO_IMPORT_STATUS | PASS，本机合成MP4/H.264 CFR/VFR |
| FRAME_EXTRACTION_STATUS | PASS，真实12张PNG、实际PTS及哈希 |
| ANNOTATION_STATUS | PASS，GUI框/多边形/正常异常持久化 |
| DATASET_STATUS | PASS，草稿/冻结/默认Native及COCO，各12图2目标11负样本 |
| ULTRALYTICS_FREE_STATUS | PASS，本候选文件/模块/运行/失败门禁范围 |
| PAYLOAD_LICENSE_STATUS | **BLOCKED** |
| CONFIDENTIALITY_STATUS | PASS，载荷扫描/空白项目/原资产保护范围 |
| TARGET_LAPTOP_STATUS | **NOT TESTED** |
| SAME_ENTITY_DELIVERY_STATUS | **BLOCKED**，未批准发送 |
| DISTRIBUTION_STATUS | BLOCKED，未GENERAL_DISTRIBUTION_APPROVED |
| PACKAGING_FREEZE | TRUE，已恢复，未来重新打包需新的用户授权 |

## 具体尚缺什么

| 阻断 | 实际影响文件 | 下一步 |
|---|---|---|
| FFmpeg完整履约 | `_internal/av.libs/`七共享DLL | 主源码/构建脚本已取得；继续闭合实际静态依赖源码/补丁/通知和提供安排，或免费构建仅需解码能力的可追溯最小共享FFmpeg并回归 |
| VC Runtime准确再分发链 | 根目录内部、PySide6、Shiboken6、NumPy内11个实际DLL，SHA/资源版本见CSV | 对照准确官方条款/redistributable清单与来源；采用可证明的免费安排，不静默安装系统组件 |
| Python平台来源/复合材料 | bundled CPython3.12.14及实际原生运行文件 | 补齐原包/第三方材料或独立已核清基座重建；不能只附PSF文本当作全部权利证明 |

同法人批准和接收范围已确认，**不需要用户重复授权同一接收方，也没有当前必须购买商业许可的证据**。这些工程材料仍由开发方继续闭合；不会要求公开工业视频/标注/权重。目标机OS、驱动、空间、权限及受控测试窗口需公司提供，当前NOT TESTED；本版不含AI训练/推理，4GB显存不作为软件已兼容保证，也不阻止CPU视频/标注路径。

Qt6.8.3对应源码/通知/替换权说明已附；匹配替代库组的实际完整流程和最终EXE启动退出通过。混版失败、stderr与Windows事件保留。历史IVAD-QT-001仍PARTIAL，未宣称根治。

候选位置`dist/IVAD_P37D_Lite_Candidate/IVAD_Internal_Demo.exe`，EXE 8,667,863 bytes；SHA256 `e0822ff177caad959283ba692362a510909a30c2645811172b52f82cf451b8f5`。完整目录302,062,240 bytes。中文指南、支持格式/禁用功能说明、原始许可证/对应Qt源码及SHA清单已经放在目录中，但**这不是可发送标记**。没有制作`IVAD_P37D_Lite_Internal_Demo.zip`，也未实际发送。

本轮保存所有日志/失败分支，不重训、不进入P3.7-B/P4、不修改原始Git历史/数据库/权重、不更改Windows安全配置、不push或公开源码。当前源代码和本轮报告仅本地提交。最终报告Commit以`git log -1 --format=%H -- reports/P37D_LITE_DELIVERY_READINESS.md`取得；最终回复和本地closeout回执给出完整SHA。完成后停止待审，不自动继续构建。
