# P3 数据集管理界面 Hotfix

日期：2026-10-15。任务范围：P3 Dataset Management UX & Data Integrity Hotfix。源码版1.0.0-P3-Dev.2；PACKAGING_FREEZE = TRUE。软件功能PASS：最终68项回归通过，最终200% GUI专项1项通过；真实单来源数据划分LIMITED。

## 交付结果

完成四个原生QTabWidget页面，顺序为“图片列表与筛查”“新建数据集”“训练集划分设置”“数据集版本”。顶部共享摄像头、故障、处理结果、来源、完成情况和剔除筛选，Tab切换保留表单、勾选和草稿，不叠加页面。初次优先当前标注摄像头，否则选择有合格样本的单摄像头；全部/未关联需明确选择。Camera Registry按当前项目动态读取。

默认隐藏EXCLUDED；表格显示摄像头、真实PTS秒数、录像名称、处理结果、类别汇总与目标数量；支持列排序和滚动。完整UUID、SHA256、源路径、摄像头/原视频UUID及校验问题保留在tooltip。没有重命名真实类别或改动样本身份。

移除了独立逐张审核区和重复提交控件。自动检查可接受已保存人工正常无框与合法异常目标；DRAFT等原审核字段不改写。新GUI只创建明确标记为实验用途的新版本；旧版本不升级、不覆盖。完整政策见P3_DATASET_VALIDATION.md。

Tab2显示候选/选择/正常/异常/无效/草稿计数，并提供添加、检查和移除成员；跨摄像头必须显式同意。Tab3独立设置来源/摄像头/随机划分、70/20/10比例与Seed123，中文Tooltip说明用途，预览预计/实际数量及风险。Tab4提供冻结、历史类别/划分详情、选中版本文件完整性和逐样本来源检查，以及既有YOLO/COCO/原生导出。

## 批量操作与保护

- 从候选列表排除：只影响当前Dataset UUID对应的会话草稿/候选范围，不改变全局标注和文件；恢复候选不会自动恢复已移除草稿成员。
- 标记无效/恢复：复用已有AnnotationService软状态及历史记录，确认后执行；与候选排除分开。
- 筛选变化清空勾选，排序使用每行UUID定位，避免跨摄像头误操作。添加草稿时只加入合格且未重复成员。批量结果显示成功/跳过/失败数量。
- 没有永久删除、数据库重建、标注编辑、旧数据集重写或模型训练。

## 修改文件

产品：ivad_app/gui/dataset_page.py、p2_controller.py、p2_hotfix_controller.py；ivad_app/services/dataset_service.py、training_service.py。P2标注工作台/媒体处理、导出器、GPU Worker和Model Registry源码没有改动。

测试：新增tests/test_dataset_management_hotfix.py；旧审核GUI测试夹具改为review_fixture服务级历史审核政策准备，相关P2测试按新的“已标注”筛选和草稿添加流程操作，未保留隐藏的旧审核入口。

文档：新增docs/P3_DATASET_USER_GUIDE.md；更新P3/P2 Markdown指南、DECISIONS、CURRENT_TASK、数据库文档说明及执行状态。没有重制Word/PDF。

## 真实GUI证据

以下来自用户项目的SQLite只读备份和图片副本；没有在真实项目执行冻结、剔除或修改标注。

![图片列表：8525、真实PTS及类别](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-20261015/real-copy-tab1.png)

![新建数据集草稿](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-20261015/real-copy-tab2.png)

![真实单来源划分LIMITED](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-20261015/real-copy-tab3.png)

![版本页结构](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-hotfix-20261015/real-copy-tab4.png)

最终独立夹具的1920×1080/1040×720截图见artifacts/dataset-hotfix-20261015/gui-acceptance；200%缩放见gui-200-delivery；成功冻结/导出后的版本页见p2-acceptance/dataset.png。截图来自实际Qt widget.grab，没有生成或绘制模拟界面。

## 测试与限制

最终结果见P3_DATA_SPLIT_TEST_RESULTS.md。布局已检查1080p、窄窗口、200%Qt缩放；小窗口各Tab内部独立滚动，浅色输入和海蓝色标签可读。首次截图发现继承深色样式及控件挤压，已通过本页限定样式与页内滚动修复，旧试验截图单独留档。

会话草稿/候选排除重启不保留，正式冻结版本持久化；当前不提供命名持久化草稿。日期/工况/时段分组仅保留策略扩展位置，未实现。比例按组分配，实际图片数不一定等于百分比。高DPI使用Qt缩放验证，没有更改Windows全局显示设置。

P3原已完成；本轮仅数据准备Hotfix，不重复训练。保持打包冻结，不进入P4–P6。完成后停止待审。
