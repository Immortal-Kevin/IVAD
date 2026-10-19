# 用户许可证行动清单

日期2026-10-19。所有事项均为拟议行动，未自动实施；无必需付费购买项。P0先于公开、关联公司交付或外部演示，P1先于发行，P2可随后完善。NO ACTION仅表示不额外申请，不免除通知义务。公司法务成本不等于第三方许可证费用。

| 编号/类别 | 组件 | 是否需要付费 | 是否需要申请授权 | 用户要做什么 | Codex能完成什么（须授权） | 免费替代方案 | 官方链接 | 优先级 |
|---|---|---|---|---|---|---|---|---|
| L01 LEGAL REVIEW | IVAD自研产权/公开方案 | 无法证明需付第三方费 | **需著作权人批准公开及许可** | 确认职务/委托/合作贡献归属，书面决定A/B、公开范围与商业秘密清单 | 分模块来源索引、白名单、合成夹具和公开前扫描 | 暂保留私有仓库，不发布 | [Apache定义和授予范围](https://www.apache.org/licenses/LICENSE-2.0) | P0 |
| L02 LEGAL REVIEW | 视频/标注/模型/配置/截图/Git历史 | 许可费用通常非该问题，权利前提待核 | 需公司及数据控制方同意用途/接收方 | 指定资产所有者、法人、访问/导出责任人；确认摄像头拍摄和委托数据使用权 | 扫描可达历史、OCR/秘密扫描、构建全新脱敏快照；不改既有历史 | 仅合成数据；不公开现有仓库或报告 | [GPL数据/输出条款§2](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.176/LICENSE) | P0 |
| L03 ATTRIBUTION | RF-DETR 1.11.2 Nano与Apache指定权重 | 无需版税（核实范围内） | 无通常额外申请 | 批准仅Nano指定资产、保留通知；不把上游权重当公司独占资产 | 固定URL/SHA、版权/Apache全文、适用NOTICE、修改说明；更新权重版本时复审 | 保留已核实Nano，不用Plus | [固定官方许可说明](https://github.com/roboflow/rf-detr/blob/7433d5919d0f7e72cc6cb78663e0a731afd499e0/README.md#license) | P1 |
| L04 ATTRIBUTION | DINOv2/LW-DETR/ConditionalDETR/DETR等来源 | 适用宽松许可路径无需版税 | 通常不需；不明来源先查 | 确认派生代码来源材料可用于公司项目 | 保留Roboflow/Baidu/Microsoft/Facebook等原文件头与各文本、逐版本比对 | 仅用已封存上游原包 | [DINOv2](https://github.com/facebookresearch/dinov2/blob/main/LICENSE) | P1 |
| L05 COMPONENT REPLACEMENT / VENDOR CONFIRMATION / LEGAL REVIEW | 历史Ultralytics代码/PT/ONNX | **本轮不买**；仅若未来坚持其专有嵌入且免费路线不适用时再评估 | 有争议时需供应商书面解释及法务意见，不等于现在申请付费 | 确认不再新用旧引擎；就权重/内部研发/衍生范围询问法务，禁止擅自公开保密权重 | 排除正式payload、P3.7-B独立实现及来源审查；保留归档 | RF-DETR Nano替换运行链；旧权重只读保留 | [供应商主张](https://www.ultralytics.com/license)、[AGPL原文§2/5/6/13](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.176/LICENSE) | P0 |
| L06 SOURCE OBLIGATION / ATTRIBUTION | PySide6/Shiboken/Qt 6.8.3 LGPL子集 | 有免费路线，不建议买Qt | 一般无需申请；需公司接受履约方案 | 指定源码交付/书面offer维护人，应用条款保留适用调试/替换权利 | 精确对应源码/修改说明、LGPL/GPL文本、第三方通知；隔离实际payload替换验收 | 保留动态Widgets/Svg，非重写全部GUI | [Qt义务](https://www.qt.io/development/open-source-lgpl-obligations)、[PySide6](https://doc.qt.io/qtforpython-6.8/licenses.html) | P1 |
| L07 COMPONENT REPLACEMENT（排除未用模块） | Qt Charts/DataVisualization/Quick3D/VirtualKeyboard等 | 排除未用模块无需付费 | 不使用无需商业授权 | 确认产品不需这些模块；若未来需要重新审议GPL/商业条件 | 逐DLL白名单和加载/最终payload验证，不把全部Addons当LGPL | 现有Widgets及自绘图表 | [GPL-only模块清单](https://doc.qt.io/qt-6.8/licensing.html) | P1 |
| L08 BUILD REPLACEMENT / SOURCE OBLIGATION / LEGAL REVIEW | PyAV 15.1.0/19.0.1及FFmpeg | 免费适当构建可行；专利成本不能预断 | 必要时向构建方取来源；法务确认codec适用权利 | 选支持格式/部署地区/编码用途；允许另行测试免费替代 | 核查flags/静动态链接、准确源码/脚本/通知；比较并验证LGPL共享构建/替代编码与PTS | 经审LGPL FFmpeg；Windows Media Foundation（系统版本/codec可用性另验） | [FFmpeg](https://ffmpeg.org/legal.html)、[MF](https://learn.microsoft.com/en-us/windows/win32/medfound/about-the-media-foundation-sdk) | P1 |
| L09 BUILD REPLACEMENT | OpenCV 5.0.0.93自带FFmpeg/图像库 | 可有免费构建路线 | 一般无需申请，二进制不明需来源确认 | 确认是否允许从最小包排除未用视频后端 | 保留所需图像功能；构建不含未核实codec后端并回归 | 复用已核实PyAV解码；适用图像任务用Pillow/NumPy | [OpenCV](https://opencv.org/license/)、[FFmpeg](https://ffmpeg.org/legal.html) | P1 |
| L10 ATTRIBUTION / VENDOR CONFIRMATION | CUDA12.8/cuDNN9.10.2及NVIDIA DLL | 不等于需要AI Enterprise，当前无必需付费证据 | 用户/公司须接受适用SDK条款；清单不明才确认 | 明确使用实体、服务器接收方；签收再分发条款审阅 | 每个DLL匹配指定redistributable、用途、通知、EULA版本和SHA；不捆绑驱动 | 目标机按批准的官方方式安装相应组件；仍需验收Torch携带DLL闭包 | [CUDA12.8.1](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html)、[cuDNN9.10.2](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html) | P1 |
| L11 ATTRIBUTION | Torch2.9.1+cu128/Torchvision0.24.1+cu128/ONNX1.20.1/ORTGPU1.24.4 | 宽松本体通常无需许可费 | 通常不需额外申请；不转授NVIDIA权利 | 批准固定版本及适用通知维护 | 保留BSD/Apache/MIT及捆绑库通知、原生文件对应；ORT当前为已装可选/历史用途，非证明RF训练用它 | 保留正式需要者，排除未用工具 | [PyTorch](https://github.com/pytorch/pytorch/blob/v2.9.1/LICENSE)、[ORT](https://github.com/microsoft/onnxruntime/blob/v1.24.4/LICENSE) | P1 |
| L12 SOURCE OBLIGATION | certifi MPL-2.0等文件级copyleft | 免费但有条件 | 通常不需要 | 同意提供所分发covered files的源码/获取安排，修改时保留MPL边界 | 准确文本/源版本、修改文件清单；不将整个应用误改MPL | 不需要则排除；需TLS时正常履约 | [MPL2.0 §§3.1–3.3](https://www.mozilla.org/en-US/MPL/2.0/) | P1 |
| L13 ATTRIBUTION / NO ACTION | Python/SQLite、SQLAlchemy、Alembic、Pillow、NumPy、PyYAML及宽松传递包 | 本体免费路径，捆绑库另审 | 无一般强制申请；不买SQLite权利保证服务也不自动获所有法域意见 | 指定通知维护人 | 按187条SBOM保留329份原文，处理OpenBLAS/图像库等复合通知 | 原组件，缺包时不随意换版本 | [SQLite](https://sqlite.org/copyright.html)、逐包官方URL见SBOM | P1 |
| L14 ATTRIBUTION / LEGAL REVIEW | flatbuffers/polygraphy/onnxsim/pycocotools及NOASSERTION/缺通知项 | 未证明必须付费 | 通常先补准确上游文本；仍不明才联系权利方 | 对发行时确需且材料缺失的项作保留/排除决定 | 用具体版本补通知/源码来源，或闭包验证后排除，不标违法或PASS | 移除未用可选工具；替代须验证功能/版本 | [完整逐组件清单](P37L_FULL_SBOM.md) | P1 |
| L15 LEGAL REVIEW | 独立法人/甲方服务器/局域网API | 取决条款与权利，不预设购买 | 需公司/接收方明确软件接收和条款主体 | 提供法人、设备所有者、用户范围、是否交付副本/容器、数据协议 | 形成交付矩阵、鉴权/RBAC/日志与最小暴露验证方案 | 同法人受控本机演示优先；不靠“同集团/仅API”豁免 | [AGPL定义/§13](https://raw.githubusercontent.com/ultralytics/ultralytics/v8.4.176/LICENSE)、[NVIDIA EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html) | P0 |
| L16 NO ACTION（许可购买） | TensorRT SDK/Python、FastAPI、Uvicorn、RF Plus | 四环境未检测到对应发行版/当前业务调用，不据规划购买；ORT捆绑TensorRT Provider单独列于原生清单 | 当前无申请 | 若将来确需，先批准范围与版本 | 到时重新盘点/许可/保密检查 | 当前无此需求，Nano继续 | 以未来选定组件官方条款为准 | P2 |
| L17 ATTRIBUTION / VENDOR CONFIRMATION | CPython3.12.14、SQLite3.53.1、OpenSSL3.5.8、zlib1.3.2及MSVC运行库 | 宽松/免费运行路线，不据本机捆绑来源直接认定可任意再发 | 原包链不明需提供方材料；MSVC按适用redist条款核对 | 确定未来构建所用官方运行时来源及条款主体 | 补准确原包、PSF/Apache/zlib/第三方原文、每个runtime DLL许可对应；不修改系统Python | 经批准的独立官方CPython构建/目标机运行时 | [平台补充SBOM](licenses/p37l/PLATFORM_SBOM.json)、[SQLite](https://sqlite.org/copyright.html) | P1 |
| L18 NO ACTION / ATTRIBUTION（按实际文本） | PyInstaller6.22.3、NumPy捆绑GCC runtime例外 | 免费例外路径，不需为产物自动购买或改GPL | 无通常额外申请，需满足例外及依赖许可 | 批准最终构建工具/通知范围 | 核对bootloader/GCC例外适用文件及修改情况，保留实际要求的文本；不把GPL工具误算作业务GPL | 保留经审工具/运行子集 | [PyInstaller](https://pyinstaller.org/en/stable/license.html)、本地NumPy完整LICENSE | P1 |

## 用户本人优先办理

1. P0：提供公司权利主体与各部署接收方/服务器信息，指定数据/模型所有者和保密负责人，批准A/B边界；未批准前保持私有。
2. P0：让公司法务审阅历史YOLO权重和供应商主张与AGPL原文之间的解释问题；不得以“软件愿开源”为由公开秘密权重/配置。
3. P1：批准免费的codec路线和支持格式，确定第三方通知/对应源码维护职责、目标机SDK条款接受主体。
4. P1：在各门禁证据闭合后，另行批准工程整改和未来打包/分发；本审计不代公司签字。

## UNRESOLVED / NEEDS USER ACTION

尚缺：著作权和数据控制证明、接收方法人/服务器清单、选择的公开许可与私有模块独立性法律意见、codec/专利适用范围、最终payload、Qt对应源码与替换实测、NVIDIA逐DLL可分发确认、若干原包/静态库材料。每项有上表责任人与免费替代，不以笼统“以后再审计”替代行动。PAID LICENSE未列为当前必办事项。
