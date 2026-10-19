# P3.7-L 许可证与保密架构专项审计

日期：2026-10-19。实际基线 `deff3667233e0fcb938c9b94bfeafc96a112d87e`，分支 `feature/p37a-rfdetr-training`。任务中较早的b0d56b7未被恢复；原有两份未跟踪规划文件保留。本轮仅只读调查、复制许可证原文与生成报告，未整改业务代码、依赖或环境。

**存在不购买第三方商业许可证继续研发的明确路线：使用已核实的RF-DETR Nano/Apache组件、宽松许可业务依赖，并履行所用LGPL库义务。** 不必为了保密工业数据而购买Qt或NVIDIA AI Enterprise，也不必先公开整个IVAD。没有证据证明本项目必需购买任何商业许可证；工程人工、法务和部署成本与许可费不同。

这不是当前软件已获无条件部署或分发认证。历史Ultralytics争议、FFmpeg构建及codec权利、Qt对应源码/替换材料、NVIDIA逐DLL再分发和著作权/数据控制权仍需解决。`PACKAGING_FREEZE=TRUE`、`DISTRIBUTION_STATUS=BLOCKED`。

## 本轮实际发现

- 四环境：GUI21、RF96、旧YOLO48、历史Lite/构建22个发行版记录，共187条，跨环境允许重复；1,687条原生文件逐SHA记录，329份原样通知材料。顶层许可不替代捆绑DLL许可。FastAPI/Uvicorn/TensorRT未检测到对应安装发行版；局域网API是未来设计。
- RF-DETR 1.11.2只走Nano、独立环境/Worker；无rfdetr_plus安装。准确权重URL、hash与上游组件版权在许可证包。官方固定README区分Apache指定权重与PML 1.0的XL/2XL检测组件，不能按名字一概判断。[RF官方说明](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/README.md#license)
- Qt安装目录确有Charts、DataVisualization、Quick3D、VirtualKeyboard等GPL-only可选模块；不等于当前业务已调用。当前Core/Gui/Widgets/Svg及qwindows有历史实测依据；最终payload须按模块白名单审查。保留现有Widgets GUI比全部重写合理。[Qt 6.8模块许可](https://doc.qt.io/qt-6.8/licensing.html)
- 当前PyAV实际FFmpeg配置含x264/x265，库返回LGPLv3+字符串但构建/链接来源未闭合。人工片段导出确实调用libx264，不能只处理旧AI Worker后就宣布视频链合规。[FFmpeg官方](https://ffmpeg.org/legal.html)
- 全部可达Git refs有37个提交、661个blob，HEAD359个追踪文件中有9张真实界面截图。另有真实项目引用、绝对路径及参数/关联信息。**当前仓库及完整历史不可直接公开**。模式扫描未发现匹配的长字面量凭据候选，但不能据此出具无秘密认证；未做图片OCR、不可达对象/LFS远端及所有高熵秘密验证。

## 谁要做什么

用户优先完成：确认公司著作权/职务或委托成果授权及数据控制权；确认各部署接收方法人和服务器所有权；批准A闭源或B部分开源的目标边界；指定保密负责人、访问权限及导出审批制度。对历史YOLO权重保密与供应商许可主张，需法务解释，必要时只请求书面确认，先不购买。

Codex可在另行授权后：建立脱敏公共快照白名单/扫描门禁、外置私有资产目录、补通知/对应源码安排、限定Qt模块及测试库替换、构建并验证免费codec替代、完成NVIDIA逐DLL清单、验证最小依赖闭包。上述均未在本轮实施。

优先顺序、逐组件费用/授权/替代路线见 [行动清单](P37L_LICENSE_ACTION_CHECKLIST.md)。[保密分层](P37L_OPEN_SOURCE_BOUNDARY.md)和[10种部署场景](P37L_DISTRIBUTION_SCENARIOS.md)分别处理公开源码与私有资产，不假定“本地”等于安全，也不假定“内部”等于没有分发。

## 当前决策

建议先沿用A路线继续受控RF研发，同时按B路线设计可选公共边界；用户/著作权人批准前不实施开源许可。部分开源只能针对真正独立、有权许可的通用代码；不能把与copyleft形成单一衍生作品的私有业务模块仅靠文件夹或进程名隔离后强行保密。Apache不会覆盖其他组件，也不会为数据自动施加访问控制。[Apache-2.0](https://www.apache.org/licenses/LICENSE-2.0)

P3.7-A功能技术PASS仍有效；Qt历史问题IVAD-QT-001保持PARTIAL。P3.7-B已有独立RF、冻结数据、Registry和锁的技术基础，但未获本轮实施授权；后续开发应以前述边界和codec/缓存风险为输入。审计交付完成不等于整改完成；各领域等级见 [就绪矩阵](P37L_READINESS_MATRIX.md)。

## 材料复核

[VALIDATION.json](licenses/p37l/VALIDATION.json)记录：187个发行版的版本/METADATA、329份通知的原件与副本SHA、1,687条原生文件SHA复核一致；9个必需报告与本地链接检查通过；原有已追踪文件未变，两份用户规划与历史Qt证据SHA未变。这里只验证审计材料一致性，不把验证PASS写成全部许可证已认证。所有正式业务源码、数据库、旧权重和环境保持原有用途，未实施整改；网络只读取官方公开许可/文档，没有上传本地代码、模型或工业数据。
