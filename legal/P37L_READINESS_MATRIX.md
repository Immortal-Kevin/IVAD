# P3.7-L 审计完成度与使用就绪矩阵

日期2026-10-19，基线deff366。**本轮约定范围的审计报告、清单与拟议方案交付完成；没有实施合规整改，也没有解除发行门禁。** 无证据项用GRAY/UNRESOLVED处理，不作违法或已合规结论。

| 分类 | 结果 | 已有证据 | 未决事项及适用范围 |
|---|---|---|---|
| A LICENSE INVENTORY | **PARTIAL** | 4环境187条发行版、1,687条原生文件、运行时文件/引用/依赖及来源索引；官方许可与实际codec元数据 | 全部捆绑DLL内部静态库/codec构建对应、若干wheel原包及精确许可证版本未闭合；不是最终payload |
| B ATTRIBUTION MATERIALS | **PARTIAL** | 329份原样通知、Apache/GPL/LGPL全文、固定RF及上游材料、About/NOTICE/作者草案 | 部分NOTICE/来源证据、库对应源码/offer、最终payload材料仍缺；草案不等于已履约 |
| C CLOSED DATA CONFIDENTIALITY DESIGN | **PASS（拟议设计范围）** | 明确A/B数据与代码分层、真实Git/导出/缓存/日志风险、12类保护及公开白名单方案 | **实施/渗透/ACL/加密/恢复验收NOT VERIFIED**；真实权利人与公开许可未批准，不能称资产已安全 |
| D ULTRALYTICS RESIDUAL AUDIT | **PASS（枚举与边界范围）** | 直接/动态旧路径、Worker/GUI/任务封禁、历史资产/模型与Git/payload范围区分 | 全产品移除仍PARTIAL；来源相似性/权重法律权利与不可达历史对象未认证 |
| E INTERNAL DEVELOPMENT READINESS | **PASS（限定零付费RF本机研发路线）** | 已有Nano/Apache、独立RF Worker及环境；无需通过购买Enterprise继续该路线 | 不覆盖旧YOLO争议或未知公司的数据/SDK接受事实；公司权利/数据审批和L01/L02/L05仍需办，不扩大为所有安装/部署PASS |
| F INTERNAL DEMO READINESS | **PARTIAL** | 同一受控开发机、授权人员观看有免费候选路线，既有功能技术证据 | 演示者/接收方法人、真实数据展示许可、拷贝软件/权重与codec材料未明确；不自动授权交领导安装 |
| G AFFILIATED PLANT DEPLOYMENT READINESS | **BLOCKED** | 有逐场景分析与免费整改路径 | 法人/服务器/数据协议、软件交付义务、runtime/codec与安全控制未闭合；REQUIRES LEGAL REVIEW |
| H WINDOWS DISTRIBUTION READINESS | **BLOCKED** | 已有清单/原文及具体解除条件 | 未形成/审定最终payload、Qt源码替换、codec/NVIDIA/通知/权利及净机证据；PACKAGING_FREEZE有效 |

## 四项不能混淆的状态

P3.7-A功能与迁移验收PASS；Qt原生历史异常PARTIAL，问题IVAD-QT-001仍开放；整个Ultralytics迁移PARTIAL；软件分发合规BLOCKED。P3.7-L只提供独立许可/保密审计，不重训、不宣布Qt根治、不替代P3.7-B技术验收。

## 未决证据

[UNRESOLVED清单](P37L_UNRESOLVED.md)逐项列责任人和关闭证据；[行动表](P37L_LICENSE_ACTION_CHECKLIST.md)明确哪些用户亲办、哪些Codex可在授权后做。不能以愿意公开通用源码自动豁免GPL/AGPL衍生范围、Qt库义务、NVIDIA许可或工业资产保护。

`PACKAGING_FREEZE=TRUE`；`DISTRIBUTION_STATUS=BLOCKED`。本轮结束后停止；B/P4、开源发布、许可证采购和打包均未授权。
