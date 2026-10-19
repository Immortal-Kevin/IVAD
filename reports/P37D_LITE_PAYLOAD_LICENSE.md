# P3.7-D Lite 实际载荷许可

日期：2026-10-19。范围仅北京金海泽地智能科技有限公司同法人研发部内部演示；接收方授权已确认，不再要求重复确认。本轮遵循新的Lite授权，先生成本机候选再审实际载荷。

源码/构建提交：`26dd8bcf10490384bcb993df4e0d38d35a9f9f8a`（其父工程提交`3fff1f734a2454f501a5b695f1adb8b76827a9aa`）；最终报告提交由本报告所属Git提交确定，提交后回执`artifacts/p37d-lite-20261019/closeout.json`和最终回复记录完整SHA。分支`feature/p37d-lite-demo`，基线`8b064b5e5fa8711e75293f189266aad99d92c502`。

**PAYLOAD_LICENSE_STATUS=BLOCKED。可保留本机候选，不可发送，不制作可交付ZIP。** 只审本次实际载荷，不要求先处理未来RF GPU Worker或187条全环境依赖。

实际文件384项，PE原生文件136项，逐文件SHA256、来源和可得文件版本见`P37D_LITE_PAYLOAD_FILES.csv`。136项均有组件归属，不等同再分发权利均闭合。版本资源缺失时留空，不猜测。实际PYZ模块与运行模块/DLL清单留在本轮证据目录。

| 组件 | 已落实 | 仍缺/结论 |
|---|---|---|
| Qt/PySide/Shiboken6.8.3 | 动态DLL白名单；GPL-only未用模块排除；原始许可/版权、127份Qt源内通知及四份对应6.8.3源码归档随候选保留；合法替换/调试权说明；主库未改 | 匹配替代栈的实际启动/完整流程通过，原混版失败保留。属于本次技术履约证据，不等同整包法律批准；见功能报告 |
| PyAV15.1.0 | BSD原文/Authors，36个扩展重新链接和RECORD更新，前后SHA/实际七DLL映射随包 | BSD包声明不转授FFmpeg所有静态依赖权利 |
| FFmpeg七共享DLL | 固定BtbN包发布校验匹配，实际库61.19.101/61.7.103等；配置明确disable-libx264/x265，未启用GPL/nonfree，返回LGPLv3+；DLL未修改 | **BLOCKED**：固定FFmpeg主源码和构建脚本已取得，但静态依赖精确源码/补丁/完整通知与可交付对应安排尚未闭合 |
| Microsoft VC Runtime | 11个实际DLL逐文件SHA/来源和可得版本；来自Qt/Shiboken/NumPy wheel及CPython基座 | **BLOCKED**：每条来源对应的准确再分发条款/传递授权材料未闭合；不因内部使用自动豁免 |
| CPython3.12.14/SQLite3.53.1/OpenSSL3.5.8 | Python完整许可、SQLite声明、OpenSSL准确Apache文本，实际文件/版本/来源列清 | **PARTIAL**：本机基座来自Codex bundled runtime，原构建/捆绑静态库的准确材料仍需补齐；不把PSF许可转授全部第三方DLL |
| Pillow/NumPy/SQLAlchemy/Alembic/Mako/PyYAML/Greenlet/MarkupSafe/typing_extensions | 选择性保留原通知，NumPy包含OpenBLAS/GCC例外等复合文本，Pillow保留捆绑许可 | 已准备现有原文；以实际逐文件矩阵为边界，不能只用“MIT/BSD”一句覆盖所有内部静态库 |
| PyInstaller6.22.3 | COPYING和bootloader例外；未修改bootloader代码，不要求自研应用因此开源 | 不免除其它依赖义务 |
| NVIDIA/Torch/RF/OpenCV/Ultralytics | 实际载荷无相应包/模块/SDK DLL/权重 | 本版不携带，未来GPU运行时不作为当前门禁 |

Qt四份源码已沿用前轮材料，不重复下载。FFmpeg新增取得的主源码commit `1fdbca85aaea513c9cc6c14d347f76543346d3da`及构建脚本commit `a99e8230eae00d1cee38f23076a7a1f55cd984e2`、准确归档SHA在本轮`ffmpeg-source-index.json`；目前留在本地工程证据，不伪称已经完成整个静态闭包。其主源码含上游可选Torch后端包装文件，不是Torch实现/包，未加入候选。

## 内容匹配与零依赖

文件名、PYZ模块、代码常量、文件原始内容、base_library ZIP和公开Qt源码归档哈希/目录均检查。没有Ultralytics包/DetectionTrainer/旧Worker/权重。保留实际内容匹配记录，不删改文字躲扫描：FFmpeg DLL中的libx264/x265字符串来自`--disable-libx264/--disable-libx265`配置；PyAV实际没有该编码器；应用中YOLO字样来自通用格式转换/历史分类和拒绝列表，通知提及Ultralytics表示排除，不是引擎。详见`payload-audit.json`。ULTRALYTICS_FREE_STATUS=PASS（本次候选范围）。

不能从去掉GPL编码器推导所有编码专利已解决；H.264/H.265等独立专利条件与开源版权分别审阅。未证明必须购买商业许可，商业预算保持0；无NVIDIA SDK/训练环境，相关未来审计不阻止本机非AI候选。

下一步可由Codex执行：按固定构建脚本逐项收齐实际启用静态库源码/补丁/通知，或以固定FFmpeg主源码独立构建仅需解码能力、禁用网络/GPL/nonfree及未用外部库的最小共享版本，再重新链接验证；核对11个VC DLL的官方redistributable条款链，必要时换用准确可追溯的官方运行时交付安排；补齐CPython基座原包/第三方材料或在独立环境换用已核清的Windows基座重建。不得以更名、猜测许可、购买默认商业版、公开私有数据或改全局环境替代整改。
