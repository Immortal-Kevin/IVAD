# IVAD Annotator v1.1 Windows x64 便携测试交付

## 本次交付

- 最终文件：`dist/IVAD-Annotator-v1.1-win-x64-portable.zip`，**可由用户拷贝到指定测试电脑**；不是仅重命名开发EXE。
- 大小：85341 bytes（83.34 KiB）。
- SHA256：`66633ee6471781024fa077a6f4a809b1034dbba198e8426e38c2ac7befd3fb97`。
- 软件：IVAD Annotator v1.1测试版；构建号 `1.1-test.20261026.01`；文件/程序集版本 `1.1.2026.1026`。
- 一次性授权 `IVAD-ANNOTATOR-PORTABLE-20261026-ONCE` 已消耗：**CONSUMED_FROZEN**。后续新版打包必须再次明确授权，打包脚本已验证拒绝复用此授权。没有签名、安装包、上传、公开发布或复制到其他设备。

## 三个独立状态

| 状态 | 结论 | 证据边界 |
|---|---|---|
| A 许可证与实际分发材料 | PASS | 对最终ZIP逐项白名单、许可证、PE/程序集/PInvoke/资源/隐私/hash审查；不含第三方运行库 |
| B 本机独立目录可执行运行 | PASS（内部命令/文件与媒体层） | 10项首次运行+3项第二进程检查，另有真实NTFS权限拒绝与包内环境检测。真实GUI流程不包含在此PASS内 |
| C 其他Windows电脑实际运行 | NOT TESTED | 尚无其他电脑实测记录，不能由本机结果推断 |

真实鼠标/物理 Ctrl+S/普通双击GUI完整流程：**NOT TESTED**。computer-use启动本次解压后的候选程序被拒绝，原文 `Computer Use was not approved to use annotator`。没有通过其他原生UI方式绕过。内部 RoutedCommand/按钮处理器不能代表真实输入。

## 实际技术栈与部署选择

C# 5、WPF、Windows .NET Framework CLR v4.0，编译为PE32+ AMD64/x64，优化、无PDB；重新编译程序使用正式产品名称和版本。现有系统编译器文件版本4.8.9221.0，构建机.NET Framework 4.8.1（Release=533509）。Portable EXE.config 与TargetFramework属性明确要求 **.NET Framework 4.8或更高4.x**。不是.NET 8/9/10 Desktop Runtime，也没有self-contained组件。纯4.8目标机尚未实测。

Windows Media Foundation负责视频读取；WPF/GDI+/Windows Forms等为系统依赖。运行不依赖Python、CUDA、开发SDK或独立GPU。没有NuGet包、FFmpeg、第三方DLL、系统字体或模型随附。自研源代码和诊断夹具实现编入同一EXE，测试视频在本地临时生成，不随ZIP携带。

目标为Windows 10/11 x64普通用户桌面；Manifest为asInvoker、系统DPI感知。系统媒体能力（特别是N版/精简系统及HEVC）需要目标机检查。纯4.8、Windows 10、其他电脑/显卡与物理DPI结果均不冒称PASS。

包内提供 `检查运行环境.cmd`（只读注册表/文件检测，不更改全局配置）和 `RUNTIME_REQUIREMENTS.txt`。缺少运行库时用户自行从Microsoft官方Runtime入口安装，可能需管理员/重启，不需要Developer Pack；不替换/降级现有较新4.x。缺CLR时由EXE.config对应的CLR激活提示处理，应用无法在CLR之前运行自身WPF提示，缺少运行时机器的真实提示仍NOT TESTED。

依据：[Microsoft版本检测](https://learn.microsoft.com/en-us/dotnet/framework/install/how-to-determine-which-versions-are-installed)、[运行时下载](https://dotnet.microsoft.com/en-us/download/dotnet-framework/net48)、[部署说明](https://learn.microsoft.com/en-us/dotnet/framework/deployment/deployment-guide-for-developers)、[supportedRuntime行为](https://learn.microsoft.com/en-us/dotnet/framework/configure-apps/file-schema/startup/supportedruntime-element)。媒体范围依据[官方格式表](https://learn.microsoft.com/en-us/windows/win32/medfound/supported-media-formats-in-media-foundation)和[N版媒体组件说明](https://support.microsoft.com/en-us/windows/experience/platform-variants/media-feature-pack-for-windows-n)。2026-10-26核对。

## Policy B.1分发审计

最终12个文件：EXE、EXE.config、LICENSE、NOTICE、THIRD_PARTY_NOTICES.txt、SBOM.json、BUILD.json、README_中文.txt、RUNTIME_REQUIREMENTS.txt、DISTRIBUTION_COMPLIANCE.txt、检查运行环境.cmd、checksums.sha256。

- Apache原文与原项目核验一致；保留Annotator和IDS的NOTICE。没有适用的随附第三方许可证文本，因为没有随附第三方组件。没有删除或改写许可证去规避政策。
- 所有托管程序集引用均为预期Windows/.NET Framework强名称系统组件。实际PInvoke仅mfplat.dll、mfreadwrite.dll；纯托管x64 PE具有CLR目录且无额外本机导入。嵌入托管资源只有自研Ivad.Theme.xaml。类型清单中没有Ivad.Full。
- Windows/.NET/WPF/媒体组件适用Microsoft条款，明确不属于Apache授权；使用收件人已有或自行从官方安装的运行库。本次没有行使Microsoft运行时再分发权利，没有打包运行时、独立系统DLL或安装器。将来捆绑必须另审具体工件与条款，不能从本次A通过推断可捆绑。
- ZIP采用明确白名单，不压缩项目。最终内容逐文件hash和ZIP CRC通过；检查无用户个人绝对路径、私人Full代码、视频/图片/标注库、凭据、日志、缓存、Python环境或权重。
- 二进制实际构建源、编译日志、程序集检查保存在 `build/portable/46e8ba21778846d3888543f05a325675`，源码快照与BUILD哈希对应。源目录将来变动不会篡改本次已封存工件，后续编译不自动打包。

审计证据：`governance/evidence/portable-audit.json`。包内SBOM仅描述实际自研产品与IDS，系统组件明确列为未随附先决条件。许可/素材/专利/权属不作无限保证；无已知确定性B.1阻断。

## 独立运行实际证据

候选从ZIP解压到全新的项目外TEMP目录，含中文与空格。子进程PATH仅Windows/System32和Windows；去掉venv、Python与SDK环境变量，工作目录是新TEMP，不是开发目录。运行的是ZIP中的 `IVAD.Annotator.exe`，没有调用临时测试工具或原开发EXE。实际托管和本机加载模块均只来自本次解压目录或Windows目录；零其他开发目录模块。

测试机：Windows 11家庭版中文版10.0.26200、Intel Arc B390、非管理员令牌、.NET Framework4.8.1。没有更改系统代理、驱动、杀毒或全局配置。权限测试仅修改新建测试文件夹的DACL并在finally恢复。

| 请求流程 | 实际执行情况 |
|---|---|
| 解压、ZIP/文件完整性 | PASS：ZIP CRC+白名单+SHA256；原包不变 |
| 从解压目录运行EXE | PASS：该EXE诊断入口实际运行并退出0；普通鼠标双击GUI NOT TESTED |
| 新建项目 | PASS：内部调用真实后台UI处理器，在用户选定样式的中文主目录创建关联 |
| 导入非敏感视频 | PASS：程序本地生成6帧AVI，实际复制/hash/关联；源文件名116字符，完整路径175字符 |
| 抽帧 | PASS：重新定位EXE启动其自身子进程，MF实际解码6帧、原始PTS一致、任务目录清理 |
| 矩形标注 | PASS：内部编辑处理器保存原图坐标；真实鼠标画框 NOT TESTED |
| Ctrl+S保存并下一帧 | PASS：相同RoutedCommand内部执行，有框存异常且换帧；物理按键 NOT TESTED |
| 无框正常保存 | PASS：内部命令执行存正常且换帧 |
| 关闭、重新打开项目 | PASS：文件重开和新进程重开相同指纹；真实关闭按钮 NOT TESTED |
| IDS导出、空项目导入 | PASS：实际包文件/资产hash/完整元数据指纹相等，重复导入幂等；文件对话框 NOT TESTED |
| 再次启动和路径/状态 | PASS：第二个独立EXE进程检测目录并找到相机，6帧且正常/异常状态保留 |
| 用户目录写权限 | PASS：实际非管理员写入；专用测试文件夹NTFS拒绝写入时记录UnauthorizedAccessException，无覆盖 |
| 异常退出恢复 | PASS：实际写完临时清单、原子替换前暂停并终止专用子进程，重开保留最后提交hash、资产一致，可再次保存；不代表断电/所有中断点零丢失 |
| 缺少运行时提示 | 配置/检测脚本已提供；本机已安装环境检测PASS；缺运行时电脑 NOT TESTED |

未提交的临时清单被保留且不加载，测试没有删除未知业务文件。诊断日志中的权限拒绝属于预期负向测试。没有把已有开发环境的媒体测试当成解压包全部格式的跨机验证。

原始结果与日志已归档：`build\portable-evidence\IVAD 独立部署 2ab7bfa6`，包含合成测试数据、results/reopen-results、execution/reopen日志、加载模块、异常退出现场和权限拒绝日志；这些文件**全部排除在ZIP外**。索引 `governance/evidence/portable-independent.json`。

## 兼容性矩阵

| 目标 | 状态 |
|---|---|
| 本机Win11 x64 + Intel +普通用户 +中文/空格路径 | PASS：上述内部/实际文件媒体范围 |
| Win10 x64、另一台Win11、AMD/NVIDIA、无独显机器 | NOT TESTED |
| 1920×1080、2560×1440/1600，100/125/150/200% | 现有37项WPF回归包含合成布局PASS；目标机真实DPI/鼠标 NOT TESTED |
| 超过260字符完整路径、网络盘、移动介质拔出 | NOT TESTED；本次长文件名116字符，不能混同超长完整路径通过 |
| Windows N缺媒体组件、缺.NET、纯.NET4.8 | NOT TESTED |
| 任意断电、杀进程资产写入中、跨版本升级/迁移 | NOT TESTED |

## Gate与修复记录

打包后完整 `scripts/release_gate.ps1` PASS：73项服务/真实媒体 + 37项WPF内部/合成布局，均0 FAIL。测试批次 `build/test-data/20261026T093824-670f25c6`。另对实际ZIP再次审计PASS。常规Release Readiness仍保留Annotator NOT VERIFIED（尚缺真实GUI/干净机等）；本次用户限定的可拷贝便携测试交付独立记A/B/C，不伪升为全面READY。

修复：抽帧子进程曾写死开发EXE名，现默认使用当前入口程序集的绝对路径，服务测试显式指定测试目标；日志改为程序内logs并提供LocalAppData兜底；加入明确版本、CLR目标配置、asInvoker与DPI Manifest、无需外部工具的可选部署诊断。IDS格式与核心持久化不变，未新增训练/模型/许可证例外。

打包审计首轮将纯托管x64的空导入表误判为应有mscoree.dll；检查实际PE32+、CLR目录和完整程序集/PInvoke后修正允许空表或唯一mscoree，仍拒绝其他本机导入。原失败记录portable-failure-*.json保留，不是忽略未知二进制。打包脚本初次生成发生PowerShell here-string解析失败，改为直接补丁写入，未改系统设置。

## 用户跨电脑复验

将最终ZIP拷贝至指定目标机，核对旁边.sha256后完整解压；阅读README_中文.txt，检测运行环境，普通权限双击IVAD.Annotator.exe。用非敏感短MP4/H.264或AVI创建中文主目录，导入/抽帧、画框Ctrl+S、空帧Ctrl+S、末帧、重开及IDS导入导出；核对帧数/状态/几何，并记录Windows版本、GPU与DPI。不要只复制EXE，必须保留EXE.config及随附说明。不修改安全设置来绕过阻止，不复制本机测试目录或用户业务数据进软件包。
