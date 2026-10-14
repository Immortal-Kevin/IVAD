# P2 下拉菜单样式修复

日期：2026-10-14（Asia/Shanghai）。基于 f0814ed 增量修复，仅 P2；无训练、推理、报警或 P3–P6 开发。

## 实现

原全局 QComboBox 只指定白底边框，未覆盖 QAbstractItemView popup 的背景/字体/高亮；系统深色调色板可使展开列表低对比。标注属性容器另有过宽 QWidget 局部样式，现限定为 QWidget#annotation_properties，不再覆盖所有子控件背景。

统一 style.py：本体白底 #ffffff / 深字 #203047；popup 同色；hover/selected 浅蓝 #d6e8ff / 深字；禁用 #f0f3f7 / #738092；焦点及悬停边框 #6690c5。以 Qt 逻辑像素设 padding/min-height，未设固定物理像素高度，不改系统主题或 DPI。沿用微软雅黑 UI 中文字体。

## 真 GUI 验证

在最终真实录像独立批次中：标注工具、目标类别、审核状态、整帧标签、整帧故障类别、ROI作用域、来源筛选、工作空间、视频 COPY/REFERENCE、播放倍速、抽帧方式/格式、片段标签/故障/审核、数据集策略/格式、设置页等共 20 个实际 QComboBox。

100% 和 200% QT_SCALE_FACTOR，每档分别以 light/dark 基础 QPalette 验证，均 1 passed；每档 40 条控件/主题记录，共 80 条，非 80 个独立 pytest 用例。展开真实 Qt popup，鼠标移动到项目，检查 selected 高亮，保存 popup、禁用本体及整页截图；未改变选择值。实际 popup palette Base=#ffffff、Text=#203047、Highlight=#d6e8ff、HighlightedText=#203047。全局样式无需逐页面重复实现。

截图与尺寸/颜色记录：artifacts/p2-workflow-fix-20261014/style-scale-1/ 和 style-scale-2/。重要菜单另见：

| 控件 | 真实 popup |
|---|---|
| 标注工具 | [截图](../artifacts/p2-workflow-fix-20261014/popup-tool.png) |
| 审核状态 | [截图](../artifacts/p2-workflow-fix-20261014/popup-review.png) |
| 整帧标签 | [截图](../artifacts/p2-workflow-fix-20261014/popup-image_tag.png) |
| 整帧故障 | [截图](../artifacts/p2-workflow-fix-20261014/popup-image_label.png) |
| ROI作用域 | [截图](../artifacts/p2-workflow-fix-20261014/popup-roi_scope.png) |
| 来源筛选 | [截图](../artifacts/p2-workflow-fix-20261014/popup-source_filter.png) |

实际截图中文字、边框、项目高亮可读；标注工具长中文未截断。100%/200% 测试是进程 Qt 缩放，未修改 Windows 显示设置；跨显示器混合 DPI、其他 Windows 主题/远程桌面 NOT TESTED。Windows COM 异常诊断见测试报告，不能以通过用例宣称消除该异常。
