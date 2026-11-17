# P3 Dataset Hotfix v2：布局、时间及批量选图

日期：2026-10-15。功能验收PASS；Schema0008不变。PACKAGING_FREEZE = TRUE。

## 本轮修改

保留四Tab和既有业务，顶部六个筛选改为两行行内标签：第一行摄像头/故障类型/处理结果，第二行来源/标注完成/剔除。使用Qt布局margin/spacing/sizePolicy；较窄时可排为两列，不使用绝对坐标、不缩小中文字体。

1080p同项目实测筛选高度142→72逻辑像素，减少49.3%；加入新选图工具后，表格实际高度493→527像素，净增34像素（约6.9%），没有将筛选高度降幅当成列表面积增幅。1040×720筛选同为72像素，页面内部可滚动；200%实测74逻辑像素，控件无重叠。尺寸证据before-geometry.json、after-final-geometry.json及gui-200/geometry.json。

底部根据项目与当前列表显示“请先前往项目管理打开或创建项目”“当前筛选条件下没有可用图片…”或真实显示/勾选数；后台读取错误显示错误。动作结果独立放在新建数据集反馈区，避免固定项目提示覆盖实际状态。

表格上方增加“全选当前结果”“全选正常”“全选异常”“取消选择”，旁列候选、已选、正常已选、异常已选计数，Tooltip说明下一步加入草稿与当前摄像头/来源。自动选择仅当前可见且eligible、未剔除的合法检测候选；手动逐项勾选仍供软剔除/恢复等管理操作使用，不因此获得训练准入。

Tab切换不清空选择；同范围后台刷新保留仍可见的勾选；主动切换筛选清空临时选择。Tab2显示“当前待添加X张”，加入后报告成功、重复跳过、不合格失败；草稿不重复、独立于勾选状态。跨摄像头仍须明确共享授权；冻结前严格校验保持。

时间修复由统一派生服务完成，非GUI固定减数。数据集列表、草稿、详情及标注帧信息显示媒体相对时间，PTS/time_base及原视频映射保留详情。解码器复用同一转换函数。根因和历史保护详见P3_FRAME_TIMESTAMP_INVESTIGATION.md。

## 真实GUI前后对照

修改前：

![修改前：142像素筛选、误导提示及绝对PTS列](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-v2-20261015/before-1920.png)

修改后：

![修改后：72像素筛选与相对时间](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-v2-20261015/after-final-1920.png)

真实副本选择200张，正常16/异常184：

![批量选择与真实数量](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-v2-20261015/real-selection-200.png)

加入草稿及重复保护：

![草稿成员与重复反馈](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-v2-20261015/real-draft-200.png)

窄窗口与200%截图见after-final-1040.png及gui-200/compact-1040.png。全部来自实际Qt窗口，不生成模拟界面。

## 修改文件

- ivad_app/gui/dataset_page.py：紧凑筛选、选择工具、动态状态、待添加/重复反馈。
- ivad_app/gui/p2_controller.py：错误状态及动作反馈分离。
- ivad_app/video/timestamps.py：统一派生媒体/原视频时间；reader.py复用相对时间函数。
- ivad_app/services/media_service.py、dataset_service.py：返回派生时间，新快照可选timing；不改历史字段。
- ivad_app/gui/annotation_page.py：仅必要的相对时间显示/服务结果接入，没有重新设计标注工作台。
- tests/test_dataset_hotfix_v2.py新增；test_dataset_management_hotfix.py适配严格有效候选全选和手动恢复选择。
- 更新数据集Markdown指南、数据模型说明及当前进度；没有重制Word/PDF。

## 测试、保护及限制

两组97项回归通过，200%专项1项通过；具体项目见P3_DATASET_SELECTION_TEST_RESULTS.md。真实项目仅只读连接/备份，GUI与草稿验证在独立副本进行；受测录像只复制/解码，不转码替换。165项选取数据库、受测项目内录像、模型及历史证据SHA256无变化；原库和备份逻辑一致，详见protection-final.json。

历史PTS/time_us、标注UUID/图片/关联、旧冻结版本和训练工件未修改。没有Migration或历史记录写入需求，因此没有执行数据修复迁移。

会话草稿仍不跨重启保留；片段缺少实际首帧映射时明确未知，不猜起点；截图和结构检查不能替代工业故障人工复核。真实8525仍只有一个原视频来源组，独立划分LIMITED限制不变。200%为Qt缩放，未改变Windows显示设置或覆盖所有显示器组合；未对极小窗口作验收。

未安装依赖、修改GPU环境、启动真实训练或重做P0；无EXE、Portable、Setup。P3原有成果保留，无待重启的旧训练任务；本轮完成后停止待审，不进入P4–P6。
