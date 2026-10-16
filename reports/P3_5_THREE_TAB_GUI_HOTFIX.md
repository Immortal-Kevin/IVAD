# P3.5 三 Tab GUI Hotfix

日期：2026-10-16。总体结论：**PARTIAL**。三Tab、自动跳转、缓存自动加载、状态栏、返回配置及真实GPU流程通过；完整下拉弹出状态及Windows浅色系统主题未完成验收，不能宣称全部PASS。

## 修改文件与边界

- `ivad_app/gui/offline_demo_layout.py`：三Tab，独立配置左右栏，大画面回放及常驻返回按钮；技术UUID移至详情/Tooltip。
- `ivad_app/gui/offline_demo_page.py`：共享项目/任务/缓存状态、真实进度、自动跳转/加载、失败提示、会话与加载世代保护。
- `ivad_app/gui/offline_demo_interaction.py`：当前配置快照、完整缓存重新匹配、结果跳转Tab 2及配置变化说明。
- `ivad_app/gui/style.py`：统一补齐QMenu、QAbstractItemView及项目状态配色。
- `tests/test_p35_gui_redesign.py`：三页实际GUI、实际短CUDA、范围、导入、回放和导出。
- `tests/test_p35_three_tab.py`：提交失败、任务失败、旧回调保护、进度/完成夹具和主题检查。
- 更新Markdown指南和阶段记录，不制作Word/PDF。

未修改CUDA Worker、视频解码器、训练引擎、Model Registry、DatasetVersion或数据库服务，无migration、依赖安装、驱动修改或重新训练。PACKAGING_FREEZE=TRUE，无软件打包。

## 最终三个Tab

1. **识别配置与视频选择**：左侧项目真实厂区（无厂区仅项目名）、Camera Registry、兼容模型、GPU和Confidence；右侧统一视频菜单、探测元数据、原片预览、双手柄及精确范围。底部仅一套开始/查缓存/刷新/取消按钮。完整Model/Dataset UUID在Tooltip和第三页。
2. **AI 识别演示**：常驻真实状态栏和EXPERIMENTAL/LIMITED限制、当前任务进度、大视频、时间轴/逐帧/速度/精确跳转、返回修改配置。不再与配置及原片共占同一页。
3. **检测详情与导出**：任务信息、来源、完整模型/Dataset UUID、GPU、实际参数、默认有检测帧/全部帧、CSV/JSON/视频/当前截图。点击记录切换Tab 2并定位。

切换Tab不重置选择、不触发推理。使用原有播放器和真实缓存；高DPI低高度下保留必要区域滚动，不再多层叠放配置和回放。

## 启动、完成与异步保护

验证视频/模型/GPU/区间后异步完整匹配缓存；匹配失败说明原因，查缓存按钮不提交GPU任务。新任务成功登记ID后才进入Tab 2，展示真实QUEUED/RUNNING百分比。提交失败仍在Tab 1，无假进度。推理失败显示FAILED和真实队列错误，停止本次播放，不自动载入历史结果。

SUCCEEDED仅加载该任务返回的路径；先校验缓存封存及视频，再比较完整cache_identity（来源/权重/类别/版本/区间/阈值/GPU/预处理/NMS/实现与环境等）。GUI还检查模型/媒体/区间/阈值一致性。加载成功后更新缓存引用、PTS/时长并保持暂停，显示“处理完成，可以播放”。不改写旧manifest，不为旧缓存伪造新身份。

Root会话世代、加载请求世代、配置快照共同保护异步回调；旧项目/旧请求完成不能覆盖新会话。运行中锁定影响结果的输入、刷新与历史入口，但可自由切Tab；明确点击取消才取消任务。新任务运行时清空当前结果表，旧文件及引用保留，停用旧视频导出入口，避免冒充新结果。

## 状态栏和返回配置

状态来自提交快照或加载的封存manifest，结合当前项目Registry解析名称。显示摄像头、架构/短版本、实际阈值、等待/GPU处理中/完成/已加载缓存/取消/FAILED、模型级别；附近保留LIMITED和工程实验限制。未硬编码8525或模型版本。

“返回修改配置”只切Tab 1，保持项目、摄像头、视频、模型、GPU、范围、阈值及缓存引用；任务运行不受影响。修改阈值等会明确提示“当前配置与已有缓存不一致”，不会改旧回放状态栏。新匹配进度/错误在配置页显示，旧回放仍保留它自己的缓存状态，避免混淆。技术任务ID和缓存路径保留在Tooltip及详情。

## 下拉主题调查与未解决项

已确认直接缺口：统一主题之前有QComboBox/QAbstractItemView规则，却没有**QMenu**规则。“选择演示视频…”实际是QPushButton挂接QMenu，不能被QComboBox规则覆盖；QWidget规则指定深色文字，而未指定菜单底色，在本机Windows深色主题下有深底继承风险。只读查注册表：AppsUseLightTheme=0、SystemUsesLightTheme=0；没有修改系统主题。

现统一theme明确菜单白底深字、悬停浅蓝深字、选中海蓝白字、禁用浅灰；为通用item view及combo补充状态，保留sidebar导航独立规则。本机实际QMenu展开、键盘选择、鼠标悬停和禁用测试项有真实Qt截图；Qt Palette深浅两组截图均清晰。

**未解决验证阻断：**当前Qt自动化调用模型QComboBox.showPopup()时，控件可见、已启用、3个项目，但item view/window未变为可见；点击和等待复验亦未定位原因。测试明确XFAIL，未用直接强制show item view伪造正常展开。故QComboBox真实展开/悬停/选择/禁用/列表滚动不能报告PASS；Camera/GPU及其他页面popup也未完成全状态复核。本轮没有证据断言其为Windows native popup根因。需后续人工复核或继续定位。

Windows实际深色环境已使用；Qt Palette浅/深测试不等于Windows系统浅/深切换。Windows浅色系统主题：NOT TESTED。完整下拉菜单配色验收：PARTIAL。

## 测试结果与证据

独立证据根：`artifacts/p35-three-tab-20261016`。原项目只读审计，GUI/服务写入仅副本和独立夹具。

|批次|真实结果|说明|
|---|---|---|
|main-run.xml|57 PASS / 3 FAIL|真实4帧CUDA、取消、7格式组合、P1/P2/P3针对性回归通过；失败为提交错误夹具类型及两组popup不可见|
|accepted.xml|3 PASS / 2 XFAIL|提交错误夹具改用服务AppError后通过；新增成功/进度/缓存身份夹具与真实三页回放/导出通过；popup未验收|
|dpi125.xml|2 PASS / 2 XFAIL|125%三页与状态/返回测试通过，popup仍未验收|
|dpi150.xml|2 PASS / 2 XFAIL|150%同上|
|final-theme.xml|2 XFAIL|最终QMenu截图检查先通过，随后combo展开未验收|
|final-verified.xml|3 PASS（复验）|最终配置错误与旧回放消息分离、状态/完成/缓存/三页截图|

汇总59个不同用例PASS，2个主题用例XFAIL（统计见test-summary.json），重复不累加。XFAIL是未解决项目，不作为通过。提交失败/FAILED/42%进度及旧回调使用明确测试夹具，不冒充实际GPU失败记录；实际CUDA成功和取消另有独立证据。最初一次命令使用不存在的测试文件名未收集用例，后续正确命令执行；开发期失败证据全部保留。

真实GPU回归：原模型4a1c7df7副本，8525视频[7.640,7.800)秒，实际4帧；RTX5070Ti，包含启动/通信/渲染耗时12.247246秒，约0.327FPS，Worker峰值分配69431296字节（约66.2MiB，非整卡占用）。缓存9a6cb4c4-cc47-4a34-bf86-c049c1582043；自动跳转/运行中返回/完成自动加载/精确复用/更改阈值不误用/另一个短任务CANCELLED通过。未重复70秒整段或P0/P3训练。最终事件收尾复验复用已有真实缓存，不重跑GPU。

格式实际探测/导入/预览沿用并复验MP4 H264、AVI MJPEG、MKV H264、MOV H264、TS H264、M4V（MP4）H264、MKV HEVC；损坏AVI有错误且不崩溃。不是所有容器/编码组合保证。

### 分辨率与截图

100%实1920×1080：回放约993×559，原片预览区域973×551；1040×720回放353×199。125%实际1920×1080：977×550，原片973×540。150%受物理屏幕限制实际1709×936逻辑像素：727×409，原片842×396；不是虚称150%下1920逻辑像素全屏。均保持原宽高比，画面与时间轴无重叠断言通过，返回与状态栏可见。低高度内容可滚动。精确尺寸以各geometry.json为准。

![Tab1 配置](../artifacts/p35-three-tab-20261016/final-verified/tab-1-1920.png)

![Tab2 回放](../artifacts/p35-three-tab-20261016/final-verified/tab-2-1920.png)

![Tab3 详情](../artifacts/p35-three-tab-20261016/final-verified/tab-3-1920.png)

![125%菜单、深色Palette](../artifacts/p35-three-tab-20261016/final-theme/menu-True.png)

![150% Tab2](../artifacts/p35-three-tab-20261016/dpi150/tab-2-1920.png)

截图来自真实Qt窗口，不生成界面、不修改预测框。截图中的背景低置信度预测是模型真实输出，不是人工确认工业故障。

## 历史保护与最终状态

原项目SQLite在线只读备份/全表比较相等：251帧、217标注、720修订、3摄像头、8媒体、2训练、2模型及冻结8525test1 v1不变。1120工件hash相等；原视频与12个原历史缓存文件合计13文件hash相等，见protection.json。训练7a01bcad、模型4a1c7df7及其SHA/ModelRegistry关系保留。

P2正常负样本/多类别/历史标注与导航、P3类别映射/数据准入/模型注册及训练GUI等针对性回归通过；不等同于重新进行完整P2现场验收。没有新训练，无工业质量/泛化合格声明；当前视频为训练来源回放。历史Qt原生访问冲突未定位限制继续保留，本轮未出现该崩溃。

本轮三Tab/自动跳转/缓存/状态栏/返回配置：PASS。下拉完整验收：PARTIAL。系统浅色切换及popup滚动等：NOT TESTED。保持PACKAGING_FREEZE=TRUE，没有EXE/Portable/Setup/分发ZIP，不进入完整P4–P10，停止待审。
