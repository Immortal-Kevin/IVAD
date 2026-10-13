# 项目执行规则

用户于2026-10-13明确批准P1，当前仅执行P1。未经用户再次明确批准，禁止进入P2–P6。
遵守 SRS、ARCHITECTURE、CODEX_MASTER_PROMPT 和 P0_IMPLEMENTATION_PROMPT。
项目专属 venv；禁止修改其他 AI 环境、全局 Python、驱动或系统配置。
AI 必须 GPU 执行，失败即记录，不自动降级 CPU。报告保留真实原始证据。
Intel 原 P0 BLOCKED 历史独立保留；本包未包含历史报告，不重建或覆盖。
P1采用独立.venv-p1，保留P0环境与全部资产。GUI业务经服务层，耗时工作移至后台。
仅本地Git版本追踪，不建立远程；排除虚拟环境、模型、日志、缓存与用户数据。
