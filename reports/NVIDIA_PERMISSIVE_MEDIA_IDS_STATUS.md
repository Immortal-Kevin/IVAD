# NVIDIA 媒体替代、许可整改与 IDS 接入阶段记录

日期：2026-11-02。结论 **PARTIAL**。`PACKAGING_FREEZE=TRUE`，`DISTRIBUTION_STATUS=BLOCKED`。

本次有实际代码修改和运行验证，但未完成全产品迁移。用户确认 Intel Annotator 最新源码与真实 IDS 完整/增量包不在本机；没有自创 IDS 格式或把测试夹具冒充 Intel 数据。

## 交付范围与状态

|工作包|结果|实际边界|
|---|---|---|
|原始资产保护|PASS|2328 个文件哈希、全部项目表记录、原有未提交文件前后相同|
|Windows 原生解码|PASS（已测样本）|核心伪 MP4 实为 MPEG-PS/H.264；完整解码 1751 帧，逐帧核对 PES PTS|
|业务服务接入|PASS（独立项目）|原服务可注入 WindowsVideoSource；导入、抽帧、重复提交、片段保存、片段再抽帧与一致性检查通过|
|正式媒体替换|PARTIAL|新适配器可用，旧 Qt GUI 默认仍走 legacy；不能宣称整个产品已去除 FFmpeg|
|Intel H1–H5 / WPF 页面|BLOCKED|缺少实际源码，未实施或声称 GUI 对齐，未生成虚假截图|
|IDS 完整、增量兼容|NOT VERIFIED|缺少 schema、导出器和真实包；未实现猜测性导入器|
|RF 候选 CUDA 路径|PASS（技术测试）|独立夹具短训、取消、保存、重载、评估及两份工业历史权重只读推理|
|IDS→CUDA 全流程|NOT VERIFIED|软件夹具不能替代真实 IDS 验收|
|严格无 copyleft 载荷|PARTIAL / BLOCKED|候选移除了部分依赖；Qt GUI、RF NumPy/SciPy 原生运行库等尚未完成替换|

## 实际代码

- `video/windows_mf.py`：直接调用 Windows MF COM API；按文件头识别容器，读取真实 sample 时间、编码、分辨率和显示裁切区域。
- `video/ps_timestamps.py`：自有 MPEG PES 解析，保留 90 kHz 原始 PTS；只接受与系统输出明确对应的时钟关系。
- `video/isolated_mf.py`：版本化、本机管道子进程协议；限制消息/队列大小；取消、超时仅终止自有 Worker 进程树。
- `video/windows_sink.py`：系统 H.264 MP4 编码；关闭视频处理器自动帧率转换，保留 VFR 时间间隔。
- `video/windows_source.py` 与 `services/media_service.py`：复用现有业务服务及事务，不建第二套数据库；记录时间证据。原有 dHash 行为保持逐 bit 一致，未新增 pHash/SSIM。
- `core/application.py`：显式 `media_backend='windows-mf'` 入口；历史默认行为保留以便回滚。
- `compat/progress`、`compat/windows_trust.py`：自有有限进度 API 和 Windows 信任根适配。没有修改上游许可证或将上游实现改称 MIT。
- `compute/offline_policy.py`：Worker 关闭遥测/在线下载，移除子进程云令牌，并拒绝 Python socket 传输；不是对原生扩展的完整操作系统防火墙。
- `scripts/permissive/`：隔离环境、可核查导入补丁、保护基线和真实测试脚本；`tests/test_permissive_*` 为针对性回归。

## 实测结果

全部本地原始证据位于 `artifacts/permissive-20261102/`，不进入 Git。

1. `matrix/summary.json`：8 个真实已有样本全部解码通过：核心 PS、标准 MP4、AVI、MOV、MKV、VFR、H.265、中文路径。H.265 使用本机已装 Microsoft HEVC 扩展，不代表其他电脑自带该能力。
2. 核心录像 SHA256：`8571e8b37fee5456c39d25523a90eb95b686fa69dbbd9c95cab196ad14c856a9`。原始 PES 首 PTS `4701769000`、time_base `1/90000`，1751 帧；MF 相对时间 0–70 秒，步长 40 ms。证据 `core-pes-mapping.json`。
3. `service-62ef2490/`、`media-v2-final.log`：仅 8 个 Python 包的媒体服务环境，禁止导入 Qt、av、cv2、NumPy、Ultralytics；抽取 10 帧，重复提交返回同一批 UUID；保存 2 秒/50 帧片段，再抽 10 帧；一致性 PASS。
4. `final-tests-v2.log`：**51 passed，31.08 秒**。包含取消/超时、重新打开、时间异常拒绝、VFR、29.97 FPS、业务服务及既有 P3.7-A 针对性回归。非整数 FPS MP4 roundtrip 最大误差 0.4 μs，按现有微秒存储精度验收；原始时钟未替换成帧序号/FPS。
5. `rf-fixture-4f2e9b57/result.json`：RF-DETR 1.11.2 / Nano，RTX 5070 Ti，1 epoch，5 次真实 CUDA optimizer steps；梯度、权重更新和重载证据通过，总耗时 55.891 秒。同权重、同验证集、同协议两次评估指标差值 0，逐帧预测哈希相同。4 train/2 val 独立生成软件夹具，含正常负样本；不是工业精度或 IDS 成绩。
6. `rf-fixture-9ecbc164/result.json`：实际训练 batch 边界取消，保存 cancelled.ckpt；测试脚本断言 GPU 锁可重新获得。没有登记成功工业模型。
7. `offline-worker-evaluation/result.json`：新离线限制下实际 CUDA 验证与重载 PASS；未再次训练。
8. `rf-inference-compat/result.json`：两份历史权重在移除 tqdm/certifi 后实际 CUDA forward；首模型冷启动 17.981 秒、后模型暖推理 0.0442 秒，峰值 PyTorch allocated 约 159 MiB（不是进程总显存，也不是视频吞吐承诺）。首帧阈值 0.5 均为空检测，结果原样保留。

历史权重 SHA256 前后相同：

|模型|SHA256|
|---|---|
|0d48a0e4 / 1 epoch|bc9d31e4457fe18c3306d3f567ff1fc6b0885a4bd3c233c867dcf865da1c52c6|
|50de2cc6 / 20 epoch|639f7f99903cd86c3ce44bd9ee48e238b35e94c185eba925d3032c72d9a9c7ad|

## 限制与失败证据

- 初版 VFR 编码被系统转成 CFR，已通过关闭 MF_XVP_DISABLE_FRC 对应转换修复并回归；旧失败日志保留。
- 首次兼容层修改与测试启动发生重叠，`rf-fixture-10ac4e0c` 明确作废。之后恢复候选文件并重建补丁，47/47 修改前哈希匹配原环境、修改后哈希匹配清单；只将封存后的结果计入验收。
- 缺失/倒退时间戳以注入测试覆盖，尚无对应损坏真实录像；旋转录像未实测。其他容器保留 MF presentation clock 并明确 clock_domain，不冒称原容器 tick。
- 新媒体解码进程隔离；片段编码仍在服务调用进程内，尚未完成编码器崩溃隔离。当前音轨不复制；奇数分辨率拒绝而不静默裁切。
- 新读取器目前从头解码到定位点，不保证长录像实时 seek 性能。完整 WPF 播放/标注 UI、旧缓存隔离接入和现场 UI 验收尚未完成。
- 许可补丁仅针对固定版本候选环境，不能在升级后盲目复用。未重新认证整个历史包仓库；最终运行载荷尚未形成。

## 保护、Git 与后续条件

基线 `1204369ff65d9c7f969406916108fbfe366475bb`；工作分支 `feature/nvidia-permissive-media-ids`；回滚点 `rollback/pre-permissive-20261102`。保留 nvidia-first 与所有历史分支。原有 Qt 问题报告、demo_rf、P3.7 规划及既有报告未混入本次提交。

`before.json` / `after-final.json` 比较 PASS：251 frames、217 annotations、721 revisions、200 dataset_samples、5 model_versions、5 training_runs 及其他表完整相同；2328 个受保护文件和原有脏文件哈希相同。原数据库只读检查并单独 SQLite backup，未运行迁移。所有新数据位于独立测试项目。

安全回滚使用基线分支的独立 checkout/worktree 与原开发环境；不要对当前含未提交文件的目录执行 reset --hard。未删除旧环境或历史权重，未上传数据，未 push，未制作分发包。

继续工作需要 Intel 最新 H1–H5 源码及真实 IDS 完整/增量包到本机，随后才能按实际契约迁移。独立剩余工作为 RF 数值库的宽松许可原生构建替代与二进制验证；这项本轮尚未完成，详见 `legal/NVIDIA_PERMISSIVE_REMEDIATION.md`。不能因此把当前分支称为已完成的正式闭源部署版本。
