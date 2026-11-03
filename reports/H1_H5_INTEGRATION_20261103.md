# H1–H5 Intel 主工程集成（2026-11-03）

实际主工程为 IVAD_Platform_v1.0。原先无 Git 元数据；在原始源码建立基线 22dbcb9 / baseline/intel-before-h1-h5-20261103，随后独立 integration/h1-h5-20261103 分支集成。源候选为 hotfix/h1-h5-review / c248f09fa63c85284b8cceb6afb650054d84f204，原始 12 个文件与该候选 merge-backup 字节相同，不存在主工程侧未保留的新源码。H1/H2/H3/H4/H5 原状态均 NEEDS_MERGE；媒体工作流原已实现，沿用。功能映射见 integration/20261103/feature_status.json。

已集成帧/几何局部事务、确认状态、保存并下一帧、筛选、虚拟化和图片缓存、原子批量正常/撤销、有界范围多选、队列软删除/恢复及有效 IDS 投影。补齐原候选缺失的缩放/平移，以及使用既有协议的增量基线保存/导出 GUI。没有新增第三方依赖、pHash、SSIM、模型、数据库迁移或协议版本改变。数据库实际为 project.ids.json 与资产目录，不是 SQLite。审核权限维持原有本地角色规则，不声称为强身份认证。

原构建是 Windows .NET Framework csc + WPF，无 .sln/.csproj。新增 Release 配置 /platform:x64 /optimize+ /debug-，嵌入原 DPI/asInvoker manifest、Theme.xaml，并复制 .NET 4.8 config、LICENSE、NOTICE。文件版本 1.1.5.0。输出 build/integrated-release-20261103/IVAD.Annotator.exe；精确 SHA256、源码 Commit/哈希和构建时间见同目录 BUILD_PROVENANCE.json。

最终 ./scripts/release_gate.ps1 -Integrated -EvidenceDirectory integration/20261103/gate-verified 全部通过；真实视频导入/抽帧/取消、几何与正常/异常审核、重启/导出、完整/删除/恢复增量、幂等、损坏包回滚等在独立测试项目执行。没有把内部 WPF 路由命令冒充物理输入。真实鼠标画框、物理 Ctrl+S 保存跳帧、Ctrl+A 多选通过；组合键鼠标、原生文件对话框完整链和中键平移仍 NOT TESTED（工具索引/焦点异常或 API 不支持），详见 native_acceptance.json。

1000/10000 帧，各100样本：选择 P95 1.9678/3.4598ms，滚动 P95 4.6682/4.8911ms，行更新 P95 0.2848/0.2728ms。窗口实际显示、每次等待 WPF 队列并确认滚动目标行已生成；这是 WPF 组件级响应，2张合成图片复用的元数据测试，非物理鼠标端到端，也不是10000张工业大图结论。首次隐藏窗口滚动检查失败记录保留在 gate-final，已修复测试显示条件后重跑；早期构建/test命名失败日志保留，不作最终失败遗漏。

原用户数据3077个文件在操作前后逐项SHA一致，保护清单在 integration/20261103。真实视频只读复制到独立测试项目。程序运行目录不包含测试包或工业数据。原主工程 build/dev 及最后历史实际使用的 H1-H3/build/dev 都先完整复制到 rollback，再以验收候选替换旧入口；旧 EXE 与全部原目录文件保留。无对外发布或安装包。

回滚：关闭新程序；从 integration/20261103/rollback/runtime_build_dev 或 runtime_last_used_h1_h3 复制原完整运行目录回对应目录，核对 rollback_manifest.json / last_used_runtime_rollback.json 的 SHA；源码在新分支查看 baseline/intel-before-h1-h5-20261103，禁止 reset --hard/clean 或覆盖用户数据。此次未修改候选源码及 Git 历史。

NVIDIA 交接采用备份目录下独立的新主线源码树，保留旧 Manifest 历史、候选记录与先前授权的真实工业包。另加入本轮真实 Exporter 生成的安全合成完整/增量包并明确分类。旧候选源码不得当作当前有效主线。
