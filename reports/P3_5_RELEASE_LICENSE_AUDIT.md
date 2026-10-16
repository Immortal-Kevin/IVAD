# P3.5 NVIDIA 展示版再分发核查

2026-10-16。结论：**BLOCKED / 许可发行方案未确认**。用户本轮明确批准一次性安装包制作，同时要求无法确认合规发行时停止正式分发；补充答复为暂无Ultralytics授权或已批准AGPL发行方案。

这不等于裁定AGPL禁止商业使用，也不等于裁定同一法人内部复制一定构成对外convey。本轮没有明确接收主体、合同授权、项目发行许可及对应源码履约方案，不能把内部使用作为自动免责，更不能擅自将公司项目开源或购买许可。停止正式构建/分发，不通过删许可证、换进程或让用户自行下载来规避。

## 已核实组件

|组件|当前实际版本/证据|发行前待闭合|
|---|---|---|
|Ultralytics|8.4.176；METADATA为AGPL-3.0，dist-info含licenses|项目/接收范围适用的授权或经公司批准的AGPL履约方案；自训/预训练权重逐项确认，不因未捆绑权重而自动消除代码许可问题|
|PyAV/FFmpeg|PyAV15.1.0；avcodec61.19.101；实际DLL license返回LGPL version3 or later，configuration同时有--enable-libx264/--enable-libx265|确认准确构建来源、相关编码库下游授权及对应源码/构建资料；不能只凭LGPL字符串判定整个二进制可随意再分发，也不能仅凭x264名字断定一定无合法商业授权|
|Qt/PySide6|6.8.3；安装元数据LGPL-3.0-only OR GPL-2.0-only OR GPL-3.0-only|实际捆绑模块清单、许可证/通知、对应源码/获取与替换机制、第三方条款逐项核对；不是必须购买Qt商业许可，但LGPL履约材料尚未完成|
|PyTorch/torchvision|2.9.1+cu128 / 0.24.1+cu128|许可证/通知与实际随包CUDA/cuDNN等组件清单及再分发许可，不能把整个开发venv复制作为审计|
|ONNX Runtime GPU|1.24.4|ORT通知及所含/外置CUDA依赖的实际发行清单，Provider存在不等于安装版GPU已验收|
|安装工具/Windows运行库|已有PyInstaller6.22.3；本轮PATH未发现ISCC/makensis|后续选择必要安装器后核对官方来源、许可和运行库；本轮没有安装新工具|
|项目自身与模型|仓库根目录未见LICENSE文件；用户确认暂无已批准发行方案|不代公司声明AGPL，也不将测试1号/权重/私人视频放入包|

PyAV具体DLL为avcodec-61-1306a7df8fab62262dd7797a8fb9f1cc.dll，SHA256 86b100542ee64b8809704c0229cc2680c785102dfe1acce48fddb6216ebd4dd3，原始配置见artifacts/p35-release-audit-20261016/video-license.json。没有重编译、替换或下载解码库。

## 官方核查资料

- [Ultralytics许可说明](https://www.ultralytics.com/license)：供应商说明包含开源及Enterprise路径，并涉及私有内部应用/自训模型；这是供应商立场，具体适用应结合安装版本许可、实际组织范围及合同核查。本轮未把其网页解释当作最终法律裁定。
- [Ultralytics AGPL正文](https://www.ultralytics.com/legal/agpl-3-0-software-license)：完整条款与对应源码义务应评审，不能仅附NOTICE就宣称履约。
- [FFmpeg官方许可说明](https://www.ffmpeg.org/legal.html)：应核查实际启用组件与构建配置，不只看PyAV包自身许可。
- [Qt for Python 6.8许可证](https://doc.qt.io/qtforpython-6.8/licenses.html)及[Qt LGPL义务](https://www.qt.io/development/open-source-lgpl-obligations)：审计使用的具体模块及第三方材料。

以上为发布门禁核查，不替代公司法律意见。未联系供应商、提交公司信息、购买授权或公开源码。

## 恢复条件

公司明确采用适用合同授权，或确认适用的开源/内部发行合规方案；同时闭合FFmpeg/Qt/实际NVIDIA运行库的发行材料。之后重新明确授权打包，并执行完整安装版验证。授权解决不自动等于技术测试通过，也不会自动恢复构建。
