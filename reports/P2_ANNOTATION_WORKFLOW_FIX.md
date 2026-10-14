# P2 标注工作流紧急修复

日期：2026-10-14（Asia/Shanghai）。基于 f0814ed 增量修复，仅 P2；无训练、推理、报警或 P3–P6 开发。

## 原因与修复

原服务本来就允许 NORMAL + 空 objects，也没有“无 ROI 禁止保存”的通用校验。真实阻断来自 AnnotationService.load 把可选摄像头 ROI scope 的校验放在整张图片加载之前：无 camera 时抛 ROI_CAMERA。该作用域可以由操作员选中或从上一项目残留，因而图片切换也失败。页面虽然回退作用域，却保留旧画布；列表选择已经移动，造成看似无法下一张。另，保存失败会清除 pending，重试缺少明确继续选择。

现在基础标注加载始终成功；无 camera 的摄像头 ROI 请求明确回到当前视频 ROI，并返回有效作用域，不伪造 camera ID。页面禁用不可用的“ROI关联摄像头”项；当前视频 ROI 仍可配置。提示改为：“当前视频未配置摄像头编号。ROI 为可选辅助信息，不影响基础标注。”仅真正保存摄像头 ROI 的专用操作才校验缺少 camera，并提示改选当前视频。

目标框/多边形仍在 Annotation.payload；NORMAL/ABNORMAL/UNKNOWN 是独立整帧语义；ROI 在独立 rois 表中按视频/摄像头 scope 保存，归一化坐标、版本冲突保护及事务保持原实现。不新增数据库字段或 migration，schema 保持 0004。不把 ROI 转成目标框，不把未知图片默认判为正常。

正常无框 + 无 ROI 合法，DRAFT/REVIEWED/APPROVED/REJECTED 状态可以保存及恢复。正常修改仍按原 350ms 自动保存，立即切换会先完成保存；保存失败时恢复列表到实际画布图片，保留修改并显示错误。再次切换提供“保存后继续 / 不保存继续 / 取消”。三条分支均通过失败夹具测试。上一张/下一张以实际 frame_id 找位置，图片列表按来源及实际相对时间稳定排序，避免同秒 created_at 的不确定顺序。

## 验证

- 最终重点套 6 passed，包括正常空目标恢复、camera scope 回退、无/有 ROI 独立、失败导航三分支、半开区间、粗索引回退与 MPEG 不使用索引 seek。
- 真实指定录像：45 张逐张正向/反向打开；正常无框保存下一张、堵煤类别测试框保存下一张、撤销/重做及 ROI 保存均通过。
- 软件关闭、新服务及新主窗口重开，三份夹具文档的 payload、审核状态、revision 一致；另独立 OS 进程实际恢复，正常无目标框及三份文档对照 PASS。
- 真实标注均明确为测试夹具，DRAFT，不冒充用户人工确认结果；其他帧 UNKNOWN，无故障框。

截图：[正常无框、尚未创建ROI](../artifacts/p2-workflow-fix-20261014/real-normal-no-roi.png)、[测试故障框](../artifacts/p2-workflow-fix-20261014/real-abnormal-TEST-FIXTURE.png)、[独立进程恢复](../artifacts/p2-workflow-fix-20261014/native-process-reopened.png)。完整 PTS、ID、哈希、夹具真值见 [real-results.json](../artifacts/p2-workflow-fix-20261014/real-results.json)。

## 使用与限制

关闭并重新启动工程根目录“启动IVAD.cmd”后生效。保留用户原来运行的窗口，未向其中注入操作。旧 dist 便携候选包未重打包，仍是旧源码，不包含本轮修复。业务支持人工确认，但此次没有选煤厂人员确认真实正常/堵煤位置。
