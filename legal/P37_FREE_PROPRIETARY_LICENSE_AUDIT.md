# P3.7-A 免费闭源许可证专项审计

日期：2026-10-16。结论：**PARTIAL；正式分发 BLOCKED**。目标为金海泽地内部闭源工业软件，不购买商业许可、不改变IVAD自研源码授权。内部运行的工程可行性、特定组件免费闭源路径与整个产品可分发是三个不同结论。关联厂区不能一概当作同一法律主体。

## 已核实的范围

本轮重新读取RF环境全部96个包及GUI环境21个包（含测试工具），分别采集154/28份原样许可通知；逐包版本、许可字段、原文位置见 [SBOM](P37_DEPENDENCY_SBOM.md)。原生文件逐条SHA256在同目录两个 `P37_*_NATIVE_BINARY_INVENTORY.json`；不能以wheel顶层许可替代它们的实际条款。原始证据位于 `artifacts/p37a-20261016/license-audit`。未运行安装器或改变依赖。

| 组件/实际版本 | 判断 | 已满足 / 尚未满足 | 免费方案与代价 |
|---|---|---|---|
| RF-DETR 1.11.2 Nano及官方Nano权重 | FREE & VERIFIED（本体与所核实资产许可路径） | 固定上游commit、Apache全文、权重哈希及官方资产声明已留存；原派生文件头保留。不是所有传递依赖发行认证 | 保留Nano；不启用Plus，后续版本/权重重新审计 |
| PyTorch 2.9.1+cu128 / Torchvision 0.24.1+cu128 | FREE WITH OBLIGATIONS | BSD等通知可读；wheel含CUDA/cuDNN等独立条款，不能整包标BSD | 保留现有环境；发行前完成二进制对应通知，约1–2人日材料核对 |
| ONNX 1.20.1 / ONNX Runtime GPU 1.24.4 | FREE WITH OBLIGATIONS | Apache/MIT及第三方通知已采集；GPU Provider不转授NVIDIA运行库权利。本轮训练不依赖ORT推理 | 保留；按实际payload校验通知及NVIDIA库 |
| PySide6 / Essentials / Addons / Shiboken6 6.8.3 | FREE WITH OBLIGATIONS | 存在LGPL免费闭源路径；实际模块与动态DLL已核实，完整GPL/LGPL文本已补采。对应源码交付、替换实测和应用条款尚未完成 | 保留现有GUI；补材料及独立DLL替换测试约1–3人日，不必擅自换GUI |
| PyAV 15.1.0（GUI）、19.0.1（RF）和其FFmpeg DLL | REPLACEMENT RECOMMENDED | PyAV BSD；两个FFmpeg均报告LGPLv3+但配置启用x264/x265，未形成构建/链接完整证据，不能宣称可闭源分发 | 经审核的无GPL/nonfree/x264/x265 LGPL共享构建+对应源码/构建脚本；先独立回归解码/时间戳/片段保存，约3–5人日。未经批准不替换 |
| OpenCV headless 5.0.0.93及其自带FFmpeg/图像库 | REPLACEMENT RECOMMENDED（发行构建） | OpenCV许可不覆盖全部codec；自带FFmpeg版本与PyAV不同，需独立检查 | 未来构建不捆绑未核实视频后端，复用已核实PyAV解码；2–4人日构建与图像回归，不在本轮实施 |
| CUDA 12.8、cuDNN 9.10.2.21 | FREE WITH OBLIGATIONS（本机开发）；捆绑分发UNRESOLVED | 本机真实CUDA运算通过；已核查EULA的运行与指定redistributable条件，但未完成每个拟分发DLL的许可对应 | 继续本机研发；未来由各电脑部署已批准官方运行库/驱动，或核对获准DLL后动态捆绑；1–3人日。不需要据此购买AI Enterprise |
| NumPy 2.2.5（GUI）及RF实际版本、Pillow 11.2.1（GUI）及RF版本、SciPy等 | FREE WITH OBLIGATIONS | 具体环境版本逐行见SBOM；BSD/Pillow等及OpenBLAS/图像库通知保留 | 按实际原生文件提供通知，不改现有包 |
| FlatBuffers 25.12.19、Polygraphy 0.53.6、pycocotools 2.0.11、ONNXsim 0.7.0 | UNRESOLVED（发行材料） | 原有补采/失败记录保留；部分wheel无通知、复合许可覆盖未闭合。不是已发现必须付费 | 从准确上游版本补齐来源和原文；或未来从不使用它们的最小运行环境排除（先做闭包测试），约1–3人日 |
| 历史Ultralytics 8.4.176 / thop 2.2.2 / platform 0.1.84及旧权重 | REPLACEMENT RECOMMENDED（未来闭源产品路径） | 无Enterprise/已批准AGPL方案；本轮RF路径零依赖实测通过，但旧GUI训练/离线路径仍保留 | 后续另行批准P3.7-B及历史入口隔离；不删除、不重新授权旧模型。约3–5人日为规划估算，未执行 |

RF权重的核实不等于数据隐私、商标、所有编解码专利或整个IVAD产权已认证。[固定RF源许可](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/LICENSE)；资产原始证据沿用P3.6，不因本轮自动扩大许可范围。

## Qt专项

真实GUI进程实际加载Qt6Core、Qt6Gui、Qt6Widgets、Qt6Svg及qwindows插件，均来自 `.venv-p1` 的独立DLL，文件版本6.8.3.0；Shiboken动态加载，记录见 `artifacts/p37a-20261016/qt-loaded-modules.json`。源代码使用Core/Gui/Widgets，QtTest仅测试工具；Svg为实际加载的图像模块。没有据此认定整个Addons可无条件发布：安装目录中其他模块未被产品实际使用，未来打包须显式排除不适用模块。

当前使用动态库，未检测到静态Qt链接或本轮二进制补丁；DLL作为文件可单独定位。**用户替换为兼容修改版DLL后的实际运行：NOT TESTED**。本轮禁止安装包构建，未执行PyInstaller/Nuitka产物替换验证。未来优先可替换目录布局，不以单文件封装、签名/哈希强校验、反修改条款妨碍适用的调试和重新链接权利；提供Qt/PySide/Shiboken准确对应源码及修改说明、LGPL/GPL文本和第三方通知，应用EULA保留为调试LGPL修改而需的权利。不得声称LGPL要求将IVAD全部开源，也不得把LGPL等同无义务。

官方依据：[Qt许可](https://doc.qt.io/qt-6.8/licensing.html)、[LGPL义务](https://www.qt.io/development/open-source-lgpl-obligations)、[Qt for Python第三方](https://doc.qt.io/qtforpython-6.8/licenses.html)。新增原样文本和来源SHA256在 `legal/licenses/p37`，不删除原版权。

## FFmpeg专项

RF PyAV libavcodec **63.1.102**，GUI PyAV libavcodec **61.19.101**；本轮分别实际读取两环境7个FFmpeg DLL的版本、configuration、license及SHA，完整结果在 `artifacts/p37a-20261016/rf-native-codec.json`、`gui-native-codec.json`，没有解码或改写视频。配置有 `--enable-shared`、`--enable-version3`、`--enable-libx264`、`--enable-libx265`，未见 `--enable-gpl` / `--enable-nonfree`。这一组合与返回LGPL字串不足以确认实际链接授权，不能据未见gpl标志就宣称整个构建LGPL安全。原生库的源码、构建脚本、静动态链接、codec提供方和实际二进制对应尚缺。

[FFmpeg官方许可说明](https://ffmpeg.org/legal.html)列出GPL组件/外部库条件及分发材料。未来候选LGPL构建必须实际核对flags、依赖和字节来源；H.264/H.265等潜在专利与开源版权是不同问题。集团内部/不销售不自动消除专利或向独立关联方交付的义务；专利地域与用途确认仍UNRESOLVED。已保留现有解码器，未进行未经批准替换。

## NVIDIA专项

独立环境Torch报告CUDA12.8，实际cuDNN DLL资源版本9.10.2.21；cudart/cublas PE资源字符串及ORT CUDA Provider实际资源版本见 `nvidia-dll-versions.json`。资源字符串保留原样，不冒充Toolkit语义版本。每个库SHA256已进原生清单；NVIDIA驱动617.42未修改且不计划捆绑。

| 场景 | 本轮判断 / 下一门槛 |
|---|---|
| 开发机本地运行 | 已有环境研发使用，CUDA运算已验证；不推定本轮生成新的授权协议 |
| 公司内部其他电脑安装 | 免费路径可评估，但必须落实条款接受主体、指定运行库和通知，不因内部使用免审计 |
| 关联厂区服务器 | 先核对是否同一法律实体/子公司、访问主体和部署方式；不能一概套用内部员工条款 |
| Windows安装程序内捆绑DLL | 逐文件核对CUDA/cuDNN获准redistributables、版本、用途、应用条款和通知；当前BLOCKED |

依据：[CUDA12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html)、[cuDNN9.10.2 EULA](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html)。所核查运行库许可路径与NVIDIA AI Enterprise订阅不同；本轮不购买任何许可证。最终产品条款和法律主体确认交公司审阅。

## 结论与停止点

技术零依赖结果见 `reports/P37_ZERO_ULTRALYTICS_DEPENDENCY.md`。可继续审阅本轮工程成果；**不能标记为整体免费闭源分发合规通过**。整改清单见 [发行义务](P37_DISTRIBUTION_OBLIGATIONS.md)。本轮只补材料、未实施替换、未购买、未开源、未打包；等待用户选择后续整改。
