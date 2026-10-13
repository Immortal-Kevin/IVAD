# IVAD NVIDIA-first 设计调整包

本包从已确认的 v1.0 十项产品需求修改 **硬件主线及 P0 验收范围**，不代表新产品需求谈判，也不包含依赖环境。

1. `docs/SRS.md`：NVIDIA CUDA 主线、Intel 延后单独验证。
2. `docs/ARCHITECTURE.md`：worker_nvidia 首要、worker_intel 保留。
3. `prompts/CODEX_MASTER_PROMPT.md`：长期规范更新。
4. `prompts/P0_IMPLEMENTATION_PROMPT.md`：改为 P0-NVIDIA 实机测试。

在 5070 Ti 机器上新建独立目录，解压本包；先让 Codex 阅读前三份，并检查第四份，然后授权 P0。不要从 B390 原项目复制 `.venv`。原 B390 P0 报告应单独备份留存，状态仍是 BLOCKED。

## 本机实施状态（2026-10-13）

P0-NVIDIA、P1、用户已批准的P2均已完成对应工程验收。双击根目录“启动IVAD.cmd”启动统一GUI；P2操作见docs/P2_USER_GUIDE.md，验收见reports/P2_ACCEPTANCE.md。
P2支持录像导入/真实PTS播放与抽帧/人工标注/冻结数据集和导出。真实厂区样本和工业模型精度未测试，P3–P6未经再次批准不得开始。
