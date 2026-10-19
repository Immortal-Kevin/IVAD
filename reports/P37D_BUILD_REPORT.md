# P3.7-D 内部演示构建报告

日期：2026-10-19。接收范围仅北京金海泽地智能科技有限公司同法人研发部领导。用户已授权本轮候选构建，不要求额外商业许可购买，也未授权公开源码或外部交付。

**BUILD_STATUS=BLOCKED_D2_NO_EXE。本轮未生成 EXE。** 按任务第11节先整改许可再构建，以及第14节“第三方DLL再分发权利无法确认”的停止条件，停止受影响的 D3–D7 候选构建、候选验收和交付批准。不是 PyInstaller 构建失败，也不是断言免费方案不可行。已下载的研究用 FFmpeg.exe 是上游工具，不是 IVAD EXE，不能发送给领导充作成品。

## 基线与文件

- 实际起点 `458e32688638ecea630fa98ad427df52bc5652c3`，原分支 `feature/p37a-rfdetr-training`；创建 `feature/p37d-internal-demo`，未 reset。
- 最终本地 Commit 由本报告所属 Git 提交确定：`git log -1 --format=%H -- reports/P37D_FINAL_SUMMARY.md`。提交后的完整 SHA 和保护结果另写本地 `artifacts/p37d-20261019/closeout.json`，最终回复给出同一 SHA；不在文件内伪造自引用提交哈希。
- 本轮修改仅新建 `scripts/p37d/` 两个检查/原型脚本、`packaging/p37d/` 的状态/来源索引/待验收指南和七份 `reports/P37D_*.md`。没有更改应用、数据库 schema、训练参数或历史打包脚本。
- 两份原有未跟踪规划文档不加入本轮提交。原分支、`nvidia-first`、P3.6/P3.7-A/P3.7-L 和 Qt 历史证据保留。

## D1–D7

| 阶段 | 本轮实际结果 |
|---|---|
| D1 最小分析 | 已生成14个 GUI 运行包输入计划；不是 PyInstaller 实际闭包。保留 RF GUI/Registry 的独立 Worker 载荷尚未确定，不能声称已得到全部实际 Payload |
| D2 关键整改 | 已取得四份 Qt 6.8.3 源码并匹配官方校验；取得固定 LGPL FFmpeg 包并匹配发布方校验；完成合成 CLI 原型。完整许可材料、PyAV 链接替换和 Qt DLL 替换验收未闭合 |
| D3 候选构建 | BLOCKED，未运行 PyInstaller，没有 onedir、Setup、ZIP 或可交付目录 |
| D4 开发机候选验收 | NOT TESTED；源码原生 Windows 回归14项通过和小张量 CUDA 检查另列参考，不能替代 EXE |
| D5 目标机 | NOT TESTED，无目标机访问和 OS/驱动/磁盘/权限资料 |
| D6 实际载荷复核 | NOT TESTED，无最终载荷可扫描 |
| D7 内部交付 | BLOCKED，未批准发送 |

## 构建环境与输出

独立创建 `.venv-p37d-build`，仅 venv 自带 Python/pip；没有把历史环境复制到其中，也未安装打包/业务依赖。由于 D2 门禁未闭合，没有假称它是已锁定的可复现构建环境。旧 `.venv-p1`、`.venv-rfdetr`、`.venv-nvidia`、`.venv-distribution` 只读使用，未 pip 安装/升级其中任何包。系统 Python、CUDA、NVIDIA 驱动和安全策略未修改。

| 产物字段 | 实际值 |
|---|---|
| IVAD EXE 路径 / 大小 / SHA256 | N/A / N/A / N/A，未生成 |
| onedir 路径 / 大小 | N/A / N/A，未生成；未新建建议的最终 dist 目录 |
| 对应源码准备 | `artifacts/p37d-20261019/qt-sources/`；来源/完整 SHA 见 `packaging/p37d/source-materials.json` |
| FFmpeg 研究包 | 62,425,578 bytes，SHA256 `0f376f96fb38554ccefb1b2ae9c7c6a7b351f0e60a372b38262c320e8392c5d0`，不作为交付批准 |
| 本地原始证据 | `artifacts/p37d-20261019/`，新建目录，不覆盖旧证据 |

本轮没有重新训练、没有下载模型、没有上传远程、没有进入 P3.7-B/P4。完成后 `PACKAGING_FREEZE=TRUE`，正式发行仍 BLOCKED，后续重新打包需要新的用户授权。
