# P3 Dataset Hotfix v2 选择与回归测试

日期：2026-10-15。软件Hotfix PASS。没有进入训练或后续阶段。

## 最终结果

- 核心回归A：66 passed / 48.91秒，artifacts/dataset-hotfix-v2-20261015/regression-a.xml。
- 标注/导航/摄像头回归B：31 passed / 56.03秒，regression-b.xml。
- 合计97个不同用例通过；200% GUI专项重复1项通过 / 3.21秒，high-dpi.xml。Qt进程串行运行。

| 模块 | 不同用例数 | 结果 |
|---|---:|---|
| 新增dataset_hotfix_v2 | 5 | PASS |
| dataset_management_hotfix | 12 | PASS |
| p2_media实际解码 | 11 | PASS |
| p2_adjustment片段/布局/业务 | 13 | PASS |
| p2_services | 5 | PASS |
| p3_training | 20 | PASS |
| top_toolbar_shortcut | 4 | PASS |
| annotation_simplification | 4 | PASS |
| p2_workflow_fix | 6 | PASS |
| annotation_camera_hotfix_gui | 2 | PASS |
| p2_hotfix_gui | 3 | PASS |
| p2_gui完整导入到重开 | 1 | PASS |
| annotation_camera_hotfix | 11 | PASS |

## 选择与反馈

GUI验证全选当前有效结果、全选正常、全选异常、取消、候选及分类选择计数、Tab1→Tab2保留勾选、待添加数量、加入草稿和重复跳过。无共享授权时多摄像头加入被阻止，明确授权后成功。草稿成员在取消/筛选变化后独立保留；同范围后台刷新保留当前选择，摄像头/故障/来源等主动筛选清空选择。空结果、无项目、具体读错误及正常数量提示均检查。

严格批量选择不再勾选未知/无效/剔除/冲突或不符合Detection的图片。旧v1测试已按该要求更新其全选断言；恢复已剔除管理流程用人工逐项勾选，未放宽训练全选。表格排序后的操作仍通过UserRole UUID定位。

真实项目副本使用原200帧验证：全选正常16、异常184、全部200；Tab2待添加200；首次添加200，第二次成功0/重复跳过200，草稿仍200。不冻结、不修改真实标注、不改变类别。副本GUI仅证明软件选择与既有记录一致，不重新确认工业真值。

## 布局及时间

同项目1920×1080实测筛选142→72px（减少49.3%），净表格高度493→527px。1040×720下筛选72px，表格最小220px，内部滚动；200%实际窗口受桌面限制为1282×702和1040×702逻辑像素，筛选74px。没有把申请的1920×1080当作200%实际窗口大小。六个筛选控件范围与无重叠断言通过；真实截图已查看。

时间测试包括普通零起点MP4、实际VFR、自制非零PTS MPEG-TS（原点>100秒）、真实裁剪再抽帧、多级片段映射与缺失映射警告。非零PTS样本按0.2–1.0秒半开区间每0.2秒抽出4帧，相对200/400/600/800ms，原PTS仍非零；片段0秒正确映射原媒体0.2秒。没有用FPS反推、重写PTS或强凑张数。

指定8525只读重probe和4点解码/像素对照通过；真实播放器、标注、数据集三处5.800秒一致。200条现有time_us均正确；0.52/0.48秒实际帧差符合0.5秒目标间隔。完整数值见P3_FRAME_TIMESTAMP_INVESTIGATION.md。

## P3兼容与数据保护

覆盖已保存正常负样本、异常box/polygon、多类别、整帧分类不冒充Detection、YOLO导出、分组比例/种子、旧冻结不可变、准入政策、训练前检查、Model Registry及Worker失败队列路径。TrainingService、GPU Worker、Model Registry执行代码和适配器未改；未实际启动YOLO26n/YOLO11n训练，不声称新增GPU硬件运行证据。

原项目SQLite只读，备份PRAGMA完整性ok、外键无错误、逻辑dump哈希与原库一致。165项选取保护文件（项目库、受测项目内视频、模型工件、历史证据与备份）0变化。旧冻结文件、标注UUID/几何/标签、图片和来源关联没有改写，Schema0008不变；无需写回迁移。范围见protection-final.json，不声称全盘核验。

## 试验记录与限制

首轮测试收集时新导入误置于MediaService的__future__之前，触发SyntaxError，已纠正导入位置后全部复验通过；未安装依赖或通过绕过业务测试解决。其余本轮最终测试无失败。上一轮未定位的Qt原生访问冲突保留历史限制，本轮串行运行未复现，不能据此宣称根因解决。

目前8525仍仅一个原录像来源，工业独立Train/Val/Test条件不足；时间修复不改变该LIMITED结论。拍摄日期未知，旧片段缺可靠映射时不猜测。高DPI仅Qt200%验证，未覆盖所有Windows缩放/显示器组合。P3既有成果保留，不重新开始旧任务；完成后停止待审。PACKAGING_FREEZE = TRUE，无EXE/Portable/Setup，不进入P4–P6。
