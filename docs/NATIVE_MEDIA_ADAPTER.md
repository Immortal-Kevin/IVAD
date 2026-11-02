# Windows 原生媒体候选接口

仅供开发验证。正式 WPF/IDS 集成未完成；打包冻结，禁止作为可分发版本。

`ApplicationServices(root, media_backend='windows-mf')` 将现有 MediaService 的 FileVideoSource 接口绑定至 WindowsVideoSource；不创建新数据库体系。省略参数仍为历史环境的 legacy 路径。不要在原用户项目上尝试时钟迁移。

解码协议 `ivad-mf-pipe-v1`：4 字节 little-endian JSON 长度、JSON metadata/frame/error/end、随后 BGRX 像素。仅 stdio 本地传输，禁止 pickle；header ≤64 KiB，pixels ≤128 MiB，队列最多 2 项。每帧必须有系统实际 sample 时间。取消/20 秒响应超时后只关闭本对象持有的进程树。

时间语义：MPEG-PS 能确定对应关系时保存 PES raw_pts + 1/90000，同时保存 MF ticks + 1/10000000；其他容器保存真实 MF presentation ticks 并标注时钟域，不把它称为容器原始 ticks。数据库继续使用既有微秒字段，额外证据放现有 parameters；旧媒体原点不一致则拒绝写入，不自动改历史帧。

片段为系统 H.264/MP4 视频，无音轨；VFR 禁用隐式帧率转换；奇数尺寸明确拒绝。MF seek 目前使用顺序解码定位，长录像性能未优化。编码器尚未进程隔离。

## 本地复现

保留当前实验目录，不要为了复现删除证据。以下创建脚本遇到已存在环境/输出会拒绝覆盖；在独立开发副本准备相同已核实源环境与本地样本后运行。无需下载工业数据，不运行 pip 升级，不做安装包。

1. 使用 `.venv-p1/Scripts/python.exe scripts/permissive/prepare_media_candidate.py` 创建 8 包媒体环境。
2. 用 `.venv-media-native-v2/Scripts/python.exe scripts/permissive/service_check.py` 执行独立项目业务服务验证。
3. 使用现有 Python 运行 `scripts/permissive/prepare_rf_candidate.py`，从 `.venv-rfdetr` 复制隔离候选。必须等复制完成。
4. 顺序运行 `scripts/permissive/apply_rf_compat.py`、`scripts/permissive/seal_rf_compat.py`。后者校验原环境及候选前后哈希；禁止与训练并行修改候选。
5. 用候选 Python 运行 `scripts/permissive/rf_compat_training.py`（1 epoch 软件夹具）或加 `--cancel`；用 `rf_inference_check.py <新的证据目录名>` 只读加载既有模型。实际 GPU 锁沿用现有机制；无 CUDA 必须失败。
6. 原 GUI 测试环境运行 `-m pytest tests/test_permissive_media.py tests/test_permissive_compat.py tests/test_p2_services.py tests/test_p37a_rfdetr.py -q`。测试使用独立项目和样本。

候选补丁固定现有依赖版本，不能直接用于新版本包。媒体包 requirements 不是整套产品依赖锁。完整版本清单及许可缺项见 `legal/NVIDIA_PERMISSIVE_DEPENDENCY_DELTA.json` 和 `legal/NVIDIA_PERMISSIVE_REMEDIATION.md`。
