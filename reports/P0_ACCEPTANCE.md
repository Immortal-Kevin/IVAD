# P0 测试与验收报告（续行）

日期：2026-10-12，Asia/Shanghai。**总体 BLOCKED；OpenVINO基础GPU已PASS，P0完整验收尚未通过。P1明确未获批准。**

| 门槛 | 状态 | 证据及限制 |
|---|---|---|
| 复用既有两环境 / 缺包核查 | PASS | 未重建；初查两环境仅pip，缓存无可复用wheel |
| DNS / 代理 / TLS诊断 | PASS（诊断） | 官方DNS可解析，配置代理未启用，证书验证保持开启；不是网络修复完成 |
| 下载问题定位 | PASS（证据） | 大响应慢/超时、官方R2端点403；官方替代CDN可读取，深层链路原因仍未确定 |
| intel_infer恢复及依赖一致性 | PASS | 已验证官方hash后离线安装；pip check通过，实际锁已保存 |
| OpenVINO实际B390 GPU计算 | PASS | 执行GPU.0，正确输出[0,1,3,5] |
| 完整intel_train安装 | BLOCKED | 缺少完整XPU及其他剩余wheel；候选闭包已核验，暂停该安装步骤 |
| XPU前向/反向/更新 | BLOCKED | 探针已执行，缺torch导入，计算段未运行 |
| YOLO26n/YOLO11n GPU推理 | NOT TESTED | 不是权重文件hash通过就可记GPU通过 |
| 两模型小训练 / 公平基准 | NOT TESTED / BLOCKED | 无训练权重、无性能数据，默认模型未定 |
| 官方模型/样例来源 | 部分PASS / BLOCKED | YOLO11n hash通过、bus取得；YOLO26n未完成 |
| 报告、脚本、真实日志 | PASS（交付） | 四份报告更新；脚本语法检查单独记录，不等于计算段通过 |
| 系统及用户数据保护 | PASS | 未改代理/TLS/驱动/全局Python，未删除或上传用户数据 |
| P1边界 | PASS | 未开发GUI或P1模块；不请求进入P1 |

## 剩余阻断与最小人工步骤

当前 62 项P0候选依赖中，44 个wheel完整通过官方hash；尚需人工取得的文件共 19 个（含未完成模型）。完整且准确的官方URL、文件名、版本、ABI/Windows标签及SHA256见 P0_OFFLINE_DOWNLOAD.md、raw/offline_missing_manifest.json。这些是候选文件清单，训练环境仍未安装，不能称为完整成功锁。

1. 在网络稳定的电脑下载该清单。可用 scripts/p0/download_offline.ps1（仅下载/校验，不安装；每文件600秒上限、TLS默认验证），或按清单用浏览器下载。若脚本执行策略阻止运行，不改系统策略，使用浏览器及Get-FileHash方法。
2. 将校验后的文件放入本项目 artifacts/p0/offline_drop 并告知Codex。随后再核查全部hash/ABI/闭包，在现有intel_train离线安装固定+XPU版本，运行pip check及GPU门禁，继续双YOLO测试。当前暂停相关安装，未用CPU替代。

## 原始证据与变更范围

reports/raw保存既有与本轮的环境、网络、403、超时、分段下载、官方METADATA/hash及GPU输出。首轮四份报告保存在 reports/history/，不覆盖其失败证据。四份当前报告及 P0_DEPENDENCIES.md / P0_OFFLINE_DOWNLOAD.md 提供当前结论；README、PROGRESS、CURRENT_TASK、DECISIONS同步更新。

修改仅在项目脚本/报告/状态记录及实验缓存内；没有改SRS、架构或正式prompt，没有改系统/其他AI项目。完整文件与未完成片段均保留；终止的进程仅为本轮已核对的项目下载任务。

风险：XPU/模型兼容性仍未测、脚本模型计算段仍未验证、无工业精度或长期稳定性结论、GPU内存未测、商业许可未解决。保持P0，不进入P1。

## 2026-10-14 VPN直连续行

Tailscale出口节点已启用，官方下载目标实际选择Tailscale路由。仅对下载进程禁用代理/绑定WLAN以及socket接口选择均未恢复连接；最后一种方式被WinError10013拒绝。未修改系统路由、VPN、代理、TLS或驱动；依赖下载尚未恢复，没有新增GPU/模型测试PASS。
详见P0_VPN_DIRECT_20261014.md及原始日志。等待用户手动停用出口节点，或单独授权临时停用并恢复，之后先做有界直连对照，再继续P0。不进入P1。
