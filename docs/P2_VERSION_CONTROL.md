# P2本地版本记录

分支nvidia-first，没有远程推送。P1基线2626af8；P2实现提交52d36f1（2026-10-13），62个源码/测试/文档文件，包含Schema0003、真实媒体/标注/冻结导出工作流及71项主测试。随后报告收尾提交以git log为准，更新最终耗时、启动验证和保留性证据。

源码ivad_app/、tests/、scripts/p2/、prompts/P2_IMPLEMENTATION_PROMPT.md、六份P2报告与依赖锁纳入版本控制。venv、artifacts、runtime、原视频/模型/用户项目/导出、P0历史敏感环境文件均被排除。测试原始JSON/XML/截图仍保存在本机artifacts/p2，不上传。

P1原测试只调整Schema最新版本期望及证据输出位置，避免覆写历史artifacts/p1；P1报告/锁/截图/hash保持一致。Git源码回滚不应擅自回退已经迁移的用户数据库；使用迁移前备份与完整项目备份另行恢复。未经明确批准不进入P3。

2026-10-14：P2补充修改在同一nvidia-first分支提交，左右媒体页/人工MP4片段/Schema0004及84项测试纳入本地版本。旧P2报告副本在artifacts/p2-adjustment/history，旧原始证据hash不变。详细提交ID以git log为准，没有远程推送，没有进入P3。
