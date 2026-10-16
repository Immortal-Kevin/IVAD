# P3 Dataset生命周期工作流测试

日期：2026-10-16。软件Hotfix PASS；工业独立性仍LIMITED。

## 最终测试范围与结果

主回归A：50 passed /75.64秒（final-a.xml）；主回归B：77 passed /99.35秒（final-b.xml），共127个不同用例。后续关联/新建授权复位等细节针对性复验11 passed（final-targeted.xml，真实副本用例不重复计数）；最终200% GUI专项3 passed /8.72秒（high-dpi-final.xml）。所有GUI测试进程串行执行。证据统一在artifacts/dataset-lifecycle-20261016，不覆盖旧证据。

| 模块 | 不同用例 | 结果 |
|---|---:|---|
| dataset_lifecycle（含真实副本） | 12 | PASS |
| projects_database | 18 | PASS |
| p3_training | 20 | PASS |
| dataset_management_hotfix | 12 | PASS |
| dataset_hotfix_v2 | 5 | PASS |
| p2_media | 11 | PASS |
| p2_adjustment | 13 | PASS |
| p2_services | 5 | PASS |
| top_toolbar_shortcut | 4 | PASS |
| annotation_simplification | 4 | PASS |
| p2_workflow_fix | 6 | PASS |
| annotation_camera_hotfix_gui | 2 | PASS |
| p2_hotfix_gui | 3 | PASS |
| p2_gui全流程 | 1 | PASS |
| annotation_camera_hotfix | 11 | PASS |

## 本轮关键断言

- 0008→0009只增加Dataset两列；原Dataset/Version字段、UUID、内容不变，完整性ok并有迁移前备份。
- 保存、不同ApplicationServices重开、同UUID修改、CAS拒绝旧修订、无重复Dataset；Frame及Annotation引用正确。不同故障数据集独立，共用正常帧不改其真值；故障集合明确决定检测类别映射。
- 项目/摄像头/故障作用域校验；多摄像头未授权拒绝，新Dataset重置旧共享授权。
- GUI模拟保存失败不清内存；成功才显示实际保存时间。切换数据集可取消/放弃；应用退出取消保持原界面，选择保存则提交后继续关闭。没有自动保存假成功。
- DRAFT保存→VALIDATED检查；成员/设置修改使旧结果失效；源标注修订改变后冻结拒绝。无Dataset或未保存时划分操作禁用。
- 三预设、分组/Seed复现、标准同源不拆、来源不足LIMITED、明确隔离工程方案；图片/目标及正常异常统计分别正确，正常专用引用不被错误归类故障。
- 当前Dataset版本表过滤、无版本提示、v1/v2编号/归属、旧manifest不变、导出与训练前校验、草稿UUID不能当Version UUID。
- 训练页Dataset/Version联动，仍支持YOLO26n/YOLO11n；Model Registry、GPU Worker失败队列、正常负样本、多类别、类别映射与P2标注/片段/抽帧回归保持。

## 真实200张副本

原项目只读备份后复制到本轮独立目录。创建“8525压滤板破裂测试1”，保存200成员并关闭应用；新服务/新Qt窗口重开，Frame和Annotation UUID列表逐项相同。最终证据Dataset UUID为920cdd1e-b164-4bfc-9e4b-261083bb7f83，项目UUID与副本清单一致；没有在原库创建同名记录。

200张=正常16+异常184，目标402，原视频根组1。标准70/20/10实际200/0/0、LIMITED；明确同意隔离小样本方案得到160/40/0：Train正常13/异常147/331目标，Val正常3/异常37/71目标。Test无样本，不存在最终Test性能指标。此处数字是实际检查结果，不是按比例伪造目标。

冻结v1后移除一成员，保存同Dataset revision2并再检查，冻结v2为199图片；v1 manifest逐字节不变，两个Version UUID分别关联同Dataset。训练页能选择v1，完整数据预检通过，没有启动实际训练。real-gui-final/results.json和6张真实Qt截图记录保存、重启、预览、两版本和训练选择器。截图不代表独立工业故障复核。

## 布局、高DPI及保护

1080p及1040×720窗口四Tab可用，内部滚动，浅色输入/下拉与海蓝Tab保持。200%受桌面可用空间限制，申请1920×1080时实际1282×702逻辑像素，另测1040×702；未将申请尺寸冒充实际值。高DPI发现故障复选项行距偏小，按Qt字体/indicator尺寸提示修正后复验3项通过。截图gui-200-final与geometry.json。

166项选取原项目SQLite、录像、P0/P3模型工件、历史证据和备份哈希0变化。原库保持Schema0008、Dataset/Version0/0；测试副本Schema0009、Dataset1/Version2；原库与只读备份逻辑dump相同，完整性均ok、外键无错误。protection-final.json记录具体清单，不声称全盘未变化。

## 失败修正与已知限制

首轮1项发现save/load返回形状差一个project_id派生字段，已统一；项目回归又发现ProjectInfo仍显示0008而实际DB0009，已同步默认schema后复验50项通过。失败XML保留，没有修改原始记录或删除用例掩盖失败。旧GUI流程用例按新的显式保存/检查/选择Dataset步骤更新，没有绕过保存门槛。

此前Qt原生访问冲突根因仍未定位，本轮串行未复现，不宣称长期稳定性解决。原来未保存内存草稿无法恢复；手动保存以外的强制进程退出不能保证未保存修改恢复。候选隐藏仍是会话状态；自动保存、人工拖动、日期/工况分组未实现。检查JSON引用由服务层保护，不新增JSON字段数据库外键。真实故障人工复核、独立工业准确率和跨显卡/跨机验证不在本轮范围。

未安装依赖、更改CUDA或重跑P0；没有真实GPU长训练、新模型或EXE/Portable/Setup。原P3成果保留，完成后停止待审，不进入P4–P10。
