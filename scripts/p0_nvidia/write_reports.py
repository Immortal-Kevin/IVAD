"""仅根据本地真实JSON证据生成P0报告。"""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
OUT, REPORT = ROOT / 'artifacts/p0', ROOT / 'reports'
probe = json.loads((OUT / 'cuda-probe.json').read_text())
yolo = json.loads((OUT / 'yolo-results.json').read_text())
bench = json.loads((OUT / 'benchmark-supplement.json').read_text())
models = bench['models']
passed = probe['status'] == 'PASS' and all(yolo[n]['train_status'] == yolo[n]['ort_status'] == models[n]['status'] == 'PASS' for n in models)
status = 'PASS' if passed else 'FAIL'
candidate = min(models, key=lambda n: models[n]['ort_forward']['p95_ms']) if passed else '未选择'
def write(name, text): (REPORT / name).write_text(text, encoding='utf-8')
shared = '''环境：Windows 11 专业工作站版26200；Core Ultra 7 265K；33577684992 bytes RAM；RTX5070 Ti，驱动617.42；nvidia-smi显存16303MiB，PyTorch可用设备属性16275MiB。
Python3.12.14；torch2.9.1+cu128；torchvision0.24.1+cu128；CUDA runtime12.8；cuDNN91002（9.10.2）；ultralytics8.4.176；onnx1.20.1；onnxruntime-gpu1.24.4。
完整固定版本见 artifacts/p0/requirements-lock.txt；实际PyPI来源与hash见install-yolo-ort.json，torch下载和安装见download-hashes.json、install-local-torch.log。
'''
write('P0_NVIDIA_ENVIRONMENT.md', '# P0-NVIDIA 环境审计（重试后）\n\n日期：2026-10-13，Asia/Shanghai。\n\n' + shared + '''
## 真实环境与隔离

项目：`[采集会话路径]`，目前是设计/探针目录，非Git仓库，无开发分支可核实。
专属解释器：`.venv-nvidia/Scripts/python.exe`，include-system-site-packages=false。
基础解释器：`[采集会话路径]`；仅读取基础运行时，没有在其中安装依赖。
py launcher没有注册Python；PATH未发现nvcc，标准Toolkit目录未发现。wheel自带CUDA/cuDNN运行时，不需系统级安装。
Intel Graphics驱动32.0.101.8736可枚举；未发现B390；未执行Intel AI测试。
E盘初始可用617059172352 bytes。

## 网络恢复结果：PASS

原pip重试访问download-r2.pytorch.org发生读取超时。用户授权VPN/直连重试后，curl对download.pytorch.org使用单进程 --noproxy '*' 直连成功，2.862GB官方torch wheel完整下载并校验官方SHA256；torchvision同样校验通过。
GitHub官方权重使用现有http://127.0.0.1:7897代理下载成功。未修改系统VPN节点、代理、注册表或全局环境变量，TLS校验保持启用。
PyPI其余依赖安装成功，pip check无冲突。当前欠缺必需安装包：无。
wheelhouse保留torch/torchvision，其他包安装来源已记录；不是完整离线安装包。
TXT下载/恢复指引：reports/P0_NVIDIA_DOWNLOAD_GUIDE.txt。

## 已有环境与安全边界

仅只读检查C/D/E顶层、用户目录、Local Programs、标准Toolkit目录及旧Stable Diffusion目录一级子目录；未完整定位现用ComfyUI/YOLO/Conda路径，不能断言不存在。
发现D:\\OLD PC Stable Diffusion & GHGZH\\BaiduNetdisk，仅读目录，未修改。
不改驱动、系统CUDA、全局Python、PATH、代理、其他AI项目；所有依赖装入项目venv，模型/数据/日志写在项目内。pip可能产生系统临时文件/下载缓存，不清理原缓存。
安全PASS基于操作范围；并非未知原环境的全盘前后哈希证明。测试期间桌面程序共享GPU，因此整卡显存采样包含其他进程。
原始硬件、源文档hash、下载和测试证据均位于artifacts/p0。原失败报告保留reports/history/2026-10-13-first-attempt。
''')
rows = ['| 模型 | PT推理 | 导出/ORT CUDA节点 | 原始输出对齐 | CUDA短训/权重更新/重载 |', '|---|---|---|---|---|']
for n in models:
    r = yolo[n]
    rows.append(f"| {n} | {r['torch_status']} | {r['ort_status']} | {r['ort_status']}，max abs={r['max_abs_error']:.6f} | {r['train_status']}，{r['train_evidence']['optimizer_steps']}次更新 |")
write('P0_NVIDIA_GPU_COMPATIBILITY.md', '# P0-NVIDIA GPU兼容性\n\n总体：' + status + '\n\n' + shared + '\n' + '\n'.join(rows) + f'''

基础CUDA：{probe['status']}。真实CUDA张量矩阵计算、Linear前向、loss.backward、SGD.step、参数变化、保存/weights_only重载一致；allocator峰值{probe['peak_allocated_bytes']} bytes。
OOM：PASS，请求远超设备容量的单块分配被分配器拒绝，捕获torch.OutOfMemoryError后继续前向成功；未故意占满实际显存，不等于穷尽所有OOM恢复场景。

## 排除CPU fallback

全部神经网络前向通过全局module pre-hook检查参数和输入张量CUDA；模型构造stride探测在CudaInitTrainer的CUDA上下文中执行。训练梯度hook断言CUDA，显式device=0，记录8次optimizer_step和第一层参数变化。
ORT session.disable_cpu_ep_fallback=1，disable_fallback()；GPU输入输出IOBinding，连续NCHW内存；profiling实际节点provider集合仅CUDAExecutionProvider。不能以session.get_providers替代这个证据。
导出device=0；当前ORT CUDA与PyTorch完整FP32都禁用TF32。CPU执行解码、预处理、规则/NMS后处理、保存和日志允许。

## 首轮失败与修复（日志保留）

1. GPU输入由permute产生非连续内存，IOBinding只接受形状和指针，误按连续NCHW读取；显式contiguous后修复。
2. ORT默认TF32与PyTorchFP32设置不一致，关闭ORT use_tf32及PyTorch TF32后对齐通过；没有放宽既定allclose阈值。
3. 极小数据/短训的默认warmup设置不足以证明第一层参数变化；使用相同SGD、nbs=2、warmup_epochs=0，两模型真实8次更新并重载通过。
4. pip inspect初次输出遇GBK UnicodeEncodeError，使用仅该子进程PYTHONIOENCODING=utf-8后记录成功；不是GPU错误。
5.第一次长时间测试输出90秒faulthandler定时栈，属诊断定时器，测试正常结束；脚本现已取消补充benchmark的该定时器。

证据：cuda-probe.json、yolo-results.json、yolo-test-fp32-console.log、*ort-profile*.json、benchmark-supplement.json；失败日志yolo-test-console.log、yolo-test-retry-console.log与对应备份JSON。
Intel XPU/OpenVINO、其他RTX、TensorRT：NOT TESTED。
''')
table = ['| 模型 | 后端 | p50 ms | p95 ms | mean FPS |', '|---|---|---:|---:|---:|']
stages = ['| 模型 | 解码p50/p95 ms | 预处理含H2D p50/p95 ms | PT后处理p50/p95 ms | ORT D2H+后处理p50/p95 ms |', '|---|---:|---:|---:|---:|']
extra = []
for n, r in models.items():
    for key, label in [('torch_forward', 'PyTorch CUDA'), ('ort_forward', 'ORT CUDA')]:
        t = r[key]; table.append(f"| {n} | {label} | {t['p50_ms']:.3f} | {t['p95_ms']:.3f} | {t['fps_mean']:.2f} |")
    cells = [f"{r[k]['p50_ms']:.3f}/{r[k]['p95_ms']:.3f}" for k in ['decode', 'preprocess_h2d', 'torch_postprocess', 'ort_d2h_postprocess']]
    stages.append('| ' + n + ' | ' + ' | '.join(cells) + ' |')
    s, t = r['stability'], yolo[n]
    extra.append(f"- {n}：对齐公开bus图像检测{len(r['ort_detections'])}个；原始输出max abs={r['raw_max_abs_error']:.6f}；连续{s['duration_seconds']:.3f}s、{s['iterations']}次，finite/unchanged均True。PyTorch allocator峰值{r['torch_allocator_peak_bytes']/2**20:.2f}MiB；整卡采样峰值{r['total_gpu_peak_mib_sampled']}MiB。短训{t['train_seconds']:.3f}s（包含验证/保存，非每步速度）。\n  官方权重SHA256：`{t['sha256']}`；重载检查点SHA256：`{t['checkpoint_sha256']}`。")
write('P0_NVIDIA_BENCHMARK.md', '# P0-NVIDIA 基准报告\n\n状态：' + status + '\n\n' + shared + '''
同一Ultralytics包内bus.jpg，640x640 resize（非letterbox），RGB、FP32、batch1、预热10、重复50；所有GPU计时前后CUDA synchronize。两模型此部署比较采用raw one-to-many输出及统一NMS（conf0.25/iou0.7），不是YOLO26原生端到端模式性能认证。
主表ORT关闭profiling，use_tf32=0、cudnn_conv_algo_search=HEURISTIC；节点CUDA证据由同一工件的独立profile测试提供。
FPS=1000/平均前向毫秒，只是推理内核吞吐，不是视频端到端FPS。p95仅50样本，不代表生产SLA。

''' + '\n'.join(table) + '\n\n' + '\n'.join(stages) + '\n\n' + '\n'.join(extra) + f'''

原始张量allclose rtol=1e-3/atol=1e-3；最终检测allclose rtol=1e-3/atol=0.05且必须非空，实际框/置信度/class均保留JSON。
PyTorch allocator峰值为当前进程测量区间，包含已有活跃CUDA张量；整卡峰值每约0.2s nvidia-smi采样，包含同时驻留的PT/ORT和桌面程序，不是ORT独占分配峰值，可能漏掉瞬时峰值；未测训练allocator独占峰值。
短训：相同本地合成矩形8train/4val、2epochs、batch2、imgsz640、SGD lr0=0.01、nbs2、warmup0、AMP关闭、seed123、workers0。合成样本仅验流程；不报告其mAP作为煤厂准确率。
60秒稳定性仅短时冒烟，不代替长时生产负载或全部GPU算子认证。

NVIDIA默认候选：**{candidate}，ORT CUDA、640、FP32、raw+NMS**，依据本次ORT p95最低且核心兼容性全部通过；训练耗时也保留，不能据此断言通用精度或训练性能更好。
选择仅对5070 Ti本次版本/输入/后端有效；YOLO11n仍保留为已测候选。Intel需要单独实测并独立选型。
原始50次计时、实际检测、稳定性和显存采样：artifacts/p0/benchmark-supplement.json；训练CSV与权重：artifacts/p0/runs/*-3；失败运行目录原样保留。
''')
write('P0_NVIDIA_ACCEPTANCE.md', f'''# P0-NVIDIA验收报告（重试后）

日期：2026-10-13（Asia/Shanghai）。工程P0总体：**{status}**。没有进入P1。

完成五份文档一致性与接口审计、硬件核实、独立运行环境、CUDA基础计算/前反向/权重更新/保存重载/OOM处理、YOLO26n和YOLO11n的CUDA推理/ONNX导出/ORT CUDA真实节点执行/短训/检查点重载、输出与最终检测一致性、分段计时/显存采样/60秒稳定性。

{shared}

| 验收项 | 状态与真实证据 |
|---|---|
| 文档一致性/未来接口审计 | PASS，docs/DECISIONS.md；只做文档建议 |
| 隔离环境与依赖 | PASS，项目venv、固定锁文件、官方来源/hash、pip check |
| CUDA基础真实计算与训练 | PASS，cuda-probe.json |
| OOM拒绝与继续计算 | PASS，受控超大单块请求，未占满显存 |
| 两模型CUDA PT推理与导出 | PASS，yolo-results.json与console |
| ORT CUDA执行且无CPU节点fallback | PASS，严格会话配置+profile实际provider |
| 两模型短训/更新/权重重载 | PASS，各8次更新与CUDA梯度/参数证据 |
| 原始输出与非空最终检测对齐 | PASS，benchmark-supplement.json |
| p50/p95/FPS、采样显存、短时稳定性 | PASS，方法和范围见基准报告 |
| 环境安全操作范围 | PASS，未改驱动/系统配置/现有AI环境；非全盘哈希证明 |
| Intel/其他RTX/TensorRT/工业准确率/长时生产稳定性 | NOT TESTED |

NVIDIA初选默认候选：**{candidate}（ORT CUDA，640，FP32，raw输出+NMS）**，依据实测ORT p95和兼容性。不是生产模型发布，也不代表Intel验证通过。

未解决问题与限制：
- 无厂区真实样本，工业故障精度、漏报/误报和生产阈值未知。
- Ultralytics AGPL-3.0/Enterprise商用许可尚未解决，禁止宣称商业生产许可通过。
- Intel独立P0历史BLOCKED保留，本目录没有原历史报告，未复制/覆盖/虚构；后续恢复需授权。
- 仅此RTX5070 Ti认证范围；没有TensorRT、原生YOLO26端到端模式和长期稳定性验证。
- 显存峰值是PyTorch allocator和整卡采样，ORT独占瞬时/训练独占峰值未测；详细方法限制已报告。
- 未完整定位已有ComfyUI/YOLO路径；无全盘原环境一致性证明，操作未修改这些环境。
- 目录非Git仓库；未提交Git commit，也未假称已建立Git开发分支。venv依赖Codex基础Python路径；不是安装包。

网络阻断已解除：torch/torchvision直连官方源，模型通过现有代理获取，TLS校验未关闭。当前欠缺安装包：无；仍提供TXT官方来源、可信同源CDN和放置指引。
保留初次BLOCKED报告reports/history/2026-10-13-first-attempt及首轮/TF32失败日志；故障修复不覆盖历史证据。
复现见scripts/p0_nvidia/README.md。P0结束并停止；任何P1工作仍必须用户明确批准。
''')
(ROOT / 'docs/PROGRESS.md').write_text(f'# 进展\n\n2026-10-13：P0-NVIDIA重试完成，工程验收{status}。独立CUDA环境、双YOLO推理/ORT/短训及输出对齐通过。默认NVIDIA候选{candidate}。\n原网络BLOCKED和失败日志保留。未进入P1。Intel独立历史BLOCKED不变。\n', encoding='utf-8')
(ROOT / 'docs/CURRENT_TASK.md').write_text(f'# 当前任务\n\nP0-NVIDIA完成，工程验收{status}；查看reports/P0_NVIDIA_ACCEPTANCE.md和基准报告。\n等待用户决定，未经明确批准不得进入P1。Intel恢复同样需授权。\n生产许可、工业精度、长时稳定性和跨GPU兼容性未完成。\n', encoding='utf-8')
print(status, candidate)
