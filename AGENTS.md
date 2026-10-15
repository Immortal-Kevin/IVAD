# 项目执行规则

用户明确批准P2，当前仅执行P2。未经用户再次明确批准，禁止进入P3–P6。
2026-10-15用户Development Directive v3优先：P2最终验收PASS后已授权自动进入P3，P2若有阻断立即停止；P3结束停止，P4–P6未授权。PACKAGING_FREEZE = TRUE：禁止构建/更新EXE、Portable、Setup和分发，既有包原状保留，解除冻结须用户明确批准。
遵守 SRS、ARCHITECTURE、CODEX_MASTER_PROMPT 和 P0_IMPLEMENTATION_PROMPT。
项目专属 venv；禁止修改其他 AI 环境、全局 Python、驱动或系统配置。
AI 必须 GPU 执行，失败即记录，不自动降级 CPU。报告保留真实原始证据。
Intel 原 P0 BLOCKED 历史独立保留；本包未包含历史报告，不重建或覆盖。
P1采用独立.venv-p1，保留P0环境与全部资产。GUI业务经服务层，耗时工作移至后台。
P2复用P1 GUI/数据库/日志/队列；普通解码/人工标注CPU允许，AI训练/推理仍GPU-only。
历史P0/P1报告、锁文件与运行证据不得覆盖；P2输出写artifacts/p2。新增依赖仅GUI环境。
仅本地Git版本追踪，不建立远程；排除虚拟环境、模型、日志、缓存与用户数据。
