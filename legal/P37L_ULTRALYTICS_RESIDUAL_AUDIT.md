# Ultralytics四个范围的残留审计

日期2026-10-19，基线deff366。审计明确区分运行技术隔离、历史开发仓库、拟议公开源码和未来payload，不能用隐藏菜单替代许可判断。

| 范围/实际路径 | 状态与真实调用关系 | 保留/待办 |
|---|---|---|
| 新RF闭包：core/application → services/training_router → rfdetr_training_service → compute/rfdetr_train_worker | 唯一新训练为Nano；独立.venv-rfdetr -I；MetaPath禁旧模块、权重/版本门禁、拒绝旧解释器/初始化，无自动旧后端回落 | 本轮只读核对源码及既有实际CUDA轨迹/环境21/96包；没有重新训练或据纯搜索冒充动态验收 |
| services/backend_policy、model_service、jobs/manager及GUI | 业务查询仅RF；旧/UNKNOWN新操作封禁；活跃GPU任务不被历史过滤丢掉；历史verify为文件哈希，模型导出复制文件不执行Ultralytics | 历史TrainingRun/ModelVersion UUID、状态、路径、SHA与关联原样保留；归档清单见既有P37报告 |
| compute/train_worker.py | 明确导入YOLO/settings/DetectionTrainer/NMS，含旧Trainer继承/恢复/导出逻辑；不在RF可达路径 | 历史保留，不能把它带入拟议Apache公共代码而不审其来源/许可；继承本身不足以证明复制，也不足以证明独立著作权 |
| services/training_service.py | 旧训练启动/配置入口抛LEGACY_READ_ONLY；只读数据预检与历史代码保留 | 不执行旧训练，后续批准后从正式payload排除；不删除历史源码 |
| compute/offline_worker.py、services/offline_demo_service.py | 旧YOLO predict实现仍在；新p35_offline任务在提交层和服务层拒绝，legacy_run也直接拒绝 | P3.7-B必须独立RF推理Worker/取消/输出校验，不能重新启用旧Worker或拷贝旧NMS逻辑 |
| services/offline_cache.py及旧demos缓存 | 当前身份含旧Ultralytics实现/环境hash；完成缓存load/回放只读，无模型加载 | B另建RF完整身份/schema，禁止跨后端命中；历史缓存不删除、不冒充RF结果 |
| datasets/exporters.py | yolo_detect/yolo_segment为独立文本/坐标转换，没有Ultralytics import | 正式GUI不列出，但开发兼容工具保留。YOLO数据格式不等于AGPL软件库；不因字符串移除合法格式 |
| compute/model_adapters.py、legacy_training_parameters.py | 旧架构描述与参数元数据仍在；纯描述不能等同加载YOLO库 | 适用来源按实际代码审查，不批量“改名”冒充RF |
| .venv-nvidia与原PT/ONNX/Checkpoint | Ultralytics8.4.176、thop2.2.2、platform0.1.84仍安装，48包历史环境；旧模型与训练工件保留 | 不将其site-packages/权重带入RF；权重权利与供应商主张另列LEGAL REVIEW |
| scripts/validate_p3_model.py、旧P0/P3/P3.5测试/benchmark/报告脚本 | 开发历史调用YOLO/NMS/LetterBox等；不是正式RF运行组件 | 本轮未运行；公共快照和最小payload分别白名单排除，不改现有Git历史 |
| packaging/nvidia依赖inventory/BUILD_PLAN、历史release lock与ivad.spec | 保留旧依赖与未来方案；现有spec是Lite且排除torch/Ultralytics，不等于完整RTX包获审 | 发布前按实际最终payload做闭包/许可/来源证明，不能从spec文本推断最终包零旧依赖 |
| reports/docs/真实截图/测试中的项目ID及配置 | 当前及历史Git包含保密素材；许可证审计报告本身也不适合直接公开 | 提议新建脱敏公共快照，先由著作权人批准；本轮没有建立公共仓库或发布 |

## 证据和未决范围

4环境当前发行版和原生清单在本轮SBOM；静态imports/动态find_spec、subprocess路由与导入阻断已阅读。既有 `artifacts/p37a-contract-20261019/.../result.json` 显示RF真实CUDA重载及禁止模块为空；该证据是前一轮实际运行，不能描述成本轮再次执行的GPU测试。完整ref历史扫描为37提交/661blob，仅可达对象；来源相似性鉴定、不可达对象、所有外部备份及模型法律权利尚未认证。

AGPL §2并不一般性地把一切训练输出变成covered work，但[Ultralytics官方](https://www.ultralytics.com/license)明确主张其训练权重也受许可约束，对内部研发/API亦有强立场。具体使用、衍生与权重性质须法务/权利方解释；本报告既不直接认定必须买，也不承诺开GUI即可保密所有旧资产。[准确8.4.176 AGPL文本](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.176/LICENSE)完整保留。

审计枚举/运行边界可以PASS，不等于整个历史仓库来源已认证。正式训练A范围保持零Ultralytics；全产品迁移仍PARTIAL，未来发行仍BLOCKED。P3.7-B需另行批准，且必须使用独立RF实现、显式类别映射、新缓存身份、正确取消和来源/结果导出验收。本轮不实施任何一项。
