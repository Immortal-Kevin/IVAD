# Windows NVIDIA RTX P3.5 展示版发布验收

日期2026-10-16。**最终状态：BLOCKED，未构建、未正式分发。**

## 授权和实际执行

用户一次性授权当前P0–P3.5安装版，并要求发布前许可门禁。源码基线nvidia-first / 66e5846，开始工作区干净。已核对构建脚本、入口、冻结模式、计算Worker路径、依赖、实际视频DLL许可、设备元数据和已有报告；用户确认暂无Ultralytics授权或已批准AGPL发行方案。

按本轮门禁停止正式构建/分发；没有擅自开源、购买许可或把Lite安装包伪装为完整NVIDIA展示版。详情见P3_5_RELEASE_LICENSE_AUDIT.md。本轮仅新增审计文档和阶段/冻结记录，不修改业务、模型、打包脚本或驱动/环境。

## 交付与验收表

|要求|真实结果|
|---|---|
|IVAD_Platform_v1.0_P3.5_NVIDIA_Setup.exe|未生成；无可提供路径、体积或SHA256|
|IVAD_Platform_v1.0_P3.5_NVIDIA_Release.zip|未生成；无可提供路径、体积或SHA256|
|Windows图形安装/卸载/快捷方式|NOT TESTED，没有安装包|
|干净系统/无Python安装启动|NOT TESTED；没有以开发机源码启动冒充|
|安装版RTX5070Ti CUDA/训练/视频推理|NOT TESTED；历史源码GPU通过不等于本次安装通过|
|其他RTX及Windows10/其他Windows11|NOT TESTED，矩阵见docs/P3_5_NVIDIA_RELEASE_GPU_MATRIX.md|
|P0–P3.5功能|保留此前源码验收成果，本轮未重跑全套或声称安装版通过|
|许可再分发核查|BLOCKED/未闭合；没有已批准发行方案，FFmpeg/Qt/NVIDIA运行库仍待核查|
|数据保护|PASS，本轮原项目全表及1578工件hash相等；251帧匹配登记hash；原视频和12历史缓存匹配此前保护清单|
|旧发行文件|既有P2 ZIP及SHA文件hash未变化；没有覆盖旧包或声称旧包符合本轮要求|
|PACKAGING_FREEZE|已恢复TRUE；本次因阻断结束，不自动续用一次性授权|

## 技术预审发现

1. packaging/ivad.spec是P2 Lite onedir配置，显式排除torch、torchvision、onnxruntime和Ultralytics。现有独立.venv-distribution为PyInstaller6.22.3，未新增依赖。旧P2分发记录本身为BLOCKED，不能直接贴新标签发布。
2. ApplicationServices默认sys.frozen即lite=True，会不注册p3_train/p3_validate/p35_offline；冻结入口仍使用IVAD P2 Beta/P2Beta应用标识，尚非要求的v1.0 P3.5 NVIDIA展示版。
3. 默认Worker路径仍为资源根/.venv-nvidia/Scripts/python.exe；直接沿用旧spec不能保证目标机不需Python及开发环境。需要明确独立可分发Worker运行时、相对定位和必要依赖清单，不能复制整个venv或引用开发机路径。
4. 用户数据已有AppData方向，但完整安装目录只读、卸载/重装保留项目、快捷方式和中文安装界面仍需真正Setup实现与验证。PATH未发现Inno/NSIS工具，本轮未下载或安装。
5. 本机只读设备结果：RTX5070Ti / CC12.0 / 驱动617.42 / 16303MiB，torch2.9.1+cu128；未因此承诺RTX20–50或专业全系列验收。

上述为待授权解除许可门禁后的技术工作项，未擅自进入新的打包实现。未通过的功能不报告为完成。

## 数据与证据

独立目录artifacts/p35-release-audit-20261016，before/after为只读SQLite在线备份及表/工件盘点；protection.json、video-license.json、audit-summary.json、existing-release-hashes.json。原项目现有3训练/3模型/251帧/217标注/720修订/冻结v1均保留。本轮没有创建/安装/卸载程序，没有复制用户项目进发行包，没有新训练或模型推理。

## 冻结恢复及停止

用户仅授权本轮制作 Windows NVIDIA RTX P3.5 展示版安装包。此后安装包更新再次冻结，未经用户明确授权不得重新打包、更新、替换或重新分发新版。

本轮因许可发行方案未明确而结束审计，PACKAGING_FREEZE=TRUE。后续P4/P5、GUI修改、模型支持或CUDA更新均不自动解除冻结。许可证/履约方案确认后仍需明确批准继续构建；不进入P4–P10，停止待审。


## 后续审计授权补充 2026年10月16日

用户随后批准继续内部依赖审计、构建方案和隔离验证，不正式分发；本次正式一次性授权仅在合规条件满足并由用户确定授权方案后继续，不因内部审计自动触发。详见THIRD_PARTY_LICENSE_AUDIT.md及packaging/nvidia/BUILD_PLAN.md。当前冻结保持TRUE，没有新增正式安装包。此前本报告BLOCKED及NOT TESTED原始结果保留，未改写成已构建通过。
