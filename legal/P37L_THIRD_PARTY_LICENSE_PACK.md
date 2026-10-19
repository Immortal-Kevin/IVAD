# P3.7-L 许可证材料与署名包

日期2026-10-19。材料草案，不是为整个IVAD新增Apache LICENSE，也不表示发行门禁已解除。

## 完整原文与索引

- [Apache-2.0完整官方副本](licenses/p37l/upstream/Apache-2.0.txt)、[固定RF原LICENSE](licenses/p37l/upstream/RFDETR-LICENSE.txt)及[官方README](licenses/p37l/upstream/RFDETR-README.md)。
- [LGPLv3](licenses/p37l/upstream/LGPL-3.0.txt)、[GPLv3](licenses/p37l/upstream/GPL-3.0.txt)、[实际Ultralytics8.4.176 AGPL全文](licenses/p37l/upstream/AGPL-3.0.txt)。
- 全部已采MIT/BSD/Pillow/PSF等原文按环境/组件分目录，329份记录见[NOTICE_INDEX](licenses/p37l/NOTICE_INDEX.json)，每份含路径与SHA；原始版权文字不由摘要替代。
- [第三方通知草案](P37L_THIRD_PARTY_NOTICES_DRAFT.md)、[NOTICE草案](P37L_NOTICE_DRAFT.md)、[作者致谢](P37L_SOFTWARE_ATTRIBUTIONS_DRAFT.md)、[About建议](P37L_ABOUT_DRAFT.md)。
- [官方网络来源/获取状态/完整字节SHA](licenses/p37l/upstream/SOURCES.json)；22项读取成功、3项未取得（固定RF根NOTICE、DINO根NOTICE、尝试的RF专门licensing页）。404不能当成许可证缺失或不存在全部NOTICE；已用固定官方README/包LICENSE核对Nano的声明。未声称访问成功不可达页面。

## RF及Apache专项

正式使用rfdetr1.11.2 Nano；[权重证据](licenses/p37l/RF_WEIGHT.json)重新计算已有文件SHA/MD5并与安装资产索引匹配，不下载模型、不反序列化。固定README将开源包及Apache指定权重列为Apache-2.0，而rfdetr_plus与XL/2XL检测组件是PML1.0；四环境无Plus发行版。不能把“XL”名称跨检测/分割和未来版本一概归类。

本地backbone文件保留Roboflow、LW-DETR/Baidu、ConditionalDETR/Microsoft及DETR/Facebook原头；DINOv2/LW-DETR/DeformableDETR完整上游LICENSE已取得，RF实际文件头索引见RF_SOURCE_ATTRIBUTIONS.json。主分支上游页面只能作补充，不证明其与安装版每个字节相同；进一步源码对应缺口单列。

Apache §2/§3提供适用版权/专利许可，不是商标授权或权利保证；§4要求许可副本、保留适用版权/专利/署名通知，修改文件作显著声明，存在适用NOTICE时按条款保留。自研且有权许可的IVAD部分可由权利人决定单独采用Apache，但不能重许可第三方受限文件；本轮不作该决定。Apache不一般性要求公开私有训练数据/权重，但继承的上游权利、数据授权和实际模型内容仍审。公开代码不提供加密、鉴权或商业秘密管理，需独立控制。

## Qt/PySide/Shiboken履约指引

实际6.8.3，Core/Gui/Widgets/Svg/qwindows为既有真实加载证据，动态DLL安装；未证明最终安装包的兼容替换已通过。闭源与部分开源GUI都需按实际LGPL路径保留完整文本/版权、提供准确对应源码及库修改材料、合规源码获取/offer、必要安装信息，允许适用库替换和为调试修改库所需逆向/重链接。只显示作者名不能替代履约；公开通用GUI可能方便审计，但不免除库义务。

安装的Charts/DataVisualization/Quick3D/VirtualKeyboard等是GPL-only可选模块，不在当前已证明调用集合。最终payload按白名单排除未用模块，不能只凭动态链接就将它们归为LGPL。Qt内部第三方SPDX/SBOM也须与最终模块文件对应；无需据此重写全部GUI。[Qt官方](https://doc.qt.io/qt-6.8/licensing.html)、[履约说明](https://www.qt.io/development/open-source-lgpl-obligations)。

## FFmpeg/PyAV/OpenCV专项

PyAV GUI/Lite15.1.0、RF19.0.1，当前实际libavcodec分别61.19.101/63.1.102；每DLL configuration/license/hash在各环境codec.json。两个构建显示shared、version3、libx264/libx265，未显示enable-gpl/nonfree，同时返回LGPLv3+。这组证据不足以裁定其外部codec准确链接/许可；需构建方源码/脚本和二进制对应。未发现nonfree标志也不等于所有传递组件免费可发。

通用人工片段保存services/media_service.py使用libx264；旧离线输出也使用libx264，即使禁止旧AI任务，P2视频链仍需处理。OpenCV5.0.0.93自带视频/图像库另审，其Apache包声明不能转授所有codec权利。H.264/H.265专利独立于GPL/LGPL，地域/用途未知为LEGAL REVIEW。

免费方案比较：已核查的无GPL/nonfree/x264/x265依赖的LGPL共享FFmpeg（更接近既有PyAV API，需替代编码器和PTS回归，估3–5人日）；Windows Media Foundation（不用随应用带整套FFmpeg，但取决OS/SKU/codec/MFT、VFR/PTS与硬件支持，部分codec可能需另装，不能承诺所有格式零额外成本，估5–10人日）；图像处理Pillow/NumPy可减少不必要OpenCV视频后端，不能直接取代所有RF传递图像操作。解码本来可CPU，不要求争抢训练GPU。以上均未替换/安装/编译。

## NVIDIA逐DLL核查清单

本机驱动617.42/RTX5070Ti只读查询，未改驱动。Torch2.9.1+cu128/Torchvision0.24.1+cu128，cuDNN文件资源版本见补表；包CUDA版本不等于每DLL资源字符串。CUDA12.8.1 EULA和cuDNN9.10.2 EULA原文已采集；逐文件仍须核对匹配版本、允许redistributable及通知/条款主体，不允许把SDK/驱动整体任意转发。AI Enterprise服务不等于这些免费SDK许可的强制购买项。

下表每一文件名有对应环境/路径/SHA/资源版本记录于NATIVE.json与BINARY_VERSIONS.json；表中差异用分号保留，空值为未核实，不以包版本填充。当前开发使用与未来捆绑分发分开评定，表项分发均待闭合。

| DLL | 实际文件资源版本（原文） | 对应条款 | 动作 |
|---|---|---|---|
| cublas64_12.dll | 6,14,11,1284 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cublasLt64_12.dll | 6,14,11,1284 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudart64_12.dll | 6,14,11,12080 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_adv64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_cnn64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_engines_precompiled64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_engines_runtime_compiled64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_graph64_9.dll | NOT VERIFIED | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_heuristic64_9.dll | NOT VERIFIED | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cudnn_ops64_9.dll | 9.10.2.21 | cuDNN 9.10.2 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cufft64_11.dll | 6,14,11,1133 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cufftw64_11.dll | 6,14,11,1133 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| curand64_10.dll | 6,14,11,1039 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cusolver64_11.dll | 6,14,11,1173 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cusolverMg64_11.dll | 6,14,11,1173 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| cusparse64_12.dll | 6,14,11,1258 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| nvJitLink_120_0.dll | 6.14.11.9000 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| nvToolsExt64_1.dll | NOT VERIFIED | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| nvrtc-builtins64_128.dll | NOT VERIFIED | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| nvrtc64_120_0.alt.dll | 6.14.11.9000 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |
| nvrtc64_120_0.dll | 6.14.11.9000 | CUDA 12.8系列/单独组件条件需对照 | 精确SHA→redistributable/通知/实体与用途，未闭合不可打包 |

ORT的onnxruntime_providers_cuda.dll、onnxruntime_providers_shared.dll及onnxruntime_providers_tensorrt.dll也在逐文件清单。TensorRT Provider随ORT安装不证明TensorRT SDK/Python包已安装或Provider启用；四环境清单未发现nvinfer运行库或TensorRT发行版，不推定全机器不存在独立SDK，也不把完整TensorRT当已用组件。nvcuda.dll属于外部系统驱动，不计划捆绑，若将来改变则另审。

本地研发：沿适用SDK条款使用，未证明需额外商业付费；公司内网安装：确认licensee/拷贝文件/用户范围；独立关联方和甲方：检查实体及交付条款；runtime入安装包：逐DLL和通知清单先闭合；用户自行安装SDK/驱动：仍不得忽略Torch自带DLL。当前所有拟议发行判断保持BLOCKED。

CUDA EULA §1.2.6还涉及Critical Application的未认证/责任条件。未来工业安全报警用途是否落入该定义需要结合实际功能和法务意见；当前RF工程验证不能替代安全认证，也不由本报告直接判定禁止用途或要求购买AI Enterprise。

## 未完成事项

其他copyleft/例外：NumPy2.2.5实际LICENSE含OpenBLAS及GCC runtime GPL-3.0-with-GCC-exception，不能仅写BSD，也不能忽略例外而认定整个应用必须GPL。certifi与tqdm的MPL覆盖文件和修改/源码获取义务须保留；tqdm还含MIT部分。PyInstaller6.22.3为开发/旧构建工具，GPL带bootloader例外、部分文件Apache；其官方说明允许依赖许可相容的商业/专有应用输出，不自动要求IVAD改GPL，也不免其他依赖条款。修改并分发PyInstaller本体另履约。[准确当前官方说明](https://pyinstaller.org/en/stable/license.html)，安装版原文在lite-build通知目录。自定义非商业/PML不作为已用Nano许可；当前无法确认的自定义或无许可证条目保持NOASSERTION/GRAY，不假定自由复制。

精确payload未形成、库源码/offer/替换实测未交付、原生内部静态依赖与codec来源/专利未闭合、部分包缺完整通知/原包凭证、实际著作权与法人接受主体未确认。MPL文件级及GPL/AGPL组合义务按准确文本审查。材料包不是最终法律意见或软件许可授予，也不代公司接受SDK条款。
