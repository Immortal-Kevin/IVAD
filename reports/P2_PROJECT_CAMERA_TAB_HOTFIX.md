# P2 项目管理 / 摄像头双 Tab 紧急修复

日期：2026-10-15。源码基线：074184b，1.0.0-P3-Dev.2 / Schema 0007。

## 结果

GUI 修复及相关回归 PASS：51 项通过（38.73 秒），200% 缩放专项另 1 项通过（2.58 秒）。仅修改 4 个 GUI 文件及新增 1 个测试文件；无 Migration，无依赖安装，无 GPU 训练或基准测试。PACKAGING_FREEZE = TRUE。

历史保护清单比较有 1 项数据库差异，单独记录在末节，不能宣称全部历史文件哈希一致。

## 原因与修改

旧控制器在项目页面构建完成后，以 takeAt / addItem 搬移既有布局项，未可靠地将表单控件归属到新 Tab 容器，造成摄像头页面与旧表单同时显示。现在在 ProjectsPage 初始化时直接创建原生 QTabWidget，表单和摄像头各有独立 QWidget / QScrollArea / QVBoxLayout，由 Qt 管理父子关系及可见性，不使用绝对坐标或浮动面板。

- `ivad_app/gui/pages.py`：默认“项目管理”Tab；完整保留创建、打开、编辑、保存、关闭、最近项目和一致性检查；增加“进入摄像头管理”快捷入口。两个 Tab 切换不会重新加载或清空项目表单。
- `ivad_app/gui/p2_hotfix_controller.py`：复用页面已有 Tab，摄像头面板仅加入第二页。项目变化或关闭时立即清空旧列表和编辑状态、清空视频页旧摄像头候选；沿用异步加载的项目上下文校验，避免旧项目回调污染新项目。无项目显示“请先打开项目”，禁用创建、保存等操作。
- `ivad_app/gui/camera_management.py`：设置明确的浅色面板样式标识及背景绘制属性；保持既有 UUID、保存和启停业务。
- `ivad_app/gui/style.py`：仅对项目页新增样式作用域。背景浅色，输入白底深字，列表浅底深字；未选中 Tab 海蓝底白字，选中和悬停白底深字；禁用按钮及文字灰色但可辨。保留全局 QComboBox popup 白底深字、浅蓝选中项样式；未改变深色导航栏或标注画布。
- `tests/test_project_camera_tabs.py`：新增真实 Qt 界面测试、上下文隔离与截图记录。

两个 Tab 共用既有当前项目服务。双击最近项目仍正常打开，并保留此前快捷进入摄像头页的行为。摄像头“保存关联”继续通过视频管理页的既有关联操作执行；摄像头 Tab 保存资料及启停，不新增重复关联业务。

## 测试结果

| 验证项 | 结果与证据 |
|---|---|
| 默认项目管理、表单完整、创建项目 | PASS，Qt 鼠标点击新建按钮，目录对话框在测试中指定独立临时目录 |
| 两 Tab 切换及归属 | PASS，断言各自父容器和可见性；反复切换无叠加 |
| 项目名称、厂区、描述未保存保留 | PASS，切换 3 次后值一致，并点击保存配置 |
| 创建、编辑、停用摄像头 | PASS，真实保存服务；状态持久化，Camera UUID 不变 |
| 重新打开项目摄像头仍在 | PASS，通过主窗口打开项目流程验证 |
| 切换不同项目、关闭项目 | PASS，立即清空旧列表，加载后无串项目摄像头 |
| 无项目创建和修改禁用 | PASS，按钮禁用，“请先打开项目”可见 |
| 双击最近项目 | PASS，既有 GUI 回归 |
| 视频页摄像头关联 | PASS，真实关联保存后校验数据库关联 |
| 视频导入、片段保存、抽帧、取消及失败处理 | PASS，既有 GUI / 业务测试回归 |
| P3 已有功能 | PASS，既有 P3 参数、数据约束、模型流程兼容性测试；未执行 GPU 训练 |
| 数据库和任务系统 | PASS，既有迁移兼容及队列完成、取消、失败、恢复测试；业务实现未改 |
| 浅色列表、Tab、中文、下拉 popup | 真实 GUI 截图已检查；popup 白底深字且选中项清晰 |
| 高 DPI | PASS，真实 DPR=2.0，内容通过滚动访问，无两页叠加 |

执行命令（均使用既有 `.venv-p1/Scripts/python.exe`）：

```text
-m pytest tests/test_project_camera_tabs.py tests/test_p2_hotfix_gui.py tests/test_gui.py tests/test_p3_training.py tests/test_p2_adjustment.py tests/test_jobs_logs.py -q --tb=short --junitxml=artifacts/p2-project-camera-tabs-20261015/regression.xml
-m pytest tests/test_project_camera_tabs.py -q --tb=short --junitxml=artifacts/p2-project-camera-tabs-20261015/high-dpi.xml
```

首轮最终回归指定 QT_SCALE_FACTOR=1；高 DPI 专项指定 2；两者 QT_FONT_DPI=96、QT_ENABLE_HIGHDPI_SCALING=0。100% 实际窗口及截图为 1920×1080。200% 时 Windows 将窗口约束为逻辑 1282×702，截图 2564×1404，摄像头页滚动范围 133；不把它宣称为物理 1920×1080 下全部内容同时可见。高 DPI 已验证上下滚动和保存操作。

测试中目录选择使用模拟对话框返回路径，控件、窗口、业务服务和持久化均真实运行；截图来自 QWidget.grab / 实际 popup 抓取，不是合成界面。悬停配色通过样式定义检查，未宣称完成所有 Windows 主题组合的人工鼠标验收。

## 真实截图

截图共 6 张，均来自本轮独立测试项目。截图中的“未保存项目名称”是专门验证表单保留所用的测试名称，摄像头截图前已点击保存配置。

- [项目管理 · 1920×1080](../artifacts/p2-project-camera-tabs-20261015/project-tab-1.png)
- [摄像头管理 · 1920×1080](../artifacts/p2-project-camera-tabs-20261015/camera-tab-1.png)
- [项目管理 · 200%](../artifacts/p2-project-camera-tabs-20261015/project-tab-2.png)
- [摄像头管理 · 200% 顶部](../artifacts/p2-project-camera-tabs-20261015/camera-tab-2.png)
- [下拉列表 · 100%](../artifacts/p2-project-camera-tabs-20261015/combo-popup-1.png)
- [下拉列表 · 200%](../artifacts/p2-project-camera-tabs-20261015/combo-popup-2.png)

原始测试结果：`artifacts/p2-project-camera-tabs-20261015/regression.xml`、`high-dpi.xml`。尺寸记录：`geometry-1.json`、`geometry-2.json`。

## 数据保护、限制与后续

没有修改数据库 schema、Camera/项目 UUID、媒体关联业务、训练代码或模型工件；测试创建的项目位于 pytest 独立临时目录。未生成或更新 EXE、Portable、安装包，未进入 P4/P5。

对上轮 `artifacts/p2-hotfix-p3-20261015/protected-before.json` 的 14,647 个历史文件重新计算 SHA-256，14,646 项一致，1 项不同：`E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2\project.sqlite`。当前文件最后修改时间为 2026-10-15T12:55:03（本机时间）。该清单并非本轮开工时快照，无法判断变化归属；本轮没有对该项目执行打开、迁移、保存、还原或清理。差异原样保留，没有用历史文件覆盖它。完整比较见 `artifacts/p2-project-camera-tabs-20261015/protection.json`；因此历史保护全量哈希检查记为存在待核对项，而非全绿。

本轮 GUI 修复可继续用于 P2 测试；P3 既有兼容回归通过。既有任务记录表明 P3 已完成，故不重复启动训练或重做模块，当前停止待审。打包冻结继续有效。
