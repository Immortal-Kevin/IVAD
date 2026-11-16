> 当前 UI/连续标注修订见 [本轮报告](V1_1_UI_ACCEPTANCE_20261026.md)。本文件保留此前阶段记录，计数不代表最新结果。

# IVAD v1.1 真实GUI验收记录

## 结论

**NOT TESTED，不能声称PASS。** 应用已实际启动和渲染，但没有完成真实鼠标/键盘端到端验收。

本轮使用已安装computer-use技能，按规定从node_repl导入`@oai/sky`。`sky.list_apps()`成功取得Windows应用清单。调用`sky.launch_app`请求现有开发EXE时，工具返回：

```text
Computer Use was not approved to use dev
```

工具没有给出更具体原因。不能把拒绝解释成WPF程序崩溃、Windows鼠标不可用或用户撤回全部开发授权。真实输入事件计数为0。没有尝试另一个自动化通道绕过拒绝。独立授权的编译、测试、现有--smoke门禁继续执行。

## 逐流程状态

| 用户要求 | 真实GUI状态 | 已有的独立证据 |
|---|---|---|
| 新建、关闭、重新打开项目 | NOT TESTED | 服务层创建/重开PASS |
| 导入视频，范围、间隔 | NOT TESTED | 实际Media Foundation/子进程范围测试PASS |
| 厂区/项目/设备/摄像头关联 | NOT TESTED | 实体关联及IDS完整指纹PASS |
| 矩形绘制、选中、移动、调整、删除 | NOT TESTED | GUI处理代码存在，几何编辑/软删除/修订服务测试PASS |
| 多边形和ROI绘制、编辑 | NOT TESTED | 顶点编辑/ROI摄像头/持久化服务测试PASS |
| 正常、异常、未知及审核 | NOT TESTED | 服务层每种状态与重新打开PASS |
| 自动保存、关闭、重开持久化 | NOT TESTED | 存储与并发保护测试PASS |
| GUI导出完整IDS再导入 | NOT TESTED | 真实文件包往返/hash/完整元数据一致性PASS |
| 导入、hash、抽帧、导出期间界面响应 | NOT TESTED | Task.Run/独立进程静态检查；后台子进程取消PASS |
| 忙碌时关闭、取消后的实际界面恢复 | NOT TESTED | 实现已加入，尚无真实GUI操作证据 |

## 不可混同的证据

`governance/evidence/annotator-smoke.png`由实际WPF窗口渲染。既有--smoke方法在窗口内直接调用服务保存标注/审核/导出；它仍是模拟工作流，不是UI自动化，不计为上述流程通过。本轮没有将其包装成真实鼠标结果。

原始工具结果摘要：`governance/evidence/windows_gui_attempt.json`。Release Gate的B项单列NOT TESTED，即使服务测试全部PASS也不自动升级。

## 最小下一步

用户可直接双击`build/dev/Ivad.Annotator.Dev.exe`按`docs/ANNOTATOR_QUICKSTART.md`人工验收。自动GUI重跑需要先恢复computer-use对该开发版的启动/操作授权；本轮没有擅自更改工具权限、系统安全或网络设置。其余普通工程问题没有要求用户介入。
