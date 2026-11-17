# P2 测试员使用指南编制与验证记录

编制日期：2026-10-14。软件版本：1.0.0-P2。范围：文档、真实截图、测试模板与独立培训项目核验；未修改软件业务功能，未进入 P3。

## 1 交付与结果

- Word：`docs/IVAD_P2_测试员操作指南.docx`，15 页 A4。首页《新测试员快速上手》独占 1 页。
- Markdown：`docs/IVAD_P2_测试员操作指南.md`，与 Word 共享同一内容源。
- Excel：`docs/IVAD_P2_测试记录表.xlsx`，3 张工作表、44 项功能用例。
- 截图：`docs/IVAD_P2_指南截图/图01.png` 至 `图13.png`，13 张真实 GUI 图像；不含 AI 生成界面。
- 47 条核验记录中，45 条属于真实 Qt GUI 操作或其界面结果核验，另 2 条为源文件哈希／服务恢复检查（GUI-19、GUI-46）。文件选择框提交边界见下文，不将其算作原生完整端到端实测。

## 2 依据和方法

已阅读 SRS、ARCHITECTURE、P2_USER_GUIDE、P2_ACCEPTANCE、P2_UI_ADJUSTMENT、P2_CLIP_SAVE_FEATURE，并复核启动脚本、当前视频页面与播放器、标注工作台和画布、类别库、数据集页面、任务中心、诊断日志、服务层与 migration 0004。软件能力以当前运行结果和实际控件为准，不把 SRS 的计划功能写成已实现。

原生启动核验：运行现有 `启动IVAD.cmd`，仅给本轮指定独立 data-dir；实际窗口标题 IVAD Platform 1.0.0-P2 已观察，进入项目管理、填写名称并打开真实 Windows“选择项目存储父目录”窗口。原生选择框最终路径提交未完整自动核实，未将其记作通过。

完整操作核验：使用既有 `.venv-p1` 的 PySide6、pytest-qt、QTest 操作真实 MainWindow、真实按钮、画布与确认对话框；业务服务、队列、解码、裁剪、抽帧、SQLite 保存均真实执行，不使用假后台成功。文件／文件夹选择返回值为独立培训路径注入，覆盖创建、打开、导入、导出；这些操作的业务链路经过 GUI，而 Windows 原生路径选择提交另列未验证。确认抽帧窗口的 Yes 是真实按钮点击，不是伪造截图或替换确认结果。

核验环境沿用当前 GUI 环境，不安装或更新 GPU／Python 包。窗口 1280×900；本进程临时 QT_SCALE_FACTOR 用于得到约 100% 的有效缩放，不修改 Windows 系统 DPI。高 DPI 用户界面本轮未单独重新测试，历史调整报告仅作参考。

本轮自制 300 秒、5 fps、640×360 MP4 包含操作练习色块，无现场隐私信息。主流程统一使用“测试员培训项目”、CAM-DEMO-01、“演示故障片段_120至140秒”。示例不是工业异常识别证据。

原始证据：
- `artifacts/p2-guide/gui_verify.py`、`gui-verification.json`、`gui-verification.xml`。
- `artifacts/p2-guide/gui-verification-rerun.log`：完整 GUI 场景 1 passed，21.88 秒，进程退出码 0。
- `artifacts/p2-guide/capture_corrections.py`、`capture-corrections-complete.log`：校正片段截图并追加全新 GUI 窗口保存恢复核验，1 passed，1.91 秒，退出码 0。
- 截图修正过程中两次脚本失败日志保留（首次使用不存在的方法；第二次未等待异步录像加载完成即填写范围），属于文档核验脚本问题。修正脚本等待正确录像加载后通过；没有修改软件实现。

## 3 四项 P2 调整的复核

| 要求 | 当前真实状态 | 证据与边界 |
| --- | --- | --- |
| 左侧列表、右侧操作区 | 已实现；左右分隔、六列列表、独立右侧滚动 | 图 2、media_page.py；列宽超过可视宽度时横向滚动。未复测所有低分辨率组合。 |
| 标签视觉统一 | 视频页四标签普通蓝底白字，激活／悬停白底黑字 | 当前样式与真实图 2–5；其他页面深色区域的低对比问题单独记录。 |
| 抽帧参数说明 | 已实现可见中文辅助文字和 tooltip；明确变化筛选非工业异常判断 | 图 5、参数表与当前控件代码；本轮截图为局部裁切，不宣称每个 tooltip 均弹出截图。 |
| 人工保存视频片段 | 已真实完成独立 MP4、CLIP 入库、播放、再抽帧 | GUI-17、18、21；原录像哈希一致。取消、REFERENCE 裁剪的本轮 GUI 异常链路未复测。 |

## 4 逐项操作核验

PASS 表示对应记录中声明的方法完成；不扩大到未执行的原生文件选择、异常取消或所有编码格式。

| 编号 | 操作或结果核验 | 结果 | 方法及限制 |
| --- | --- | --- | --- |
| GUI-01 | 启动当前真实MainWindow及开发模式 | PASS | 真实 Qt GUI |
| GUI-02 | 切换生产监控模式并确认规划功能 | PASS | 真实 Qt GUI |
| GUI-03 | GUI填写并新建独立培训项目 | PASS | 真实 Qt GUI；项目父目录选择返回值注入；真实Windows选择框提交未自动核实 |
| GUI-04 | 保存项目配置 | PASS | 真实 Qt GUI |
| GUI-05 | 项目一致性检查 | PASS | 真实 Qt GUI |
| GUI-06 | GUI关闭并重新打开同一项目 | PASS | 真实 Qt GUI；文件夹选择返回值注入 |
| GUI-07 | COPY导入及可选摄像头厂区设备信息 | PASS | 真实 Qt GUI；文件选择返回值注入 |
| GUI-08 | 选择录像及READY状态和元数据查看 | PASS | 真实 Qt GUI |
| GUI-09 | 相同录像重复导入复用已有资源 | PASS | 真实 Qt GUI；原生文件选择返回值注入 |
| GUI-10 | 批量AVI MOV MKV导入 | PASS | 真实 Qt GUI；原生文件选择返回值注入 |
| GUI-11 | 实际播放暂停 | PASS | 真实 Qt GUI |
| GUI-12 | 逐帧前进后退 | PASS | 真实 Qt GUI |
| GUI-13 | 播放速度选择 | PASS | 真实 Qt GUI |
| GUI-14 | 输入120秒跳转并显示实际画面 | PASS | 真实 Qt GUI |
| GUI-15 | 拖动时间轴实际跳转 | PASS | 真实 Qt GUI |
| GUI-16 | 由当前画面设置起点终点及检查范围 | PASS | 真实 Qt GUI |
| GUI-17 | 保存20秒独立CLIP及名称备注 | PASS | 真实 Qt GUI |
| GUI-18 | 选择并实际播放新CLIP | PASS | 真实 Qt GUI |
| GUI-19 | 原始录像内容保持不变 | PASS | 源文件 SHA256 比较（补充，不计入 GUI 操作数） |
| GUI-20 | 倒序及过短片段提示 | PASS | 真实 Qt GUI |
| GUI-21 | 案例B 20秒片段每0.2秒抽取100张图片 | PASS | 真实 Qt GUI |
| GUI-22 | 案例A 300秒录像每2秒抽取150张图片 | PASS | 真实 Qt GUI |
| GUI-23 | 变化筛选及基础间隔样本实际运行 | PASS | 真实 Qt GUI |
| GUI-24 | 抽帧后进入标注工作台并按录像编号筛选 | PASS | 真实 Qt GUI |
| GUI-25 | 打开第一张图片及来源PTS显示 | PASS | 真实 Qt GUI |
| GUI-26 | 通过标签库GUI创建故障类型 | PASS | 真实 Qt GUI |
| GUI-27 | 鼠标拖动真实矩形框 | PASS | 真实 Qt GUI |
| GUI-28 | 矩形移动及角点尺寸调整 | PASS | 真实 Qt GUI |
| GUI-29 | 撤销重做 | PASS | 真实 Qt GUI |
| GUI-30 | 整帧异常标记及REVIEWED审核自动保存 | PASS | 真实 Qt GUI |
| GUI-31 | 逐点绘制多边形并Enter完成 | PASS | 真实 Qt GUI |
| GUI-32 | 多边形顶点编辑 | PASS | 真实 Qt GUI |
| GUI-33 | 删除错误标注并撤销恢复 | PASS | 真实 Qt GUI |
| GUI-34 | 独立矩形ROI绘制保存 | PASS | 真实 Qt GUI |
| GUI-35 | 独立多边形ROI绘制保存 | PASS | 真实 Qt GUI |
| GUI-36 | 滚轮缩放中键平移适应窗口 | PASS | 真实 Qt GUI |
| GUI-37 | 下一张及正常画面标记 | PASS | 真实 Qt GUI |
| GUI-38 | 未知待确认标签 | PASS | 真实 Qt GUI |
| GUI-39 | 上一张重开标注与ROI保存恢复 | PASS | 真实 Qt GUI |
| GUI-40 | 显式保存标注 | PASS | 真实 Qt GUI |
| GUI-41 | 已审核图片检查冻结YOLO Detection导出 | PASS | 真实 Qt GUI；导出父目录选择返回值注入 |
| GUI-42 | 任务中心查看状态及进度 | PASS | 真实 Qt GUI |
| GUI-43 | 选中任务查看任务日志 | PASS | 真实 Qt GUI |
| GUI-44 | 诊断日志复制脱敏信息 | PASS | 真实 Qt GUI |
| GUI-45 | 窗口正常关闭且完整保存 | PASS | 真实 Qt GUI |
| GUI-46 | 关闭后新服务重开同项目标注仍在 | PASS | 新 ApplicationServices 重开项目（补充，不计入 GUI 操作数） |
| GUI-47 | 全新GUI窗口重开培训项目并恢复已保存标注与ROI | PASS | 真实 Qt GUI；原始服务恢复检查之后追加真实GUI恢复核验；仅打开本轮独立培训项目。 |

## 5 本轮未完成 GUI 验证的场景

| 场景 | 状态 | 指南处理 |
| --- | --- | --- |
| Windows 原生文件／文件夹选择框最终提交 | PARTIAL | 观察了选择框；Qt 场景注入路径，明确验证边界。 |
| REFERENCE 导入、源文件移走、重新定位、从引用保存 CLIP | NOT TESTED | 按当前实际按钮和代码解释行为；不冒称本轮 GUI 通过。 |
| 损坏录像、READY 无法播放、超范围任务失败 | NOT TESTED | 列真实诊断路径与预期处理，供其他测试员执行。倒序及过短范围已实测。 |
| 任务执行中取消、断电／中断、取消后的竞态 | NOT TESTED | 说明取消按钮和已完成资源可能保留；未人为制造故障破坏数据。 |
| 自动保存失败、退出阻断、放弃修改确认、缺失图片恢复 | NOT TESTED | 不修改数据库制造失败；记录为待测。 |
| 当前画面候选帧、片段标签 CRUD、摄像头作用域 ROI 重用 | NOT TESTED | 控件已实际看到、代码复核；指南不宣称本轮完整操作实测。视频作用域 ROI 已验证。 |
| 所有倍率、任意分辨率、200% DPI、所有格式导出 | NOT TESTED | 实测 2×、本轮窗口、指定素材及 YOLO Detection；其他组合不得按本轮结果推断。 |

当前版本暂不支持：AI 训练、生产自动报警／实时摄像头、AI 预标注、AI 辅助抽帧、片段再裁片段、“保存并继续抽帧”、复杂多边形孔洞、完整项目备份恢复 GUI、一键提交问题工单。指南均明确限制，没有编造操作入口。

## 6 截图来源与处理

截图全部来自运行中的真实 Qt 控件 `QWidget.grab()`。只作裁切与非遮挡红框标记，保留原始图；没有替换文字、拼装假按钮或生成界面。源图位于本轮 artifacts 目录，交付图随 Markdown 位于 docs 中。原始路径显示区经裁切排除，截图没有账号或现场人员画面。图 8 为类别保存后输入区复位的真实状态；图 6 为真实 Yes/No 确认窗口。

| 正文图号 | 文件 | 原始截图来源 | SHA256（交付图） |
| --- | --- | --- | --- |
| 图 1 | `docs/IVAD_P2_指南截图/图01.png` | `artifacts\p2-guide\raw-01.png` | `f745faaf9b700a241fd68b08b9a2cefc5f27a05b5d6f3a1d18a4ba5792d1d31d` |
| 图 2 | `docs/IVAD_P2_指南截图/图02.png` | `artifacts\p2-guide\raw-02.png` | `3cdefc0495bd6e0fd47eb6785be21a641163c2cf238c7df69520d5a381dd8f6a` |
| 图 3 | `docs/IVAD_P2_指南截图/图03.png` | `artifacts\p2-guide\raw-03.png` | `f2c58000e237327ff824c0d4ce09530fedd60d56f74fe0786f6905bfae4c43ab` |
| 图 4 | `docs/IVAD_P2_指南截图/图04.png` | `artifacts/p2-guide/raw-04-guide.png` | `9ce7607a41a3b45b43c940ea2c6d1c0b92cdc619a0bd0e4530e9fa0c4bcbf110` |
| 图 5 | `docs/IVAD_P2_指南截图/图05.png` | `artifacts\p2-guide\raw-05.png` | `97c6deb7843861c378018979d5e2b361ea70c38f6a9d07d9ae94bbbfb20dc012` |
| 图 6 | `docs/IVAD_P2_指南截图/图13.png` | `artifacts\p2-guide\raw-13.png` | `52ae7b509b87ead7a76f13fc76b54a4fbb28fce668e4a0e717ac6608b05dc161` |
| 图 7 | `docs/IVAD_P2_指南截图/图07.png` | `artifacts\p2-guide\raw-07.png` | `202adace1ae8c66dc14251bb4ff36d02ea460306642a0d0fe94b9a24986fac7f` |
| 图 8 | `docs/IVAD_P2_指南截图/图06.png` | `artifacts\p2-guide\raw-06.png` | `0d66ff6c37a176a3363118873428a4a86865537614ea4e51943139c8b63b95cb` |
| 图 9 | `docs/IVAD_P2_指南截图/图08.png` | `artifacts\p2-guide\raw-08.png` | `23f6175523a08686e858876f754612306b46ec5e772dba974d0203d8064ec108` |
| 图 10 | `docs/IVAD_P2_指南截图/图09.png` | `artifacts\p2-guide\raw-09.png` | `263609dbc8e264333ec198dd1083ae3922b37577c6ed54ac2f88fb48a5ebebd5` |
| 图 11 | `docs/IVAD_P2_指南截图/图10.png` | `artifacts\p2-guide\raw-10.png` | `abd86566f53f34ab63332e3b5a114028383bac6e6985a9a03f52cf159742e7eb` |
| 图 12 | `docs/IVAD_P2_指南截图/图11.png` | `artifacts\p2-guide\raw-11.png` | `20d3920f2e05029f95a711ca9b131f539a395e291baed024aaf94f858e3e0c16` |
| 图 13 | `docs/IVAD_P2_指南截图/图12.png` | `artifacts\p2-guide\raw-12.png` | `af48d046c52ebd99ab2caf925d6327b26a644a388f3e25c1af8f167990feacff` |

## 7 文档质量检查

- Word 使用 A4、微软雅黑中文字体、黑色标题，页脚使用自动 PAGE。首页 10 项引用使用 PAGEREF 书签域。通过本机 Microsoft Word 16.0 实际重新分页、更新域、保存并导出 PDF，不预估页码。
- 当前首页页码依次为：3、3、4、5、6、7、9、10、12、15，与正文书签和 PDF 文本核对相同。总页数 15，第一页没有正文第一章内容。
- 已逐页查看 15 页实际 PDF 栅格图，检查标题、中文、表格、图片、页脚和页面边界；表格无跨页拆行，页面无文字溢出。重要按钮用红框，图片保持原比例。截图保留软件当前颜色，不能把原软件低对比文字伪装成已修复。
- 文档技能的 render_docx.py 首次运行缺少 PATH 中的 soffice.exe，因此未安装依赖，改用已安装 Microsoft Word 的文档接口导出及已有 Poppler 渲染；产物为实际最终 Word 分页。
- Markdown 从同一 manuscript 构建，逐段标题／正文与 Word 内容检查通过，页码由最终 Word 输出同步；图片随附相对路径便于发送整个 docs 文件夹。
- Excel 使用 bundled @oai/artifact-tool 生成；3 张表分别渲染查看，无标题或表头溢出。原导出未写入 native AutoFilter，采用最小 OOXML 补齐 3 个表的 autoFilter，保留所有其他内容。未使用 openpyxl 编写工作簿，未修改项目环境。
- 本机 Excel 只读打开最终 XLSX，无修复提示；3 表均 ShowAutoFilter=True。XML 核实冻结前 3 行与前 2 列、状态／严重程度／处理状态 3 个下拉及日期格式。工作簿无公式，故不存在计算公式错误。功能清单实际结果与人员／日期留空，44 项均 NOT TESTED。
- QA 证据：`page-map.json`、`document-quality.json`、`excel-native-check.json`、`rendered/final-01.png` 至 `final-15.png`、3 张 `workbook-*.png`。

## 8 发现的问题与待用户决定事项

| 问题 | 实际发现 | 处理 |
| --- | --- | --- |
| DOC-01 录像来源显示不完整 | 工作台仅显示录像短 UUID、图片相对秒数与 PTS，不显示完整来源名称及父录像时间面板；多录像易混淆。 | 指南提示记录来源与范围，不能猜测。没有擅自修改业务功能，等待用户决定修复。 |
| DOC-02 非视频标签区域的低对比文字 | 项目管理、类别库、诊断／任务页面的部分深色标签与背景对比不足；Yes/No 确认窗口的问题文字也偏暗。视频四个标签的蓝白／白黑状态已实现。 | 保留真实截图，不篡改颜色冒充软件修复；建议用户审阅后决定界面修复。 |
| DOC-03 核验进程 Windows COM 诊断异常 | Qt 核验日志在首次事件等待时打印 Windows fatal exception 0x8001010D 调用栈；完整场景及截图恢复场景随后完成、pytest 为 PASS 且退出码 0。 | 原始日志保留。原因未定位，不认定已修复，也不将其误报为场景中断。需开发人员检查运行／自动化环境。 |
| DOC-04 原生选择框与异常用例待人工补测 | 本轮路径返回值注入，取消与缺失等未再制造。 | 测试模板覆盖相关场景，明确 NOT TESTED；不得据此宣称 P2 所有验收项已通过。 |

## 9 保护与阶段限制

- 本轮开始前已追踪 109 个项目文件逐一 SHA256 比较，全部一致；包括现有代码、历史报告、锁文件和启动脚本。详见 `artifacts/p2-guide/preservation.json`。
- 所有 GUI 测试仅使用 `artifacts/p2-guide` 的新应用目录、培训项目与自制素材；未打开或改写真实现场项目。未安装依赖、未调整驱动／CUDA／NVIDIA 环境。
- 本轮仅交付文档、截图、测试模板。未修改架构、数据库 migration 或业务模块，未进入 P3。完成后停止，等待用户验收。

建议测试员首先执行正文第 13 页完整案例：原录像 120–140 秒 → 保存 20 秒 CLIP → 每 0.2 秒抽帧、上限 100 → 人工矩形框与类别 → REVIEWED → 保存重开。普通 5 分钟均匀抽帧案例作为第二轮操作；现场初次试用优先采用 20–60 秒合法短素材。