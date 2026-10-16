# THIRD PARTY LICENSE AUDIT

IVAD Platform P3.5，2026年10月16日。范围：当前本机依赖、P2 Lite与NVIDIA Worker差异、可复现构建准备及内部隔离探针。

**审计与构建方案准备已完成；正式可分发版本仍未准入。** 用户已明确：暂无Ultralytics Enterprise授权，亦未批准AGPL开源发行方案；允许内部构建测试与隔离验证，不向领导交付安装。没有购买许可、对外发送、改变项目许可、删除既有声明或绕过义务。

本报告区分“已完成审计动作”和“已履行最终分发义务”；后者不能仅因发现一个LICENSE文件而判为满足。内部是否构成特定条款下的convey、接收人员是否属同一法人及合同范围，须由公司确认；不武断断言内部一定免责，也不把AGPL等同禁止商业使用。以下为技术合规准备，不替代法律意见。

## 1. 核查方法与证据

从3个现有隔离环境读取实际distribution METADATA、Requires-Dist、默认环境marker、RECORD文件和许可文本；不安装包，不扫描其他大型项目。脚本scripts/audit_release_dependencies.py可复跑到新的唯一目录。

|环境|默认依赖闭包|本机许可/通知审计副本|原生DLL/PYD条目|
|---|---:|---:|---:|
|GUI .venv-p1|14个包|19份|505|
|CUDA .venv-nvidia|45个包|93份|123|
|构建 .venv-distribution|21个包|44份|505|

三组总计62个不同name/version对、156份包许可副本，副本hash逐项符合原读取值；Python LICENSE.txt另存。没有默认依赖缺项；3环境pip check均返回0，无已声明依赖冲突，原始pip-check.json保留。重复包/许可在不同环境分别留存，不能把条目数当作不同软件数量。505条包括完整PySide6依赖的许多未用模块，并不意味着安装版将全部收集。

证据根artifacts/p35-compliance-plan-20261016/verified，含各环境inventory.json、requirements-installed.txt、未修改的notices/及verification.json。62个版本对摘要见packaging/nvidia/dependency-license-summary.csv。清单不是最终payload BOM，不包含所有运行时动态加载/可选extras的最终证明；审计副本不作为公开发行包。

## 2. 实际版本与许可状态

|组件|实际版本 / 本机声明|已核实或保留|尚未闭合的发行义务及处理|
|---|---|---|---|
|Ultralytics|8.4.176，AGPL-3.0|原完整LICENSE副本及hash、metadata|公司需确认适用合同授权或批准的AGPL履约路径及接收范围；本项目源码、构建脚本及模型涉及范围需评审；不自作开源决定|
|Ultralytics平台/THOP|ultralytics-platform0.1.84 AGPL-3.0-only；ultralytics-thop2.2.2 AGPL-3.0|均是当前Worker默认依赖，许可证已保留|不能只处理主包许可而遗漏二者；企业授权是否覆盖须按合同核对，不能推断|
|PyTorch|2.9.1+cu128，BSD-3-Clause|本机LICENSE/NOTICE已保存；LICENSE含其他项目文本|保留版权/免责声明/不背书条款，按实际payload保留全部相关第三方通知；BSD不自动覆盖CUDA/cuDNN二进制|
|torchvision|0.24.1+cu128，BSD|2份许可记录|保留其第三方声明，核实最终编解码DLL，不能仅保留torch的LICENSE|
|ONNX Runtime GPU|1.24.4，MIT License|onnxruntime/LICENSE与ThirdPartyNotices.txt完整副本|最终包必须随附这些文本；CUDA/cuDNN仍独立核查，Provider存在不是GPU节点已执行|
|ONNX|1.20.1，Apache-2.0|LICENSE副本|按Apache条款保留许可/通知及修改说明，核对其protobuf等依赖；不改变原有专利/商标条款|
|PyAV|15.1.0，BSD-3-Clause|PyAV LICENSE及作者材料副本|PyAV自身许可不能代替FFmpeg及其codec的许可核查|
|GUI FFmpeg|libavcodec61.19.101、avformat61.7.100、avutil59.39.100|实际DLL返回LGPL v3 or later，构建配置含libx264/libx265；hash与上轮相同|准确构建来源、两个codec授权、相应源码/构建材料及可替换机制未闭合。LGPL字符串不足以判定整个库权利，也不能仅凭codec名断定无商业授权|
|OpenCV/另一FFmpeg|opencv-python5.0.0.93（cv2报告5.0.0），Apache2.0；内置FFmpeg avcodec61.19.100|cv2/LICENSE及LICENSE-3RD-PARTY各副本；实际build info|Worker也带视频库，不能仅审GUI PyAV。核对本wheel FFmpeg版本、通知和适用源码提供义务，未因为当前只读图片就删除它|
|PySide6/Qt/shiboken|6.8.3；metadata LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only|4个wheel的现有LicenseRef-Qt-Commercial.txt副本|该文件不证明公司有商业授权；本轮从这些wheel的RECORD未找到完整LGPL文本。选择适用许可、补完整文本/对应源及通知、确认Qt模块条款、允许必要替换/调试；onedir动态DLL不等于义务已全部满足|
|Python|3.12.14，现有基底LICENSE.txt|原文本副本及python.exe/python312.dll观察hash|核对基底来源、附带库和CRT条款；官方3.12.14没有Windows二进制安装器，不能编造embed包来源或拿当前venv作可移植包|
|CUDA/cuDNN|torch.version.cuda12.8，cuDNN DLL9.10.2.21|列出实际torch/lib DLL；设备历史与本轮张量探针|逐DLL核对NVIDIA对应版本EULA/可再分发清单和通知，不捆绑驱动/整个Toolkit，不以torch BSD替代这些条款|
|NumPy/Pillow/PyYAML|GUI2.2.5/11.2.1/6.0.2；Worker2.5.4/12.3.0/6.0.3|分别按本机文本保存；NumPy包含复合许可|两环境分别固定，保留bundled BLAS等相关文本，不简写成全BSD即免责|
|PyInstaller|6.22.3，GPLv2-or-later带输出/bootloader例外；hooks2026.8|本机许可材料已保存|例外不消除被打包组件义务；输出不因使用PyInstaller就自动成为GPL，不能据此改变IVAD许可|
|安装器/Windows CRT|NSIS3.12仅候选、未下载；CRT非本轮新依赖|目前未安装新工具或捆绑CRT|安装器/插件和实际CRT若加入需单独列明来源hash/许可证；不把候选写成已验收|

其余实际闭包包（科学计算、HTTP客户端、数据库、序列化等）的name/version、声明和许可文件数均列在CSV。对字段为空或无本机许可文本者，状态仍为待核查，应取对应官方版本原文；不是仅主表组件才需遵守义务。

## 3. P2 Lite 与 NVIDIA Worker 差异

- P2 spec包含Qt/PyAV/数据库，明确排除torch/torchvision/onnxruntime/Ultralytics；冻结程序默认lite=True，训练/推理job不注册，应用名仍P2Beta。
- Worker还需科学计算、ONNX导出、ORT、Ultralytics平台/THOP及CUDA原生DLL。GUI NumPy2.2.5与Worker2.5.4，Pillow11.2.1与12.3.0，YAML6.0.2与6.0.3，不可直接合并锁文件。
- 服务当前通过Python -I -X utf8运行脚本，默认查.venv-nvidia；冻结EXE不能机械接受这些解释器参数。独立Worker可复用原main/JSON协议，但需薄入口和路径适配。
- Worker锁写脚本根/runtime，安装到只读Program Files会有权限风险；应统一改为明确可写锁位置并测试多实例。默认基础权重位于artifacts/p0，正式包不能偷偷带入或自动下载未授权权重。
- torch/lib实测53文件、4,427,383,390字节；全GUI依赖还有大量不用Qt模块。应按payload收集及测压缩上限，不能用旧Lite大小推断完整安装器。

详见packaging/nvidia/BUILD_PLAN.md；本轮没有修改这些业务入口或GPU引擎。

## 4. 哪些已满足，哪些未满足

|事项|当前状态|证据/后续动作|
|---|---|---|
|本机版本与默认依赖闭包审计|已完成此审计步骤|3份inventory，无缺项；不能替代最终freeze依赖分析|
|原许可声明不被删除/修改|已遵守本轮要求|156份审计副本hash通过；未动venv声明|
|适用版权/通知材料收集|部分完成|已保存本机存在的文本；最终NOTICE组合、缺失文本/精确来源仍待补|
|Qt/FFmpeg对应源码与重链接/替换方案|未闭合|按最终二进制版本准备源码/补丁/配置与履约途径；仅放官网链接不自动满足|
|Ultralytics授权或AGPL方案|未确定|由用户/公司决策，含平台/THOP范围；无自动购买或开源|
|NVIDIA/CRT实际再分发边界|未闭合|逐DLL与EULA/分发包相配对，不是检查torch主许可即可|
|冻结完整输入与离线重建|部分准备|已固定installed版本，尚缺wheel哈希lock、Python构建基底归档、最终spec/安装脚本和编译器hash|
|内部独立进程验证|PASS，限定现有venv|PYTHONPATH放明确失败夹具，-I成功忽略；真实16元素CUDA张量通过，原始isolated-probe.json|
|内部冻结EXE/安装包、干净系统|NOT TESTED|本轮不必为审计生成大包，未声称干净Windows通过|
|正式分发准入|未解除|不以新增审计文件代替公司授权及上述履约|

“已完成材料收集”不是“所有许可义务已履行”，没有给出合规认证结论。

## 5. 可行处理方案

1. **适用商业/研究合同路径**：由公司核实或取得适用于IVAD当前内部研发、测试人员及未来分发范围的合同授权；确认版本、模型、平台/THOP、期限及接收者范围。项目不因此自动免除其他依赖义务；本轮不联系供应商或代购。
2. **公司批准的AGPL路径**：公司先评审IVAD及组合代码/模型适用范围，形成接收范围、源码/修改/构建/许可通知的完整履约方案，再批准实际交付方式。不能默认必须公开全部企业数据，也不擅自发布代码、模型或私人录像。
3. **现阶段仅受控内部研发**：保存本轮审计和内部测试证据，由公司确认适用范围；不得伪装正式可分发版或交领导安装。不同法人/承包方/外部测试不能自动视同同一组织。
4. **视频依赖闭合**：优先核实当前构建的真实上游来源和对应源码；如无法闭合，可另行评审有清楚许可链的构建/codec组合。替换后须重新验实际MP4/AVI/MKV/MOV/TS/M4V及片段保存/回放，不能悄然移除编码能力却宣称兼容。
5. **Qt及基础库材料**：动态可替换部署、补完整适用文本/第三方通知、提供适用源码/获取机制并核实限制；若无法满足选定开源路径，再由公司考虑其他适用授权，不预设必须购买Qt商业许可。

## 6. 官方依据与本机原件

核查日期2026-10-16。网页用于辅助理解；实际安装版本文本/合同及最终分发事实仍应逐项评审。

- [Ultralytics供应商许可说明](https://www.ultralytics.com/license)及[AGPL正文](https://www.ultralytics.com/legal/agpl-3-0-software-license)：区分开源与合同路径；网页说明不代替公司法律判断。
- [PyTorch v2.9.1 LICENSE](https://github.com/pytorch/pytorch/blob/v2.9.1/LICENSE)：主许可及通知保留；本机文件另含组合第三方文本。
- [ORT v1.24.4 LICENSE](https://github.com/microsoft/onnxruntime/blob/v1.24.4/LICENSE)：MIT；对应第三方通知使用本机原件，不拿main最新文本冒充该wheel。
- [FFmpeg许可说明](https://www.ffmpeg.org/legal.html)：具体构建可因启用组件而不同，需核实codec来源。
- [Qt for Python6.8许可](https://doc.qt.io/qtforpython-6.8/licenses.html)及[Qt LGPL义务](https://www.qt.io/development/open-source-lgpl-obligations)：核实实际模块/履约，不因onedir就结束审计。
- [CUDA12.8 EULA入口](https://docs.nvidia.com/cuda/archive/12.8.0/)及[cuDNN9.10.2许可](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html)：最终所用runtime的单独权利与条件，不由torch BSD覆盖。
- [Python3.12.14发布页](https://www.python.org/downloads/release/python-31214/)：source-only，官方说明3.12.10为最后带二进制安装器的3.12完整修复版；没有在本轮降级。
- [NSIS官方下载](https://nsis.sourceforge.io/Download)及[许可](https://nsis.sourceforge.io/License)：3.12作为待核实候选，不是已安装构建工具。

## 7. 停止条件

用户决定授权方案前不进行正式交付，不向领导安装。可复现方案和输入模板已准备但尚非完整封存/已成功重建的发行流水线。未生成EXE/Release ZIP、未新训练、未更改Python/CUDA/驱动、未进P4–P10。PACKAGING_FREEZE=TRUE；一次性正式打包授权仅在合规条件满足后按用户确认继续，完成后再次恢复冻结，不因后续源码修改自动构建。
