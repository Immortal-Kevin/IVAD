# P3.7-D Lite：最后三项许可整改结论

2026-10-19；基线 `6e5a48753928461273b6723261012bf42fc499a3`。只适用于北京金海泽地智能科技有限公司同一法人内部研发演示，原授权无需重批。本文件是证据核对，不是法律认证。原功能测试 PASS 继续有效；未运行 GUI、构建、编译、全量 SBOM 或 GPU 测试。

**结论：三项不能机械地继续按“完整源码缺失”阻断；本轮补充材料已准备，但以下确切证据仍 UNRESOLVED，未批准发送。没有证据证明必须改变任何现有二进制。**

许可材料在 `legal/P37D_LITE_LAST_THREE/`，未加入或改动冻结候选目录。原始报告不覆盖，本补充纠正其适用范围；`DISTRIBUTION_STATUS=BLOCKED`、`PACKAGING_FREEZE=TRUE` 不变。

## 1. FFmpeg 七 DLL

**A — 实际条款。** LGPLv3 通过 GPLv3 的第0、2、6节区分内部运行/复制与向其他主体传递；LGPLv3 第4节规定向接收方提供组合程序时的许可、替换及源码安排。[GNU 官方内部复制解释](https://www.gnu.org/licenses/gpl-faq.en.html#InternalDistribution)明确同一组织内部复制不属于对外分发。因此，当前已确认的同法人内部演示，不能仅因没有全部静态库源码即认定必须重编译或公开 IVAD。未来对外传递时才需针对具体 GPL/LGPL 版本提供对应源码、构建/修改材料及适用的链接安排；MIT/BSD/Apache/FTL 一般要求相应版权、条款、免责声明、适用 NOTICE，而非一概交源码。MIT 的“所有副本”条件应保留，不用内部使用豁免一切通知。

**B — 已满足。** 七 DLL 的原 SHA、BtbN 包校验及原 FFmpeg 配置继续复用；固定 FFmpeg 源码 `1fdbca85…` 和构建脚本 `a99e8230…` 均已在本地，本轮未重下。已从现有脚本归档提取脚本、变体和全部4份补丁（AOM 1份、aribb24 3份）；49个配置功能与对应脚本逐条建材料映射，另保存传递依赖原通知。FFmpeg 自身主源码已取得，不等于所有静态库源码已取得；索引明确区分。

重要纠正：`50-chromaprint.sh` 指定 `FFT_LIB=fftw3` 和 `-lfftw3`；`avformat-61.dll` 含1017处 `fftw` 字节匹配。固定 FFTW 源码的 COPYRIGHT 授权 GPL-2.0-or-later，Chromaprint 自己也提示需考虑 FFT 库条款。故不能称整个载荷所有静态依赖都是 LGPL。该证据不推导本次内部使用必须公开源码，也不把 GPL 的内部使用禁掉。

**C — 确切缺项，UNRESOLVED。** 上游包未附实际静态链接对象/归属清单和完整第三方通知汇编。需补与本包 SHA 对应的通知清单，重点是 shaderc 的 glslang/SPIRV-Tools、libjxl 的 Highway、rav1e 实际静态 Rust 依赖，以及 GCC/libstdc++/libgomp/MinGW 所带内容的例外/版权材料；LAME、libiconv、soxr 的固定版本原通知仍未完整取得。已有顶层 LICENSE 不能自动覆盖这些内部组件。49条映射不能替代逐 DLL 链接图；不将“脚本中能构建”一律写为“对象确实进入七 DLL”。

**D/E — 最小动作。** 优先从 BtbN 对应构建产物/维护材料取得上述第三方归属及 LICENSE/NOTICE，复用已取得原文补齐即可；本次内部使用不要求为此重新编译，也不要求补齐所有静态库完整源码后才演示。对外传递的源码闭包另为未批准事项。FreeType 的使用致谢已准备于 `SUPPLEMENTAL_NOTICES.txt`；不宣称 OpenH264 的源码构建享有 Cisco 官方预编译二进制的专利安排。编码专利与版权分开，当前未证明需购买许可。

**F — 如需咨询的具体问题。** 若准备超出同法人范围，须重新核对 FFTW 等的组合许可证及对应源码安排；本次不申请扩大范围，也不要求法务确认泛泛的“全部 FFmpeg 合法”。

## 2. VC Runtime 11 DLL

**A — 实际条款。** [Microsoft Runtime EULA](https://visualstudio.microsoft.com/license-terms/vs2022-cruntime/)第1节给予不限副本的安装和使用权；第3节另有限制分享、为他人组合提供、向第三方转移等规定。这不是通用再分发授权。[Visual Studio 2022 REDIST](https://learn.microsoft.com/en-us/visualstudio/releases/2022/redistribution)允许符合其软件许可的主体随程序带未修改的 `VC/redist` 文件；[官方说明](https://learn.microsoft.com/en-us/cpp/windows/redistributing-visual-cpp-files)将再分发与有效 Visual Studio 许可相联系。开发者使用 VS Code 或 DLL 带有效签名均不自动证明获得该再分发权。

**B — 逐项匹配。** 以下均为 Windows x64 v14 release CRT 文件族，非 DebugCRT；精确 SHA 沿用原 CSV，并在 `VC-signatures.json` 逐条对应。签名本轮全部 Valid，签名方不等同于许可授予方。Microsoft REDIST 为目录规则，不是这11个哈希的官方签名白名单。

| 实际相对路径（均位于 `_internal/`） | 版本 | 原包 / 签名方 | 已能匹配 / 尚缺 |
|---|---|---|---|
| numpy.libs/msvcp140-263139962577ecda4cd9469ca360a746.dll | 14.40.33810.0 | NumPy2.2.5 / Microsoft | MSVCP140家族；原包传递授权未证明 |
| PySide6/MSVCP140.dll | 14.39.33520.0 | PySide6 Essentials6.8.3 / Qt | 同上 |
| PySide6/MSVCP140_1.dll | 14.39.33520.0 | 同上 | MSVCP140_1家族；同上 |
| PySide6/MSVCP140_2.dll | 14.39.33520.0 | 同上 | MSVCP140_2家族；同上 |
| PySide6/VCRUNTIME140.dll | 14.39.33520.0 | 同上 | VCRUNTIME140家族；同上 |
| PySide6/VCRUNTIME140_1.dll | 14.39.33520.0 | 同上 | VCRUNTIME140_1家族；同上 |
| shiboken6/MSVCP140.dll | 14.39.33520.0 | Shiboken6.8.3 / Qt | MSVCP140家族；同上 |
| shiboken6/VCRUNTIME140.dll | 14.39.33520.0 | 同上 | VCRUNTIME140家族；同上 |
| shiboken6/VCRUNTIME140_1.dll | 14.39.33520.0 | 同上 | VCRUNTIME140_1家族；同上 |
| VCRUNTIME140.dll | 14.44.35211.0 | Python基座 / Microsoft | VCRUNTIME140家族；已有Python Windows附加条件，但未单独列明外置DLL传递权 |
| VCRUNTIME140_1.dll | 14.44.35211.0 | 同上 | VCRUNTIME140_1家族；同上 |

**C — 确切未决问题，UNRESOLVED。** 在“公司作为许可使用主体、只向该公司员工电脑部署”事实下，Runtime EULA 第1节与第3节的适用关系尚未获得明确的供应方说明或法务条款判断。现有原包没有找到足以单独证明这11份文件可向第三方再次分发的授权；不能用 NumPy BSD 或 Qt LGPL 代替 Microsoft 条款。这个未决点不是“DLL真假不明”或“要重编译全部Python”。

**D/E/F — 最小动作。** 仅请负责许可证的人员回答一个问题：**公司作为现有 Runtime 许可使用主体，将这些未改文件部署到本公司员工电脑，是否落在 EULA 第1节的内部安装使用，而非第3节的向他人/第三方提供？** 若认可此适用，留存该条款判断及官方 EULA 即可，无须为这次内部使用另证对外发行权。若不认可，再提供公司现有适用的 Visual Studio 许可/REDIST 权依据，或 Qt/NumPy/Python 供应方对这些原包文件的传递条件；不是要求购买许可或重新编译。官方 Runtime EULA、原 DOCX 和 REDIST 页面均已保存，单纯增加 NOTICE 不能创造缺失授权。

## 3. CPython3.12.14

**A — 实际条款。** PSF License v2 第2节允许保留许可及版权的源码/二进制复制与分发，第3节要求修改所形成派生作品附修改摘要；没有“必须使用PSF官方Windows二进制”或“必须交全部构建源码”条件。expat/libffi/libmpdec等按各自宽松条款保留文本，OpenSSL 按 Apache-2.0 第4节保留适用材料。[官方3.12.14发布页](https://www.python.org/downloads/release/python-31214/)明确该版本是仅源码发布，没有官方 Windows 安装包；不能要求提供不存在的官方同哈希 EXE。

**B — 已满足。** 现有 `python312.dll` 版本3.12.14，Valid 签名方 OpenAI OpCo, LLC；`sys.version` 为2026-08-25自建MSC1944版本。来源可追至现有 Codex runtime 基座，不是未知目录文件，也不是 PSF 官方构建。现有完整 `CPython-LICENSE.txt` 已有历史许可、bzip2 和 Windows Microsoft 附加条件；补充准确官方v3.12.14许可、Doc/license.rst及expat/libmpdec/HACL/SipHash等通知，保留现有准确OpenSSL3.5.8 Apache文本。读取到expat2.8.3、zlib1.3.2、libmpdec2.5.1、bzip2字符串1.0.8；补取zlib1.3.2许可。无需因此重建Python或Qt。

**C — 确切缺项，UNRESOLVED。** 官方源码PCbuild默认依赖与当前基座不同（如官方脚本zlib1.3.1/OpenSSL3.0.16，当前为1.3.2/3.5.8），不能把官方脚本当本基座构建证明。当前 `libffi-8.dll` SHA `9034f55f…` 与CPython公开3.4.4依赖的 `eff52743…` 不同，PE代码段也不同；“只是重签名”未获证实。需基座提供方给出 **libffi的版本及适用版权/许可、静态liblzma的版本/适用许可，以及若修改了CPython则相应修改摘要**。后两项不需要完整构建环境或可复现构建；不同哈希本身也不是禁止使用证据。

**D/E/F — 最小动作。** 已保存libffi3.4.4的MIT及liblzma旧版公有领域/新版0BSD文本作对应候选，但不冒称已证明本二进制版本。取得上述短清单/通知及必要摘要后只补材料即可；PSF、MIT、0BSD本身不要求重新编译。只有供应方证明存在无法满足的额外限制，才讨论最小替换；目前不提出替换，不推定需要商业许可。

## 完成边界

下一步只有：补FFmpeg实际传递组件的通知归属；完成上述一项Microsoft条款适用判断或补已有授权链；取得Python基座的上述小范围依赖/修改说明。前三项均不能伪报PASS。补充目录尚未成为已闭合交付许可包。

未修改候选目录任何文件、EXE或DLL；原384项SHA清单逐项核验不变，EXE SHA仍为 `e0822ff177caad959283ba692362a510909a30c2645811172b52f82cf451b8f5`。核验结果在补充材料 `unchanged-payload.json`。原数据、环境、两份未跟踪规划文档及历史Qt结论未改。未重新打包、重跑GUI、下载已有Qt/FFmpeg源码、上传或发送任何材料，完成后停止。
