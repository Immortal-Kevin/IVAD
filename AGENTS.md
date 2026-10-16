# 项目执行规则

用户明确批准P2，当前仅执行P2。未经用户再次明确批准，禁止进入P3–P6。
2026-10-15用户Development Directive v3优先：P2最终验收PASS后已授权自动进入P3，P2若有阻断立即停止；P3结束停止，P4–P6未授权。PACKAGING_FREEZE = TRUE：禁止构建/更新EXE、Portable、Setup和分发，既有包原状保留，解除冻结须用户明确批准。
2026-10-15执行结果：P2最终及P3源码工程验收PASS，Schema0006，当前已停止等待用户审阅。P4–P6仍未授权；不恢复打包，不将实验/软件夹具当作工业生产批准。详见reports/P3_ACCEPTANCE.md、docs/CURRENT_TASK.md。
2026-10-15后续P2 Hotfix已PASS：源码P3-Dev.2/Schema0007，既有P3兼容且业务源码/训练工件保留。P3此前已完成，返工后不重启P3，停止待审；旧P2/P3验收报告不覆盖。PACKAGING_FREEZE仍为TRUE，P4–P6未授权。报告reports/P2_HOTFIX_DURING_P3.md。
遵守 SRS、ARCHITECTURE、CODEX_MASTER_PROMPT 和 P0_IMPLEMENTATION_PROMPT。
项目专属 venv；禁止修改其他 AI 环境、全局 Python、驱动或系统配置。
AI 必须 GPU 执行，失败即记录，不自动降级 CPU。报告保留真实原始证据。
Intel 原 P0 BLOCKED 历史独立保留；本包未包含历史报告，不重建或覆盖。
P1采用独立.venv-p1，保留P0环境与全部资产。GUI业务经服务层，耗时工作移至后台。
P2复用P1 GUI/数据库/日志/队列；普通解码/人工标注CPU允许，AI训练/推理仍GPU-only。
历史P0/P1报告、锁文件与运行证据不得覆盖；P2输出写artifacts/p2。新增依赖仅GUI环境。
仅本地Git版本追踪，不建立远程；排除虚拟环境、模型、日志、缓存与用户数据。

2026-10-15 Camera Registry Hotfix v2：代码/80项针对性测试通过，Schema目标0008；真实项目仅只读备份且仍0007，同一Camera UUID被历史EDIT复用。禁止未经用户另行批准恢复/补建真实摄像头或改动关联。P3已完成，不重复训练；打包冻结，P4–P6未授权。报告reports/P2_CAMERA_REGISTRY_PERSISTENCE_HOTFIX.md。

2026-10-15 Annotation & Camera Dataset Hotfix完成：103不同用例/高DPI回归通过，Schema0008不变。真实库只读（3摄像头251帧22标注），不得按旧快照还原或猜测关联；保留P3，不重训，不打包。两张历史测试截图覆盖例外已披露，后续所有测试截图必须写本轮独立目录/临时目录。详见reports/P2_HOTFIX_REGRESSION.md。

2026-10-15 Annotation Workflow Simplification功能PASS：69项最终整组/高DPI4项通过；一次混合GUI测试原生访问冲突未定位，串行复验未复现，必须保留报告限制。Schema0008不变，P3不重启，打包冻结，后续截图仅本轮独立目录。详见reports/P2_ANNOTATION_WORKFLOW_SIMPLIFICATION.md。

2026-10-15 顶部标注快捷按钮Hotfix PASS：58项回归/200%专项4项通过，162项保护哈希0变化。Schema0008不变；P3此前已完成，不重启，打包冻结，停止待审。历史Qt原生访问冲突限制保留。报告reports/P2_TOP_TOOLBAR_SHORTCUT_HOTFIX.md。

2026-10-15 用户批准P3 Dataset UX Hotfix已完成：68项回归及200% GUI1项通过，Schema0008不变。新GUI用显式human-auto-v1实验政策，不改原审核/旧冻结政策；真实8525来源1组200帧划分LIMITED。163项选取保护哈希0变化。P3原成果完成，停止待审，打包冻结，P4–P6未授权。报告reports/P3_DATASET_UI_HOTFIX.md及对应VALIDATION/SPLIT结果。

2026-10-15 P3 Dataset Hotfix v2 PASS：97不同用例/200% GUI1项通过。8525为旧GUI误显带偏移PTS，200条time_us正确；仅派生时间，不写历史。Schema0008不变，165项保护hash0变化，P3原成果保留，停止待审，打包冻结、P4–P6未授权。报告reports/P3_DATASET_UX_HOTFIX_V2.md。

2026-10-16 Dataset Lifecycle Hotfix PASS：127不同用例、后续11复验/200%3项通过。Schema头0009，只增Dataset.details/revision；真实项目仍0008只读，166项保护hash0变化。旧内存草稿不可虚构恢复，副本200重启/版本已验；停止待审，不重训，PACKAGING_FREEZE=TRUE，P4–P10未授权。报告reports/P3_DATASET_PERSISTENCE_HOTFIX.md等四份。

2026-10-16 Workflow & Training GUI Hotfix：数据集检查先原子保存，工程/严格模式及签名风险确认；训练响应双栏/预检门控/恢复原参数只读。62不同用例、末次100%2项/200%3项通过；Schema0009不变，真实7a01bcad/4a1c7df7/8525test1 v1及660文件/全表/5选取环境hash0变化。无新训练/打包，历史Qt及epoch显示差异保留，停止待审。详见reports/P3_WORKFLOW_GUI_HOTFIX.md。

2026-10-16 用户明确批准P3.5离线演示（不是完整P4）：Part A模型4a1c7df7/真实GUI/CUDA/ONNX已PASS，新增主程序离线预处理回放/真实框/导出。48不同pytest、3实际CUDA比对通过，200%11+最终1复验；原项目2训练/2模型全表、1120工件及256选取文件0变化。无schema变化、无新训练/安装/打包，背景低置信度框需人工复核，不宣称独立工业质量PASS。PACKAGING_FREEZE=TRUE，停止待审，P4–P10仍未授权。报告reports/P3_MODEL_VALIDATION.md、P3_5_OFFLINE_DEMO_ACCEPTANCE.md。


2026-10-16 P3.5 GUI重构：两页/统一视频选择/真实探测/双手柄原片预览/大回放与详情导出，57不同用例及100%/200%复验通过；必要10帧CUDA及schema2精确缓存通过。真实项目全表、1120工件、12历史缓存文件0变化，无schema/Worker/TrainingService/Registry修改，无新训练或打包。PACKAGING_FREEZE=TRUE，P4–P10未授权，停止待审。详见reports/P3_5_DEMO_GUI_HOTFIX.md。


2026-10-16 P3.5 Three-Tab Hotfix：三页、真实状态、返回配置、自动跳转/完整身份加载及4帧CUDA通过；59不同用例PASS，2个combo popup用例XFAIL，完整主题验收PARTIAL，Windows系统浅色切换NOT TESTED。原项目全表/1120工件/13视频与缓存文件hash不变；只改GUI/事件/主题/测试，无引擎或schema修改。PACKAGING_FREEZE=TRUE，P4–P10未授权，停止待审。详见reports/P3_5_THREE_TAB_GUI_HOTFIX.md。


2026-10-16 本周最终收尾：仅P3.5播放器与P0–P3.5管理层Word报告。标准1096×617、专注1440×810（1920×1080/100%），125/150%及11不同针对性GUI用例通过；12页/11图号（10不同截图）Word已真实渲染复核。原项目3训练/3模型全表与1578工件0变化，251帧登记hash一致。QMenu人工确认正常，不改主题，历史XFAIL保留。PACKAGING_FREEZE=TRUE，无重训/打包/P4；本周工作结束，停止等待下一次明确授权。报告P3_5_FINAL_PLAYER_HOTFIX.md、IVAD_REPORT_SOURCE_INDEX.md。


2026-10-16 Windows NVIDIA P3.5一次性打包审计结束：基线66e5846，用户确认暂无Ultralytics授权/已批准AGPL发行方案；按本轮发布门禁BLOCKED，未构建Setup/Release ZIP，未安装/卸载或重训。原项目全表/1578工件及既有ZIP保护通过。现有打包仍P2 Lite，不能冒充完整NVIDIA包。PACKAGING_FREEZE = TRUE已恢复。用户仅授权本轮制作 Windows NVIDIA RTX P3.5 展示版安装包。此后安装包更新再次冻结，未经用户明确授权不得重新打包、更新、替换或重新分发新版。停止待审，不进入P4–P10。见reports/P3_5_WINDOWS_RELEASE_ACCEPTANCE.md、P3_5_RELEASE_LICENSE_AUDIT.md。
