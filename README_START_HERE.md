# IVAD NVIDIA-first 设计调整包

本包从已确认的 v1.0 十项产品需求修改 **硬件主线及 P0 验收范围**，不代表新产品需求谈判，也不包含依赖环境。

1. `docs/SRS.md`：NVIDIA CUDA 主线、Intel 延后单独验证。
2. `docs/ARCHITECTURE.md`：worker_nvidia 首要、worker_intel 保留。
3. `prompts/CODEX_MASTER_PROMPT.md`：长期规范更新。
4. `prompts/P0_IMPLEMENTATION_PROMPT.md`：改为 P0-NVIDIA 实机测试。

在 5070 Ti 机器上新建独立目录，解压本包；先让 Codex 阅读前三份，并检查第四份，然后授权 P0。不要从 B390 原项目复制 `.venv`。原 B390 P0 报告应单独备份留存，状态仍是 BLOCKED。
