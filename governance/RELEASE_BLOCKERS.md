# 尚未解决的重要阻断

## Annotator — NOT VERIFIED

1. 2026-10-26用户仅授权一次Annotator本机Windows x64便携测试包交付；授权状态：CONSUMED_FROZEN。签名、公开发布、Full及后续新版打包不在授权内；常规冻结保持。无安装程序，安装/升级/卸载NOT TESTED。
2. 尚未在干净Windows10/11、AMD/NVIDIA机器验证；已有本机独立TEMP目录便携EXE执行记录（PASS）；其他电脑未实测，Windows OS媒体/运行库先决条件尚未跨机器验收。
3. 真实鼠标完整流程仍为NOT TESTED：此前启动、本轮读取已打开窗口均被工具审批拒绝，原文分别见evidence/windows_gui_attempt.json、evidence/windows_gui_ui_revision_attempt.json。本轮标准标题栏、主目录、工具栏、审核后换帧、IDS命名已实现；WPF内部控件和合成尺寸/DPI渲染不代替真实屏幕/鼠标验收，真实响应/关闭取消仍待验收。
4. 后台流式hash/复制/IDS交换、进度/取消、范围抽帧、矩形与多边形/ROI编辑已实现，服务层与实际子进程回归已通过。AVI、MP4/H.264、MOV、MKV、HEVC、VFR及30分钟1080p合成视频已实测；不代表高码率25/30fps监控视频、全部容器变体或跨机支持。
5. 真正断网/网络拒绝、断电/任意时刻崩溃恢复、海量数据、跨版本迁移、缩放平移、完整撤销重做、复杂多边形拓扑、冲突合并UI仍未验收或未实现。进程硬终止与资产移动/日志写入之间仍有极小的孤立文件窗口；不自动清理未知历史任务或业务文件。应用无网络API的静态检查不能替代运行时网络审计。

## Full / NVIDIA — BLOCKED

1. RF-DETR1.11.2[train]递归候选中存在B.1未允许许可。tqdm4.70.1实际wheel为MPL-2.0 AND MIT，certifi2026.10.23为MPL-2.0，不能简单选择MIT分支。未安装。
2. PyTorch2.14.1声明包含BSL-1.0与LLVM-exception组合；NumPy2.5.4还存在0BSD/Zlib/CC0声明及已实证Windows wheel GCC runtime GPL例外；SciPy和其他二进制内嵌库需逐工件审查。不能顶层BSD/MIT一票通过。
3. supervision0.31.2自身MIT，但传递绘图/图像/科学计算依赖未整体合规；其实际Detections/可视化调用已定位，不可盲目卸掉而声称训练仍可用。
4. 官方权重虽有Apache指定，具体文件未下载/校验、NVIDIA硬件与CUDA/SDK再分发未验证；训练不启用。

## 已自动解决和可行后续路径

标注端自主改用Windows内置运行组件和自研IDS/GUI，完全隔离训练许可问题；旧受限模型、NumPy GPL runtime、旧OpenCV/绘图/build副本已清理。使用本机媒体解码避免引入未经审查FFmpeg构建。

Full后续无需先申请许可例外：优先从固定Apache RF-DETR核心提取本地训练调用，去掉不需要的联网下载/Roboflow路径；以自研进度输出替换受限tqdm调用，并用OS证书信任的本地工件交付替代certifi下载路径。这些替换必须覆盖transformers等传递调用并跑训练回归，当前仅完成调用审计与阻断接口，未声称替换已完成。

科学计算可评估经审查的MSVC构建且不携带GNU runtime的NumPy/相关库，以及更小的COCO/图像依赖链；这是可研究替代路线，不是已取得合规二进制。本轮不通过伪造包元数据或删除许可证让训练“通过”。无需用户当前批准例外，证据缺口保持阻断。

专利、素材/商标权利及合同边界独立登记；不能由自动许可证扫描消除。

## 本次便携测试交付证据

见evidence/portable-audit.json、portable-independent.json及windows_gui_portable_attempt.json。受控测试已验证在写完临时清单、原子替换前硬终止后恢复最后提交数据；不等于真实断电或任意资产阶段零丢失。纯4.8系统、其他电脑/显卡、物理快捷键仍NOT TESTED。
