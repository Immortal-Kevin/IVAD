# IVAD v1.1 — 独立标注端与 IDS

当前基线见 [v1.1需求](docs/V1_1_SRS.md)、[架构](docs/V1_1_ARCHITECTURE.md) 与 [用户授权](prompts/IVAD_V1_1_AUTHORIZATION.md)。目录名保留v1.0仅为路径稳定，不代表继续旧技术路线。

- **Annotator / IDS**：自研Apache-2.0，Windows本地离线人工标注，无AI依赖。
- **Full / NVIDIA**：私有业务代码，RF-DETR审查与数据适配边界，训练仍BLOCKED。
- **分发冻结**：没有正式安装程序，未签名、未公开、未分发。

开发启动：运行 `scripts/build.ps1`，然后打开 `build/dev/Ivad.Annotator.Dev.exe`。

测试与治理：运行 `scripts/release_gate.ps1`；它不制作安装包。

[操作说明](docs/ANNOTATOR_QUICKSTART.md) · [IDS协议](docs/IDS_V1_SPEC.md) · [Release Gate](governance/RELEASE_READINESS.md) · [剩余阻断](governance/RELEASE_BLOCKERS.md) · [清理证据](governance/LEGACY_CLEANUP_REPORT.md)

代码许可证按src/Annotator、src/Ids、src/Full各自LICENSE确定；不能将整个仓库笼统宣称Apache。用户素材、标注、模型、原始日志、旧环境和审计缓存不属于开源分发内容。
