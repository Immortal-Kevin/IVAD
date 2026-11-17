# P2 Annotation Workflow Simplification

日期：2026-10-15；基线 67b415e；Schema 0008；PACKAGING_FREEZE = TRUE。

## 验收结论

本轮功能验收 PASS：最终整组 **69 passed / 0 failed / 0 errors**（74.987 秒），200% 专项 **4 passed / 0 failed**（8.446 秒，重复验证，不增加独立用例数）。初次整套混合运行曾出现一次原生访问冲突，后续分组与整组串行均未复现，根因未确定，作为限制保留，不能宣称已修复该原生故障。

没有 Migration、字段删除、服务/导出/训练执行代码修改、GPU训练、环境安装或软件打包。

## 字段审查

Annotation.payload.objects 是目标检测/多边形真值，payload.image_label_id 是独立整帧分类字段，image_tag 是 NORMAL/ABNORMAL/UNKNOWN；Annotation.status 和历史修订的 DRAFT/REVIEWED/APPROVED/REJECTED 独立保留。Frame.handling 管理软剔除及工作列表状态。来源经 Frame.media_id → MediaAsset.camera_id → Camera UUID；没有按文件名猜测。

YOLO Export Adapter 对无框非正常图片仍拒绝导出检测标签；P3 validator 仍检查审核、来源、冲突和异常无框情况，没有用“已标注”替代准入。

## 修改文件

- `ivad_app/gui/annotation_page.py`：本轮唯一业务 GUI 文件；会话默认类别、右侧布局、历史详情和三种操作。
- `tests/test_annotation_simplification.py`：连续标注、正常穿插、相机切换、多类别、历史信息、无摄像头视频隔离及导出测试。
- `tests/test_p2_workflow_fix.py`、`tests/test_p2_ux_v2_gui.py`：旧夹具绘制前明确选择故障类型，适应“无默认则不预选”的新规则。
- `tests/test_annotation_camera_hotfix_gui.py`：绘制前明确类别；修正旧截图硬编码输出，使用 IVAD_ANNOTATION_EVIDENCE 或测试自身临时目录，避免覆盖历史证据。
- 两份标注 Markdown 指南及当前进度更新。Word/PDF 和旧验收报告不改写。

## 默认故障类别

工作默认类别保存在当前窗口内的 working_labels，键是 `(project_root, camera, CameraUUID)`；无摄像头时键是 `(project_root, media, MediaUUID)`。同摄像头跨视频/片段继续沿用，未关联来源按视频隔离；跨项目不混用。第一次进入一个上下文没有记忆则显示“请选择故障类型”，不会偷偷选第一项。停用类别不能成为新绘制对象的有效类别。

默认值只决定新对象 label_id，不写入下一张图片，不复制坐标，不自动设异常，不影响正常或剔除图。选择、加载已有对象不修改工作默认值或对象数据。已有真实类别在“当前对象”列表及只读汇总中显示；顶部故障类型始终表示新绘制对象的默认值。

同一帧可选择另一类别继续画目标。改变默认值不再直接改当前选中框；如果要编辑旧框，先选对象、选类别，再明确点“修改所选对象类别”。这样不会因默认类别变化静默改写历史。

限制：默认类别仅当前窗口会话记忆，没有实现跨重启偏好持久化；用户允许采用会话实现，本轮未新增设置或数据库写入。

## 两个下拉框与整帧维护

“标注状态”和“整帧故障类别”已从常规布局移除；内部不显示的兼容读写对象保留，不能由操作员手动改完成状态。没有删除数据库字段或历史记录。

完成由现有服务按实际持久化内容计算，列表图标、tooltip 和当前帧信息显示结果。正常无框合法；合法目标或有明确整帧分类的异常可完成；异常无框且无分类不完成；剔除/冲突独立。未保存和保存失败不提前完成，删除有效内容后重新计算。审核与 review_stale 规则不变。

“整帧标签详情…”是维护历史 image_label_id 的独立入口；确认后沿用原自动/手动保存。它不会因目标类别默认值改变而自动覆盖，也不会制造框。无框分类仍是分类真值，不伪装为检测真值。汇总可同时显示多个目标故障及独立历史整帧类别。

## 三种快捷操作与布局

- **保存正常并下一张**：已有异常内容按原流程明确确认并保留修订；本帧无故障对象和整帧类别，不需 ROI；成功才翻页。
- **保存异常并下一张**：保存合法目标或明确的整帧分类；没有这些内容会提示，不自动建框。下一张只保留工作默认类型。
- **剔除并下一张**：选择原因及核对预览，沿用软剔除，保留文件与历史；成功后请求下一张，最后一张没有虚构下一张。

三个带“下一张”的主要按钮始终在成功后请求翻页。待复核保留辅助保存及自动翻页设置；普通“保存标注”允许留在当前图。原快捷接口/快捷键保留兼容，原 GUI 回归与新可见按钮流程均验证。

右侧顺序为当前摄像头、当前处理方式、用于新对象的故障类型、当前对象、只读汇总、必要维护及主要操作；继续浅色主题和原生滚动布局。1080p 已抓取真实截图，200% 下通过滚动访问较低位置按钮，无控件叠加；不宣称小逻辑窗口能同时显示全部内容。

## 测试覆盖

| 要求 | 验证结果 |
|---|---|
| A 连续“8525压滤机 / 压滤板破裂” | PASS，新框类别沿用，下一张初始无框/无异常标签，新坐标与上一张不同 |
| B 正常帧穿插 | PASS，正常帧无框、无整帧类别；后续默认值仍在 |
| C 相机切换 | PASS，另一机位首次不预选；落料口堵煤与压滤板破裂独立记忆 |
| D 历史标注 | PASS，选中已有对象再改工作默认值不改对象/修订；直接切图原数据不变 |
| E 完成状态 | PASS，正常/异常保存、未保存、保存失败、删除、剔除及审核独立回归 |
| F 多类别 | PASS，实际矩形+多边形，保存/载入均保留两类；YOLO 映射有两个正确 class_id |
| G P3 | PASS，正常负样本空标签；无框分类拒绝 YOLO/Detection preflight；冻结 manifest 字节不变；训练参数/泄漏/模型仓库/配置接口及审核回归 |
| 未关联来源 | PASS，各视频默认类别独立，仅选类别不产生标注修订 |

以上摄像头、故障名称和绘制区域均为独立测试夹具，不是用户现场真值；未对真实项目批量写入或自动确认工业故障。

### 过程与异常

初次新夹具先创建自定义类别，导致默认模板未初始化，触发 StopIteration；已显式初始化独立测试类别并复验通过，初次失败 XML 保留。

一次整套混合测试运行返回 exit_code=1，输出 Windows fatal exception: access violation；当时有另一 GUI 专项进程运行，但证据不足以断言并发是根因。首次未重定向完整输出，完整调用栈仅在当轮工具输出中，目录保存的 mixed-run-crash-note.txt 是摘要，不是假造 dump。

随后不并发启动 GUI 测试：P2 GUI 19 通过、P1 GUI 8 通过、数据/P3/队列业务 42 通过；再整组 69 通过，200% 4 通过。仍保留“一次未定位的原生访问冲突”作为未完全解释的风险，不以复跑掩盖首次异常。没有为此更换 Qt、Python 或 GPU 环境。

## 原始证据

目录：`artifacts/annotation-simplification-20261015/`。

- `combined-final.xml` / `.log`：最终 69 项整组结果。
- `p2-gui-serial.xml`、`p1-gui-serial.xml`、`business-p3-serial.xml` 及对应日志：19/8/42 分组结果。
- `high-dpi-final.xml` / `.log`：200% 四项。
- `targeted.xml`：初次夹具失败；后续 targeted-final、default-separation-final 等记录独立复验。
- `protected-before.json`、`protection-final.json`：选择 159 项模型权重、训练元数据、历史截图/报告及真实项目 SQLite 作只读 SHA256 检查，0 变化。这是已选保护项，不是整仓库扫描。

真实 GUI 截图：

- [正常与三个快捷操作](../artifacts/annotation-simplification-20261015/gui-delivery/simplified-workbench.png)
- [同帧多类别及只读汇总](../artifacts/annotation-simplification-20261015/gui-delivery/multiclass-workbench.png)
- [200% 缩放](../artifacts/annotation-simplification-20261015/gui-200-final/simplified-workbench.png)

没有覆盖上轮截图输出，没有打开真实项目执行标注/迁移/恢复。本轮无新增数据库字段或表，Schema 0008 与旧模型及数据集关系保留。

## 阶段状态

本轮 P2 Hotfix 功能及最终针对性回归 PASS，原生测试异常按上文留档。P3 已有完成记录，本轮没有发现需恢复的未完成开发项，故不重复训练、生成模型或重开发。保留 P3 成果，停止待审，不进入 P4/P5/P6。

PACKAGING_FREEZE = TRUE；没有 EXE、Portable ZIP、安装包或新测试分发，没有重制 Word/PDF。
