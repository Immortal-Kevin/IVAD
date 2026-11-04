# P0 分发阻断整改：技术部分完成，分发继续阻断

`PACKAGING_FREEZE=TRUE`；`DISTRIBUTION_STATUS=BLOCKED`。没有安装包、发行 ZIP、Push 或工业模型重训。仅开发 EXE、第三方依赖 wheel 和隔离测试工件。

## 基线与变更

实际初始 HEAD：`5182e6ab0bb478780935d8951e0ffe28bd6427c6`。回滚分支 `rollback/pre-distribution-p0-20261104`；实施分支 `feature/nvidia-distribution-p0-20261104`。开始时已有的 `reports/P37_QT_NATIVE_ISSUE.md` 修改、`demo_rf/` 和 P37/RF_DEMO 未跟踪报告原样保留，不纳入本次提交。

沿用 WPF / Media Foundation / Intel IDS / RF-DETR Nano，没有重做 H1–H5。新增：

- Windows SID 与 NTFS ACL 检查，显式初始化全新空工作区；检查工作区、策略文件、项目、SQLite/WAL/SHM、任务目录/catalog 和主要资源目录；推理及模型验证检查实际权重 ACL。独立证据目录及四份数据库备份亦已限制 ACL。
- 匿名 stdin/stdout 管道继续使用继承随机 token 和协议校验，无监听 TCP 端口。错误 token 实测拒绝。
- 所有者 SID 对应 administrator / reviewer / viewer 角色；不再凭“本地管理员”显示名称授予权限。默认关闭 IDS/基线导出，启用后仅允许工作区 exports 子目录，并检查目录边界/ACL。
- Python 日志、C# 诊断日志及 RF 子进程控制台日志脱敏。训练管道持续读取并在写盘前脱敏；推理输出也在写盘前处理。
- RF 解释器选择保存在现有设置中，不再每次打开覆盖；启动器支持显式 `--rf-worker-python` / `-RFWorkerPython`。
- 无 IDS 投影的旧 NVIDIA 项目给出明确受控拒绝，避免误当空 IDS 项目。没有擅自转写原库。

保护边界是单 Windows 所有者工作区及其他账户访问控制；不是多用户身份服务器、加密存储，也不抵御拥有该账户权限的任意代码。初始化仅用于空目录；没有对原始工业数据库执行 ACL 修改或迁移。

## NumPy / SciPy 实际构建与替换

安装免费 MSVC Build Tools 17.14.44（工具目录 14.44.35207 / cl 19.44.35229、SDK 10.0.26100.0）、Meson 1.12.1、Ninja 1.13.2、meson-python 0.21.1、Cython（NumPy 3.3.1 / SciPy 3.2.9）、pybind11 3.0.4、oneMKL 2026.2.0。工具和源码在本轮私有构建目录，不改全局 Python/驱动，不购买许可证。[Microsoft 关于免费编译开源依赖的说明](https://devblogs.microsoft.com/cppblog/updates-to-visual-studio-build-tools-license-for-c-and-cpp-open-source-projects/)。

官方 PyPI sdist 下载 SHA256 已匹配 API。源码和 LICENSE/METADATA 未改。源码、工具链、构建参数、wheel SHA 见 `legal/licenses/p0-numeric-20261104/BUILD_SOURCES.json`。

|组件|真实结果|
|---|---|
|NumPy 2.5.4|MSVC 从源码构建成功；`blas=none, lapack=none, allow-noblas=true`。wheel SHA256 `d9938375203b4240f74123462a74fe453bc4781041c18911a7047b3ee770aabf`。|
|SciPy 1.18.1|MSVC + oneMKL LP64 sequential 从源码构建成功；`_without-fortran=true, use-pythran=false`。wheel SHA256 `c729f4b9b1ba41901bc05f1d4701bc8cea529f59030292dacc4b848d41018f82`。|
|构建故障处理|先解决 MSVC 缺失和 BLAS 缺失；再定位 f2py 对含空格路径的错误拆分。用临时 R: 构建映射解决，映射已撤销。构建期 NumPy 固定 2.2.6，运行期为自编译 2.5.4。保留每次失败日志。|
|实际原生调用|数值运算实际加载 `mkl_sequential.3.dll`、`mkl_core.3.dll`、`mkl_avx2.3.dll`、`mkl_vml_avx2.3.dll`。候选观测/PE 闭包无 OpenBLAS、libgfortran、libgcc 文件；这不等价于全部静态第三方许可已审定。|
|替换范围|已安装到隔离 `rf-noblas` 候选，通过 `.pth` 复用原 RF 包及本机 oneMKL 库。原 RF 环境未替换；默认运行环境未强制切换。该候选不是可搬运的独立发行载荷。|
|功能限制|SciPy 官方实验性无 Fortran 路线不安装 `scipy.odr`。RF 路线已验证，不能称完整 SciPy API 等价替换。|

NumPy 单独替换、NumPy+SciPy 组合替换后均运行了 CUDA 1 epoch 合成夹具短训、指标计算和 Checkpoint 重载；分别重跑两份历史 RF 模型推理。两份历史权重 SHA 保持 `bc9d31e4…1c52c6` / `639f7f99…a9c7ad`，此单帧预测均为空，不将其描述为工业准确率验收。

最终相同冻结数据、相同 Checkpoint 的原环境/候选对照：precision/recall/mAP50/mAP50:95 差值全部 0，预测轨迹 SHA 一致。另对 solve、SVD、Hungarian assignment、Gaussian filter、distance 比较，最大绝对误差 `8.53e-14`（门限 `1e-10`）。这些结论限定于本轮测试数据。

## 必要原生依赖证据与分发结论

`legal/P0_NATIVE_EVIDENCE_20261104.json` 以原 `runtime-closure.json` SHA 为基线，合并 RF 推理、实际数值运算、WPF 及存活 bridge 进程模块，递归解析 PE 普通/延迟导入。记录 304 个原生文件（173 个非 Windows 系统文件）、21 个所属包，包含路径占位符、版本资源/包版本、SHA256、RECORD 校验、依赖解析、来源和许可/NOTICE 指针。没有扫描隔离旧 Qt/YOLO/FFmpeg 环境。

所有有 RECORD SHA 的文件本地校验匹配。非系统文件的直接/延迟依赖没有未解析项；保留 10 个 Windows 系统组件内部、未加载的延迟依赖为 UNRESOLVED，不擅自复制它们。动态未覆盖分支和静态嵌入库仍需额外证据；清单不是所有功能的完备证明。

|重点组件|证据与仍需满足的事项|
|---|---|
|PyTorch 2.9.1+cu128 / Torchvision 0.24.1+cu128|实际 DLL SHA、安装 RECORD、包通知及来源入口已记录；上游 wheel 与每个 vendor DLL 的加密来源绑定、静态库对应通知仍未闭合。顶层 BSD 不覆盖全部 vendor DLL。|
|CUDA 12.8 / cuDNN 9.10.2.21|精确版本条款、现有原文及 DLL 证据保留；仍需逐文件与再分发清单绑定，并落实应用条款/通知。[CUDA 12.8.1 EULA](https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html)、[cuDNN 9.10.2 EULA](https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html)。|
|NumPy / SciPy / oneMKL|自编译源码与产物链已形成，新增源码 BSD/捆绑许可证清单和安装包原始 ISSL。oneMKL 按随包 ISSL 有条件再分发，仍需完成对应第三方材料及最终载荷 NOTICE 组合。[Intel 官方许可 FAQ](https://www.intel.com/content/www/us/en/developer/articles/tool/onemkl-license-faq.html)。|
|Pillow RF 12.3.0 / 媒体 11.2.1|本机原生哈希及先前图像库通知保留；两个 wheel 的准确构建来源及静态图像库对应关系仍待闭合。|
|Windows/.NET/WPF/MF、MSVC、Python|系统模块是前置条件，不随本轮输出复制；Python 基础运行时与 Microsoft 可再分发库仍需确定正式供应渠道/EULA/REDIST。不能用 WPF 源码许可替代 Windows 二进制条款。[Microsoft 部署指南](https://learn.microsoft.com/en-us/dotnet/framework/deployment/deployment-guide-for-developers)。|
|RF-DETR Nano 和骨干|沿用固定 Nano 预训练资产 SHA `d8d6b9ee…57440d`、官方下载来源、Apache-2.0 及 DINOv2/LW-DETR/Deformable DETR 原文；不使用 plus/PML。私有微调数据和权重权利独立处理。|

GNU GCC Runtime Library Exception 允许符合条件的专有模块组合，不自动要求公开 IVAD 数据库；排除 GPL/LGPL/MPL 是用户更严格的工程政策，二者不可混淆。[GCC exception 原文](https://www.gnu.org/licenses/gcc-exception-3.1.en.html)。本轮没有删除许可证、改 METADATA、重命名 DLL 或以进程隔离规避许可。

## 独立回归结果

证据根：`E:\IVAD Project\P0_Private_20261104`；历史推理原始证据在项目忽略的 `artifacts/permissive-20261102/p0-*-history/`。仅记录本轮真实结果：

|测试|状态|证据/限制|
|---|---|---|
|SID/ACL/角色/导出/IPC/日志|PASS|`security-catalog-final.log` 10/10；C# 独立编译日志脱敏探针 PASS。|
|真实 IDS 全量/增量/重复/损坏/冲突/事务回滚|PASS|`ids-final/summary.json` 14/14；源资料只读，输出隔离。|
|原 Intel 核心回归|PASS|`wpf-build-tests.log` 73/73；该套核心测试不等于 NVIDIA bridge GUI 验收。|
|Python 服务/数据库/兼容层|PASS|`pytest-services-isolated.log` 29/29。|
|Media Foundation 独立进程测试|PASS|`pytest-media-isolated.log` 15/15。|
|先前混合进程 pytest|FAIL|40 PASS / 6 FAIL 原日志保留：4 个 COM apartment 冲突在独立媒体进程复验通过；2 个旧缓存夹具使用已禁用的历史模型路线，未修改策略或伪造通过。|
|数值替换后的 CUDA、评估、重载、历史推理|PASS|`cuda-noblas`、`cuda-numpy-scipy`、`numeric-parity`；日志脱敏代码改后 `cuda-final-logged` 再跑成功，最终 catalog ACL 及持久解释器配置由 `final-service-smoke.json` CUDA 推理验证。|
|925 帧实际选择与批量正常|PASS（限定输入方式）|从 0 选择开始，真实鼠标点击 875 秒帧 + Shift+End，真实鼠标批量按钮；922 成功/3 受保护跳过/0 失败，已确认 1129/1800。`native925-*.png`、`native925-db.json`；新进程重开仍为 1129/1800，保留 ROI 和两帧异常。不是预置 925，也不是纯鼠标 Shift 拖选。|
|WPF 训练真实按钮|PASS（已操作按钮）|GPU 状态、开始训练、任务状态、模型 UUID 输入和单帧推理；任务 `0e06addc…fdf4` SUCCEEDED，推理 CUDA_FORWARD=true / weights_unchanged=true。验证/取消按钮未逐项验收。|
|标注画布真实操作|PASS（缩放/适应）|真实鼠标放大与适应窗口，`native-canvas-fit.png`；完整绘图/拖动保存未做本轮 native 验收。|
|高 DPI 多档与纯鼠标跨屏拖选|NOT TESTED|没有把数学坐标测试或当前窗口操作冒充 125/150/200% 多档真实验收。|
|原始数据保护|PASS|`final-checks.json`：89 个选取数据库/权重 SHA 无变化；4 份 SQLite 一致备份保留。不是本轮全媒体全盘扫描。|
|历史 NVIDIA 存储层副本读写/失败回滚|PASS|副本经现有 ProjectStore 打开、提交、故障回滚、integrity_check；原库不变。|
|无 IDS 投影旧 NVIDIA 项目完整 WPF 兼容|FAIL|明确拒绝 `LEGACY_PROJECT_REQUIRES_VALIDATED_IDS_COPY`；尚无受验转换，不自动改写旧库。已导入 IDS 项目可重开。|
|OS 级隔离断网下 IDS/训练/推理|NOT TESTED|创建隔离防火墙规则被 Windows 拒绝 Access Denied；未停用用户网络、未留下规则。应用层离线 Worker 通过，不能替代 OS 断网。|

## 仍然阻断分发与使用方式

许可闭包、最终第三方通知与准确来源未审定；候选依赖本机外部 RF/MKL 路径、SciPy ODR 缺失；OS 断网、完整高 DPI/native GUI 和旧项目 WPF 兼容尚有缺项。以上技术 PASS 均不产生商业分发许可 PASS。

新测试工作区可用 `scripts/start_wpf.ps1 -Workspace <全新空目录> -InitializeWorkspace` 初始化；已有安全工作区不加该开关。仅显式选择受测候选时加 `-RFWorkerPython "E:\IVAD Project\P0_Private_20261104\rf-noblas\Scripts\python.exe"`。需要保留基线解释器与候选引用的 oneMKL 目录。默认导出禁止，不能通过改显示名称解除。

源码回滚使用本次提交的 `git revert <commit>`，或在无冲突工作区切换 `rollback/pre-distribution-p0-20261104`。不使用 `reset --hard` / `clean`。数值候选在隔离目录，移除启动参数/将工作区解释器设置恢复至 `.venv-rf-media-candidate/Scripts/python.exe` 即回到原环境；不删除工业数据或历史权重。
