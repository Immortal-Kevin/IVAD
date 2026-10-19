# P3.7-D Lite 构建结果

日期：2026-10-19。范围仅北京金海泽地智能科技有限公司同法人研发部内部演示；接收方授权已确认，不再要求重复确认。本轮遵循新的Lite授权，先生成本机候选再审实际载荷。

源码/构建提交：`26dd8bcf10490384bcb993df4e0d38d35a9f9f8a`（其父工程提交`3fff1f734a2454f501a5b695f1adb8b76827a9aa`）；最终报告提交由本报告所属Git提交确定，提交后回执`artifacts/p37d-lite-20261019/closeout.json`和最终回复记录完整SHA。分支`feature/p37d-lite-demo`，基线`8b064b5e5fa8711e75293f189266aad99d92c502`。

**BUILD_STATUS=PASS；真实EXE已生成并从正常入口实测启动。当前仅本机候选，不可发送。**

| 产物 | 实际值 |
|---|---|
| EXE | `dist/IVAD_P37D_Lite_Candidate/IVAD_Internal_Demo.exe` |
| EXE大小 | 8,667,863 bytes（8.266 MiB） |
| EXE SHA256 | `e0822ff177caad959283ba692362a510909a30c2645811172b52f82cf451b8f5` |
| onedir | `dist/IVAD_P37D_Lite_Candidate/` |
| onedir大小/文件数 | 302,062,240 bytes（288.069 MiB），384文件，含公开对应源码/通知及SHA清单 |
| 清单 | 根目录`SHA256SUMS.txt`；全文件来源/哈希/版本见`P37D_LITE_PAYLOAD_FILES.csv` |
| 可交付ZIP | **未制作**，许可证尚未闭合 |

## 实施

复用现有界面、ProjectStore、SQLite、后台任务、视频播放器、标注画布、数据集服务。Lite专用标识和能力门禁同时作用于组合根、服务入口、任务注册/提交和动态导入；不是只隐藏按钮。AI/历史缓存服务使用拒绝实现，片段重新编码从队列与直接服务调用两处拒绝。训练/模型/离线识别导航隐藏，生产工作空间禁用；研发源码、旧记录和权重均保留。Lite空白项目不再初始化行业故障类别模板，由用户自行创建类别。

独立`.venv-p37d-build`安装锁定GUI与构建工具，PyInstaller6.22.3 onedir，不复制旧venv、不使用onefile。旧环境未安装/升级任何包，未修改系统Python、驱动、CUDA或Windows安全策略。主要命令：`.venv-p37d-build/Scripts/python.exe -m PyInstaller --noconfirm --workpath artifacts/p37d-lite-20261019/build-minimal --distpath dist packaging/p37d-lite/ivad_lite.spec`。

先实际生成初始候选并正常启动（初始EXE SHA已单独留存），随后按测得问题迭代。36个PyAV扩展PE导入表重新链接到前轮已校验的七个BtbN共享FFmpeg DLL，原构建环境wheel DLL移到本轮研究区，完全不进入载荷；旧GUI/RF/YOLO环境不变。PyAV的RECORD同步更新，保留原BSD版权和修改说明；不是重命名旧x264/x265文件规避检查。

Qt Python模块排除不足以限制hook自动收集，因此增加实际DLL/插件白名单：Core/Gui/Widgets/Svg、qwindows、样式及必要图像插件。排除VirtualKeyboard/Qml/Quick/Pdf等未用模块、构建工具代码、主机构建工具目录误收的44个Windows API shim及UCRT。使用受支持Windows自身的系统组件；不修改系统。Alembic源脚本保留，禁止生成程序目录字节码缓存。

## 证据与局限

`pyinstaller-initial.log`至`pyinstaller-caption-final.log`保留所有构建日志。没有将构建成功等同可交付；首个候选正常入口启动返回0，最终候选完整流程和新进程重启均返回0。完整过程见功能报告。开发机Windows11 10.0.26200 x64；没有干净VM/独立Windows账户，没有目标笔记本实测。运行时PATH只保留Windows System32，移除开发Python环境变量并隐藏CUDA；实际加载的Python/Qt/视频库来自onedir，不依赖开发venv。

恢复`PACKAGING_FREEZE=TRUE`，`DISTRIBUTION_STATUS=BLOCKED`。不push、不公开源码、不进入P3.7-B/P4、不训练、不交付他人。
