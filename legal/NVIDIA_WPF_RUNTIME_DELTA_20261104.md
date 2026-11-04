# WPF 运行闭包增量：未获得分发放行

复用 NVIDIA_PERMISSIVE_REMEDIATION.md 与 P3.7-L 原始通知，不覆盖旧结论。当前本机完整包/DLL清单保存在受控目录 runtime-closure.json：媒体服务8包/17原生文件，RF候选移除可选组件前92包/275原生文件。清单有安装版本、Requires-Dist、通知路径、DLL/PYD大小及SHA256；不能用此清单替代构建来源证明。

实际变化：默认GUI入口迁移至WPF，不加载PySide6/Shiboken；Qt代码在history入口，仅供回滚。新媒体路径沿用已整改MF环境；RF候选继续采用此前自研进度/CA兼容层，排除av、tqdm、certifi、Ultralytics与OpenCV FFmpeg DLL。新增移出ml_dtypes 0.6.0及其原生载荷/元数据至本地隔离备份，原LICENSE完整保留；移除后CUDA训练和历史模型推理通过。ONNX可选链未验证，不能把移除可选组件称为整个ONNX能力保持。

|实际必要组件|版本/许可依据|当前结论|
|---|---|---|
|SQLAlchemy / Alembic|2.0.40 / 1.15.2，MIT|沿用原通知；SQLite schema不变|
|greenlet / Mako / MarkupSafe|3.5.6 / 1.4.3 / 3.0.4，MIT / MIT / BSD|安装版本已记录；原生来源仍需闭合|
|PyYAML / typing_extensions|6.0.2 / 4.16.0，MIT / PSF|保留既有依赖，不单凭顶层许可批准全部载荷|
|Pillow|媒体11.2.1、RF12.3.0，HPND及捆绑图像库通知|沿用原通知；两套实际二进制来源仍需闭合|
|RF-DETR Nano|1.11.2，Apache-2.0基础路线|不安装plus，不切换PML模型；权重及骨干分别按原材料核查|
|NumPy / SciPy|2.5.4 / 1.18.1，顶层BSD，捆绑OpenBLAS/GCC例外|严格策略BLOCKED，不能按顶层BSD放行|
|PyTorch / Torchvision|2.9.1+cu128 / 0.24.1+cu128，BSD及第三方通知|保留CUDA功能；逐DLL再分发证据未闭合|
|CUDA/cuDNN等NVIDIA库|实际DLL清单与历史通知|受NVIDIA条款及可再分发清单约束，未放行|
|Windows MF/.NET/WPF|本机系统前置，不随开发输出复制|不是因非MIT而拒绝；未来选定再分发组件需按具体EULA/清单核对|
|SQLite|现有Python系统库及SQLAlchemy接口|未新增SQLite发行二进制，来源及随附条件仍纳入未来载荷审计|
|字体/资源|Intel Theme.xaml，WPF系统字体|未下载或随附新字体；系统字体不复制入载荷|

NumPy/SciPy仍实际用于RF数值、图像及指标链，不能删除。当前PATH无cl/clang-cl/flang/meson/ninja，标准vswhere路径不存在；本轮未成功建立替代工具链，也未完成源码重构建，故严格策略阻断未解除。可行路线应继续按官方构建说明准备MSVC/无BLAS NumPy和合规Fortran/BLAS SciPy，不以目录重命名、进程隔离或删除通知冒充替换。

法律与工程策略分开：[GNU GCC Runtime Library Exception 3.1](https://www.gnu.org/licenses/gcc-exception-3.1.en.html)允许符合条件的专有独立模块组合，不自动要求公开IVAD数据库；但现有捆绑组件仍不满足用户选择的更严格无GPL载荷政策。[Microsoft .NET Framework部署指南](https://learn.microsoft.com/en-us/dotnet/framework/deployment/deployment-guide-for-developers)说明部署/再分发渠道，本轮未将系统DLL复制打包；具体未来组件仍须核对授权条款。[NumPy官方构建文档](https://numpy.org/doc/stable/building/)为替代构建依据，不能当作本机已构建成功的证据。

公司源代码、工业数据库、媒体与权重仍为私有资产。保留Intel及其他第三方署名/许可不等于公开公司业务源码。技术PASS与许可PASS分开：本轮许可总体BLOCKED；PACKAGING_FREEZE=TRUE。
