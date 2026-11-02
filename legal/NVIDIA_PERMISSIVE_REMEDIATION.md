# NVIDIA 严格许可策略整改增量

2026-11-02；**PARTIAL，DISTRIBUTION_STATUS=BLOCKED，PACKAGING_FREEZE=TRUE**。

策略是用户选择的“目标必要载荷不含 GPL/AGPL/LGPL/MPL/非商业/研究限定依赖”，并非认定 LGPL 一概不能闭源使用。本文件不改变 IVAD 私有代码授权，不是最终法律认证。

## 已核查与实际替换

`NVIDIA_PERMISSIVE_DEPENDENCY_DELTA.json` 复用 P3.7-L 187 条 SBOM；187/187 已安装 METADATA 与历史证据一致（历史规范化文本哈希，另存真实文件字节哈希）。分类 RETAIN 89、REPLACE 18、REMOVE_FROM_RUNTIME 10、HISTORICAL_ONLY 48、UNVERIFIED 22；附当前两个候选环境准确包版本。检查所有本地分支，21 个历史提交涉及 Qt/av/Ultralytics 引用；保留原历史，不据此宣称审完所有历史原生二进制。

|组件|实际处理|尚未满足|
|---|---|---|
|PyAV / FFmpeg|新原生 MF 业务路径不导入 av；媒体环境不安装 av/cv2；RF 候选排除 av 与 OpenCV FFmpeg DLL，实测 CAP_FFMPEG=False、Torchvision video_opt=False|旧 Qt GUI和历史离线演示仍保留原路径；不能称全产品替换完成|
|Qt / PySide6 / Shiboken|保留旧环境与许可证，新媒体服务不加载|WPF GUI 未完成；缺 Intel 最新源码，不能用 LGPL 说明代替迁移|
|Ultralytics|RF 候选不安装且训练 Worker 明确拒绝导入；旧 YOLO 文件保留|历史整个产品仍有旧组件，不能混入目标载荷|
|tqdm（混合 MIT/MPL）|候选改用 IVAD 自有有限进度 API；不是复制上游实现后改许可|仅固定版本依赖调用已验证，升级需重新验证|
|certifi（MPL CA 包）|候选改用 Windows 可信根/CA；保留 TLS 证书与主机名验证|不宣称完整 SChannel 撤销检查；联网业务未验收，训练禁止联网|
|NumPy / SciPy|媒体服务已移除 NumPy，历史 dHash 输出保持一致|RF 必需 DLL 内静态 GCC runtime：GPL-3.0-or-later WITH GCC-exception-3.1，虽有例外仍不符合本轮无 GPL 策略，必须替换构建|
|ml_dtypes / Eigen|测试 RF 训练和推理未导入|候选仍有可选包与 MPL Eigen 材料；ONNX 后续路径需替换/剥离并重新验证，不能静默取消导出能力|
|Pillow / 捆绑图像库|补齐精确版本 publisher 原文、URL、SHA；媒体侧无 raqm|原 wheel 与全部原生构建来源链仍需闭合，通知存在不等于二进制完整认证|
|Windows MF / H.264 / HEVC|实际加载系统组件；未复制系统 DLL|HEVC 依赖本机已装 Store 扩展，其他电脑授权/可用性未确定；编解码专利按部署地区另核|
|CUDA/cuDNN/PyTorch/ORT|保留 P3.7-L 原材料与现有版本，不修改驱动|每个未来随包 DLL 的再分发来源/条款仍待目标载荷确定；本机成功不代表自由分发|

## 二进制证据与替代方向

实际 Windows NumPy/SciPy 的 `*.dist-info/LICENSE*` 在 OpenBLAS 部分明确列出静态 GCC runtime 与 GCC Runtime Library Exception。不能只引用顶层 BSD。目标替代方向为 NumPy 无 BLAS 构建，以及 SciPy 使用经过核查的宽松许可编译器/Fortran/BLAS 运行库构建；需要固定源码、工具链、完整 DLL 清单与 RF CUDA/评估回归。**尚未完成该替代，也未验证其全部数值性能或许可闭包**。不购买商业数学库，不删除 RF 功能以假装通过。

对 Eigen/MPL 的备选是只在确实不依赖该包的训练环境排除，ONNX 导出另做无需该实现的受测路径；需先验证 ONNX 真实依赖，不可宣称仅删 metadata 即可。完整替代工作量和可行性取决于原生构建结果。

47 个依赖源码导入补丁记录在本地 `artifacts/permissive-20261102/compat-overlay/manifest.json`，保留修改前原文、前后 SHA 和修改通知。候选中原 tqdm/certifi/pip 移至本地证据档案；原四个开发环境未修改。不是发布上游 wheel，也不代表原 Requires-Dist 已被完整重新打包；将来安装锁文件/构建产物必须重新生成及审计。

补充原始通知位于 `licenses/native-media-20261102/`，有来源与哈希清单：libjpeg-turbo 3.1.0、FreeType 2.13.3（选择 FTL 路径）、LittleCMS 2.17、libwebp 1.5.0、OpenJPEG 2.5.3、zlib-ng 2.2.4、libtiff 4.7.0。FreeType 的版权确认及这些库的 NOTICE 仍应随未来获准载荷保留；没有许可付费或源码公开行为。

参考原始依据：[MF Source Reader](https://learn.microsoft.com/en-us/windows/win32/medfound/source-reader)、[MF 帧率转换控制](https://learn.microsoft.com/en-us/windows/win32/medfound/mf-xvp-disable-frc)、[tqdm LICENSE](https://github.com/tqdm/tqdm/blob/master/LICENCE)、[certifi LICENSE](https://github.com/certifi/python-certifi/blob/master/LICENSE)。准确图像库版本来源以本目录 `SOURCES.json` 固定 tag URL 为准；NumPy/SciPy 判断以本机实际捆绑许可证为准。

## 未来分发放行前缺项

1. 完成 Intel 基线对齐的 WPF GUI，以及真实 IDS 全量/增量和回滚测试。
2. 替换 RF 数值库及可选导出链中的禁止组件；不得仅以未触发某个 import 放行实际捆绑文件。
3. 对最终 Python、.NET、原生 DLL、字体/图标、预训练权重逐文件固化来源、哈希、版权与通知；本轮尚无最终 GUI/载荷，因此全量闭包仍 UNVERIFIED。
4. 验证干净 Windows 的系统编解码能力，确定无需付费扩展的格式支持边界；验证 GPU DLL 合法再分发清单。
5. 增加 WPF/Worker IPC 权限、数据目录 ACL、导出权限和正式部署隐私验证。现有 Python 离线保护不替代 OS 级安全边界。
6. 技术与许可门槛分别验收，用户批准解除冻结前不得生成或交付安装包。
