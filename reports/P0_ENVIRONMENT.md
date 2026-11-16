# P0 环境核查报告（续行）

日期：2026-10-12，Asia/Shanghai。当前只授权 P0；用户明确不批准 P1。

**现状：intel_infer 已恢复并通过真实 GPU 门禁；intel_train 仍缺 XPU 主运行库，暂停安装。** 沿用既有环境，未重建。

| 核查项 | 结果 |
|---|---|
| 项目根目录 | C:/Users/kevin/Desktop/IVAD Project/IVAD_Platform_v1.0 |
| Windows | Windows 11 家庭版 中文版，Build 26200 |
| CPU / GPU | Core Ultra X7 358H / Arc B390 |
| 驱动 | 32.0.101.9033；未改动 |
| RAM | 33,873,752,064 bytes；不等于 GPU 独占显存 |
| Python | 既有独立 CPython 3.14.7，普通 cp314 Windows x64；未更换版本 |
| intel_infer | 项目 .venvs/intel_infer；pip 26.2.1、OpenVINO 2026.4.1、NumPy 2.5.4、openvino-telemetry 2025.2.0 |
| intel_train | 项目 .venvs/intel_train；仍仅 pip 26.2.1，未安装半套训练环境 |
| 全局环境 | 默认 Miniforge、全局 Python、PATH、其他 AI 项目均未修改 |
| Git | 仍非 Git 仓库；未创建仓库 |

初查硬件/驱动/磁盘记录见 raw/environment.json、environment_extra.json。首轮沙箱路径问题属于已记录的启动限制，不据此认定 Miniforge 损坏。

## 下载阻断定位

1. 两环境前置核查确实只有 pip，原 GPU 失败是缺包导入，不是设备不兼容。只读检查 pip wheel 缓存、HTTP 缓存中的 wheel 容器及 Downloads，未找到可复用兼容 wheel；见 raw/dependency_inventory_resume.json。
2. DNS 可以解析官方域名；urllib 未发现配置代理，WinINET ProxyEnable=0、无 PAC，WinHTTP 为 Direct。保持默认 TLS 证书/主机名验证，curl ssl_verify_result=0。证据见 network_snapshot_resume.json、winhttp_proxy_resume.txt 和各 curl 日志。
3. 小响应和小 Range 可完成；PyPI wheel 大响应、较大 Range 出现低吞吐和读取/握手超时。原生 curl 官方源 1MiB 测试在15秒仅取得458,752 bytes，TUNA镜像取得736,987 bytes，两者都未完成。此前“零字节”不足以证明无传输，还受整段读取/文件缓冲影响。
4. 官方 XPU 索引提供的 download-r2.pytorch.org 路径返回403；等价 download.pytorch.org 官方 CDN 返回206，大小、索引 SHA256、METADATA SHA256均核对。该端点问题已区分于下载传输不稳定。
5. gzip 元数据传输和64KiB分段取得实际进展：三个推理 wheel 完整通过官方 hash 后离线安装；GitHub release JSON亦完整取得。XPU大文件改用已核实官方端点并降低并发后仍出现超时，按有限尝试规则暂停；未无界重试。

结论：已定位到下载传输层和一个官方 CDN 403 问题；没有观察到证书验证错误或 DNS 解析失败。记录不足以确定更深层责任在运营商、服务器或链路，不能宣称已彻底修复网络。

## 版本、来源及离线交付

固定主版本保持 PyTorch 2.14.1+xpu、torchvision 0.29.1+xpu、triton-xpu 3.8.0、Ultralytics 8.4.175、OpenVINO 2026.4.1。全部 P0 候选依赖闭包 62 项，具体包名/版本/ABI/官方 URL/hash 见 P0_DEPENDENCIES.md 和 raw/p0_full_offline_manifest.json。当前已有 44 个候选 wheel 完整通过官方 hash，下载通过不等于已安装或 GPU 通过。

实际环境锁为 raw/intel_infer_resume.lock.txt、intel_train_resume.lock.txt；候选闭包要求文件不是成功环境锁。需要人工的剩余 19 个文件及最小步骤见 P0_OFFLINE_DOWNLOAD.md。

全程未禁用 TLS、未修改系统代理/证书/驱动/全局 Python，未删除或上传用户数据；系统级操作均未执行。仅结束本轮已核对命令行的下载进程，保留未完成片段。商业生产许可仍未解决，当前只做本地 P0 测试。

## 2026-10-14 VPN直连续行

Tailscale出口节点已启用，官方下载目标实际选择Tailscale路由。仅对下载进程禁用代理/绑定WLAN以及socket接口选择均未恢复连接；最后一种方式被WinError10013拒绝。未修改系统路由、VPN、代理、TLS或驱动；依赖下载尚未恢复，没有新增GPU/模型测试PASS。
详见P0_VPN_DIRECT_20261014.md及原始日志。等待用户手动停用出口节点，或单独授权临时停用并恢复，之后先做有界直连对照，再继续P0。不进入P1。
