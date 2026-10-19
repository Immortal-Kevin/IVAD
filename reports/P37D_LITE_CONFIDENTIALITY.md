# P3.7-D Lite 保密验收

日期：2026-10-19。范围仅北京金海泽地智能科技有限公司同法人研发部内部演示；接收方授权已确认，不再要求重复确认。本轮遵循新的Lite授权，先生成本机候选再审实际载荷。

源码/构建提交：`26dd8bcf10490384bcb993df4e0d38d35a9f9f8a`（其父工程提交`3fff1f734a2454f501a5b695f1adb8b76827a9aa`）；最终报告提交由本报告所属Git提交确定，提交后回执`artifacts/p37d-lite-20261019/closeout.json`和最终回复记录完整SHA。分支`feature/p37d-lite-demo`，基线`8b064b5e5fa8711e75293f189266aad99d92c502`。

**CONFIDENTIALITY_STATUS=PASS（本次载荷及已执行流程范围，不是全系统安全认证）。**

- 候选实际384文件扫描未命中原项目受保护标识/来源路径，没有SQLite项目库、工业视频、真实抽帧/标注/冻结集、摄像头配置、模型权重、旧环境或历史报告。原始数据没有复制进onedir。
- 正常首启创建的项目无媒体/帧/摄像头/类别/版本；所有测试素材均为自有合成色块视频。12帧/2目标/11正常样本只存在独立测试项目，不随候选交付。
- 程序目录与数据目录分离，最终真实EXE流程后程序树哈希不变，无字节码缓存；用户数据沿ProjectStore保存在自行选择的目录。程序替换不应删除项目，本轮没有执行安装/卸载或删除用户资料。
- AI服务/队列/导入/重编码门禁均在后台实施；无模型首次下载，无远程上传实现；正常流程Python网络审计0次，原生FFmpeg仅允许file协议，网络引用拒绝有日志。没有做OS级全网络抓包，不将此写为操作系统绝无网络通信；Windows自身WER/安全服务属于系统行为，本轮未改变其策略。
- 本轮原项目全表、2,328个项目及来源媒体文件、两份原规划文档、原Qt/Windows证据、四个旧环境已登记的native/notice/METADATA和原分支指针前后相同。保护结果五组全部true。旧权重/数据库/缓存未删除，系统Python/驱动/CUDA不变。

证据：`payload-audit.json`、`payload-files.json`、`payload-modules.json`、`release-acceptance/results.json`、`release-processes.json`、`protection-result.json`，均在`artifacts/p37d-lite-20261019`。保护快照含真实表信息和路径，是私有审计资料，不可把整个artifacts或仓库作为软件交付。

逐文件CSV的来源已按BUILD_ENV/CPYTHON_BASE/REPOSITORY标签归类；日志和运行模块清单仍可能含测试路径，保留本地，不复制进候选。凭据/商业秘密未发现的扫描结论仅覆盖已列规则与材料，不替代未来用户自由文本、诊断或崩溃转储的审阅。

Qt源码归档中的公开上游源码/测试素材是履行第三方义务的材料，不是IVAD开发夹具或工业数据；四份归档哈希与官方来源一致，目录扫描无Torch/Ultralytics/YOLO权重条目。未授权开源IVAD，未push/上传录像或模型，未向任何人发送候选。
