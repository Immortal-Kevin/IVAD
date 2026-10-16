# P3.5 Windows RTX 可复现构建方案

日期2026-10-16。状态：**审计方案已准备，构建输入未全部封存；不是已经复现成功的安装包。**仅内部研发/合规准备，不向领导交付，不改变公司开源状态。PACKAGING_FREEZE=TRUE；未来一次性正式构建仅在用户确认合规路径后按授权继续，完成后立即再次冻结。

## 1. 保留现有工具与双运行时

继续使用现有PyInstaller6.22.3及同版本hooks，GUI onedir沿用ivad.spec的基础收集方式。CUDA Worker另一个onedir，在一个应用安装载荷内，不形成第二套产品或第二个安装包。两者按各自实际依赖锁分别构建，避免合并NumPy/Pillow/PyYAML版本。

目录目标（未生成）：

```
<安装目录>/
  IVAD.exe
  _internal/                 # GUI Qt/PyAV/数据库/迁移与资源
  compute/IVADCompute.exe    # NVIDIA独立进程，包装原Worker入口
  compute/_internal/         # torch/Ultralytics/ORT及核实后的DLL
  notices/                  # 最终载荷对应许可证/通知/履约材料
  build-manifest.json        # revision、输入hash、组件和内部/正式级别
```

程序目录只读。设置/日志/目录索引放AppData，项目/录像/模型/缓存放用户选择目录。GPU锁采用同一用户所有实例共享的可写位置，而非安装目录；跨Windows用户GPU争用另行验收。不安装驱动、不动其他AI环境、不内置测试1号、私人录像、P0测试图片、实验权重或未明确授权的基础权重。

## 2. P2 Lite至完整RTX的必要最小适配

这些是**待实施项**，本轮没有把计划写成既有能力：

|位置|现状|正式构建前改动|
|---|---|---|
|packaging/ivad.spec|onedir且排除torch/ORT/Ultralytics|保留GUI分离，增加独立Worker构建spec；明确需要的Qt模块与数据资源，不盲收全部Addons|
|ApplicationServices|sys.frozen默认lite=True，AI jobs不注册|通过受校验build-manifest区分P2 Lite与NVIDIA edition，仍对缺GPU明确阻断|
|__main__.py|冻结程序标识P2Beta|使用P3.5 NVIDIA展示版名称和独立AppData目录，不覆盖旧Beta数据；不强制迁移项目|
|Device/Training/Offline服务|python -I -X utf8 script.py request|支持冻结Worker命令probe/train/offline；不能给EXE机械套用Python解释器参数；源码模式保留原调用|
|Worker入口|现有main及JSON请求/JSON-lines协议|薄分发入口复用原main；freeze_support与PyInstaller运行测试；不重写训练或解码引擎|
|GPU锁|脚本根/runtime/gpu-locks|显式可写共享锁路径，训练/推理一致；本机源运行默认路径不被安装版写入替换|
|基础权重|默认artifacts/p0/yolo*.pt，缺失即失败|不携带未经核实权重；提供合法显式导入/选择路径，并验真实可从新项目配置训练，不能让安装器下载代替许可|
|第三方/隐私|开发依赖和记录在venv/artifacts|仅按最终依赖/原生DLL清单收集；排除缓存、pytest、历史记录、用户路径和自动下载|

Worker进程启动前设置本机版本实际支持的YOLO_OFFLINE=true、YOLO_AUTOINSTALL=false、独立YOLO_CONFIG_DIR；导入Ultralytics前设置，sync关闭。离线缺权重应失败并提示，不能自动下载。需在最终冻结版验证所有网络/自动安装路径，不声称仅设置变量即完全离线。

## 3. 输入封存与可复现边界

当前runtime/build及build-tools的requirements-*.inventory.txt是**已安装版本清单，不是带wheel SHA256的完整lock**。默认extras/动态加载/原生DLL均须按最终hook输出补充，不能直接把62个版本对全部当作要分发的组件。

输入模板release-inputs.template.json的null均表示缺失，不是批准。正式构建必须封存：

1. 明确的源revision与git archive SHA256；仅白名单源码/迁移/GUI资源/必要Worker代码，不含runtime及项目数据。
2. Python3.12.14构建基底、Python DLL/标准库的来源、PSF及内含第三方材料和SHA256。本机基底来自Codex bundled runtime；已保存观察hash，但没有证明一个可公开获取、完整可复现的Windows基底归档。
3. 3个独立wheelhouse清单，每个whl固定文件名/版本/平台tag/SHA256/官方来源；torch/torchvision的cu128从官方索引单独取得，不允许在CPU wheel上静默替换。其他包从经核实官方PyPI；缺wheel时停止，不关闭TLS或改用不明二进制。
4. GUI/Worker/构建工具各自带hash的requirements。完整闭包包括Worker的ultralytics-platform/thop、OpenCV、科学计算库及其通知；不能只固定torch和ultralytics两个包。
5. 最终PyInstaller配置、PyInstaller hooks-contrib2026.8实际版本、NSIS工具归档（建议候选3.12，未下载/验收，需官方原件hash）及安装脚本hash。
6. 公司授权/开源履约决定记录、允许的接收范围、最终license/NOTICE/对应源码及必要书面提供方案。审计脚本不会自动作出法律判断。

Python官方3.12.14为source-only，不虚构python-3.12.14-embed-amd64.zip下载地址。可选处理：封存并核实当前基底再分发来源，或以官方3.12.14源码和固定Windows工具链构建，或经明确批准另选有官方Windows发行版的基底并重做兼容。均未在本轮实施，也不擅自降级。

“可复现”首先指同一封存输入可离线重复构建并比对组件/行为；EXE逐字节一致还受时间戳、压缩器、PE和签名影响，未测试，不作保证。

## 4. 可执行顺序与命令契约

以下为后续实施顺序；列出的新spec/install.nsi尚未实现。不能直接执行为已批准发行流水线。

1. 人工确认许可路径和本轮构建范围，写入审批记录；来源门禁/输入hash任何缺项均失败。
2. 从批准revision新建唯一staging；Git archive不改变原工作树。记录环境、源zip及配置hash。
3. 在新的build-gui与build-cuda虚拟环境离线安装，既有3个venv仅作审计对照，禁止pip升级它们。

```powershell
# 由构建负责人明确设置阶段目录及已封存Python；不能改用全局Python。
& $pythonBase -m venv (Join-Path $stage 'build-gui')
& $pythonBase -m venv (Join-Path $stage 'build-cuda')
& $guiPython -m pip install --no-index --require-hashes --find-links $guiWheelhouse -r $guiHashLock
& $cudaPython -m pip install --no-index --require-hashes --find-links $cudaWheelhouse -r $cudaHashLock
# build-tools清单是现有build闭包扣除GUI闭包的构建工具子集；正式仍需wheel hash lock。
foreach ($buildPython in @($guiPython, $cudaPython)) {
  & $buildPython -m pip install --no-index --require-hashes --find-links $buildWheelhouse -r $buildToolsHashLock
}
& $guiPython -m pip check
& $cudaPython -m pip check
# 下面spec路径为待实施/评审，不存在时必须停止。
& $guiPython -m PyInstaller --noconfirm --distpath $guiDist --workpath $guiWork $guiSpec
& $cudaPython -m PyInstaller --noconfirm --distpath $cudaDist --workpath $cudaWork $cudaSpec
```

4. 单独收集DLL及metadata/模型配置/许可证，建立最终payload BOM与每文件SHA；不是复制整个venv。Torch本机lib有53文件合计4,427,383,390字节，不能凭Lite的约100MB ZIP估算RTX安装器大小。
5. stage内先验证冻结GUI和Worker协议（空状态、新项目、GPU探测、短PT/ORT推理、只读模型hash、失败/取消）；需要的模型通过测试者已有合法文件显式选择，只留在外部隔离测试项目，不进入载荷。
6. 候选NSIS3.12 Unicode（新工具须来源/许可/大小验证）封装一个中文Setup：当前用户安装、目录选择、开始菜单、可选桌面、卸载、不要求用户Python。先测压缩总量及工具单EXE上限；若不能容纳，记录阻断并评审支持该体积的单包工具，不擅自变成多套产品或伪造单文件成功。
7. 内部候选写显著INTERNAL TEST / NOT FOR DISTRIBUTION，输出到内部唯一artifacts目录，不使用正式dist发布文件名，不向领导交付。签名和扫描结果分别记录，不关闭系统安全功能。
8. 干净Windows10/11、无Python/无Codex、只读程序目录、无GPU空状态、中文路径、重启/卸载/重装数据保留、RTX5070Ti实际短GPU测试。其他RTX没有实机则NOT TESTED。
9. 只有所有合规与技术门禁通过且用户确认授权范围后，才生成正式Setup/Release ZIP、SHA256、许可材料及测试摘要。之后恢复PACKAGING_FREEZE=TRUE；后续源码更新不自动重打包。

## 5. 测试清单与本轮状态

本轮完成3环境依赖闭包/156份原许可证副本hash核查，默认依赖无缺项；现有独立CUDA进程-I隔离测试通过，真实16元素CUDA张量通过。仅这一小探针，不训练、不加载私有模型、不把ORT Provider列表当作实际ORT GPU计算验收。

未构建内部EXE/Setup，本轮无新依赖安装；干净系统、最终payload DLL解析、freeze Support/JSON协议、打包模型加载/ORT节点、安装卸载/重装全部NOT TESTED。大体积压缩、完整输入hash锁、对应源码/通知、Python基底和公司许可路径仍是正式构建前门禁。方案不表示任意Windows/RTX支持。

本轮GUI/CUDA/build三个现有环境pip check均返回0（No broken requirements found），见证据pip-check.json；这不是新的隔离安装已复现。
