"""Generate auditable inventories from saved evidence, never grant missing approvals."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];G=ROOT/'governance';E=G/'evidence';R=E/'rfdetr'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
deleted=json.loads((E/'legacy_deletion_manifest.json').read_text(encoding='utf-8'))
extra=json.loads((E/'incompatible_legacy_deletion_manifest.json').read_text(encoding='utf-8'))
(G/'LEGACY_CLEANUP_REPORT.md').write_text('''# v1.1 旧路线清理报告

依据：2026-10-26用户明确授权退休Ultralytics，移除其代码、依赖、权重和专用实验资产。项目根仍为IVAD_Platform_v1.0以保持路径稳定，产品基线已变为v1.1。

## 删除前证据

- evidence/legacy_deletion_manifest.json：%d个文件，%d bytes，逐文件原路径/SHA256/用途。
- evidence/incompatible_legacy_deletion_manifest.json：追加%d个文件的原路径/大小/hash。
- evidence/legacy_installed_before.json：原安装包身份；uninstall_*.log/remove_*.log：实际卸载结果。
- evidence/legacy_manifest_changes.json：移除旧依赖条目的清单原hash。

## 已执行

卸载ultralytics 8.4.175、ultralytics-platform 0.1.83、ultralytics-thop 2.2.2；移除官方/实验YOLO权重、IR、模型特有脚本、训练输出、合成数据、bus样例、专用原始日志、配置/字体缓存及对应wheel。保留一份旧进度摘要解释历史，旧链接中已删除文件不再可复现，不伪造原日志。

追加移除两环境NumPy 2.5.4及wheel：实际Windows wheel的numpy.libs/libscipy_openblas*.dll许可证声明包含GPL-3.0-or-later WITH GCC-exception-3.1，B.1未批准此例外。移除退休训练环境OpenCV、matplotlib及setuptools相关实验安装/缓存；setuptools78.1.0内嵌autocommand2.2.2为LGPLv3，不能作为未审查例外沿用。没有删声明来保留二进制。

## 保留与限制

通用GPU探针、网络诊断、hash/续传工具、非Ultralytics的旧GPU工件及基础测试摘要保留；通用脚本已去除旧模型目标。旧环境现为退休资产，依赖可能不完整，不再是可执行训练环境或发行锁。保留不等于B.1审查通过；全部排除出Annotator/Full候选分发，禁止自动恢复安装。

OpenVINO包含名为region_yolo/reorg_yolo的通用算子头文件，这是OpenVINO自己的操作定义，不能因为字符串相同就当作Ultralytics安装；当前产品也不引用OpenVINO。

项目外父级同名目录未触碰。没有修改全局环境、其他AI项目、驱动、VPN/代理，未删除真实厂区/人工标注业务资产。所有删除均校验解析后的路径在项目内。

## 清理后验证

scripts/release_gate.ps1重新读取实际安装dist-info、嵌套dist-info、缓存wheel身份、产品源码与开发EXE引用。结果见evidence/installed_scan.json、wheel_scan.json、candidate_manifest.json与RELEASE_READINESS.md。字符串扫描不作为唯一证明；保留历史文档/删除清单中的名称不代表运行依赖。
'''%(len(deleted),sum(x['bytes'] for x in deleted),len(extra)),encoding='utf-8')
rf=json.loads((R/'resolution.json').read_text(encoding='utf-8'))
lines=['# 第三方许可证与来源登记','','## Annotator / IDS','','自研代码Apache-2.0，LICENSE原文来源https://www.apache.org/licenses/LICENSE-2.0.txt；本地SHA256：`'+digest(G/'licenses/Apache-2.0.txt')+'`。','当前产品无NuGet/pip/npm第三方依赖、无随附字体/图标/FFmpeg/模型。系统WPF字体不复制入项目。','','| 环境组件 | 角色 | 许可/证据 | 随附 |','|---|---|---|---|','| Windows .NET Framework/WPF | 托管运行与界面 | Microsoft系统条款；https://learn.microsoft.com/en-us/dotnet/framework/get-started/system-requirements | 否 |','| Windows Media Foundation | 软件视频解码、真实样本时间 | Microsoft系统组件；https://learn.microsoft.com/en-us/windows/win32/medfound/source-reader | 否 |','| C# compiler / PowerShell | 开发编译与自动化 | 现有系统开发工具，单独登记，非Apache假定 | 否 |','| CPython 3.14.7 / pip 26.2.1 | 元数据和文件审计 | PSF / MIT及pip内嵌工具各自许可；不属于产品运行时 | 否 |','','## Full / NVIDIA候选递归依赖','','固定根：rfdetr '+str(rf['root_version'])+' [train]；Windows x64 / CPython3.12目标。仅元数据解析，不安装、不下载权重。候选并非成功安装锁。所有工件的内嵌许可证未完成前保持BLOCKED。','解析候选数：'+str(len(rf['packages']))+'；未解决解析错误：'+str(len(rf['errors']))+'。原始请求/依赖/URL/hash/标签见evidence/rfdetr/resolution.json。解析器为有界约束累积，不冒充完整回溯安装求解器。','','| 包 | 固定候选版本 | 声明许可（截短） | 决定 |','|---|---|---|---|']
for p in rf['packages']:
    lic=' '.join((p['declared_license'] or 'UNKNOWN').split()).replace('|','/')[:180]
    lines.append('| '+p['name']+' | '+p['version']+' | '+lic+' | BLOCKED：待具体工件/内嵌许可与功能验证 |')
lines+=['','审计过小wheel的LICENSE/METADATA及hash见evidence/rfdetr/artifact_review.json；只保留声明与证据，不安装候选wheel。PyTorch/CUDA大工件未批准。旧环境和下载缓存完全排除于候选分发。']
(G/'THIRD_PARTY_LICENSES.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
(G/'MODEL_LICENSE_REGISTER.md').write_text('''# 模型与权重许可登记

Full / NVIDIA：BLOCKED；Annotator无AI/模型依赖。

| 对象 | 固定依据 | 状态 |
|---|---|---|
| RF-DETR核心代码 | 官方tag1.11.2的LICENSE/README/pyproject与同版wheel核对 | Apache声明已取得；整栈尚未批准 |
| RFDETRNano/Small/Medium/Large检测权重 | 同tag README标为Apache；model_weights_source.txt保留官方映射 | 只列候选，未下载；具体权重hash/内容验证和本地运行NOT TESTED |
| rfdetr_plus与PML模型 | 官方明确区别许可 | 禁止引入，不下载、不安装 |
| 其他变体/权重 | 不从项目根许可证推断 | UNKNOWN/BLOCKED |
| 旧Ultralytics权重与实验权重 | 已退休 | 删除，非运行/分发依赖 |

来源：https://github.com/roboflow/rf-detr/tree/1.11.2 ，对应raw文件和wheel发布方URL/hash均保存在evidence/rfdetr。官方README的“Apache-designated model weights”不足以代替将来实际文件的SHA256和来源校验；当前没有任何获准加载权重。

自研RfDetrBackend.CanTrain=false，Train明确失败，不隐式下载，不降级CPU，不引入Plus。当前只实现IDS到COCO矩形检测快照适配与协议边界。
''',encoding='utf-8')
(G/'RELEASE_BLOCKERS.md').write_text('''# 尚未解决的重要阻断

## Annotator — NOT VERIFIED

1. 正式打包/签名/公开/分发未授权，持续冻结；无安装程序，首次安装、升级和卸载NOT TESTED。
2. 尚未在干净Windows10/11、AMD/NVIDIA机器验证；当前只在本机开发环境测试，Windows OS媒体/运行库先决条件尚未跨机器验收。
3. 真实鼠标完整流程仍为NOT TESTED：此前启动、本轮读取已打开窗口均被工具审批拒绝，原文分别见evidence/windows_gui_attempt.json、evidence/windows_gui_ui_revision_attempt.json。本轮标准标题栏、主目录、工具栏、审核后换帧、IDS命名已实现；WPF内部控件和合成尺寸/DPI渲染不代替真实屏幕/鼠标验收，真实响应/关闭取消仍待验收。
4. 后台流式hash/复制/IDS交换、进度/取消、范围抽帧、矩形与多边形/ROI编辑已实现，服务层与实际子进程回归已通过。AVI、MP4/H.264、MOV、MKV、HEVC、VFR及30分钟1080p合成视频已实测；不代表高码率25/30fps监控视频、全部容器变体或跨机支持。
5. 真正断网/网络拒绝、断电/硬杀崩溃恢复、海量数据、跨版本迁移、缩放平移、完整撤销重做、复杂多边形拓扑、冲突合并UI仍未验收或未实现。进程硬终止与资产移动/日志写入之间仍有极小的孤立文件窗口；不自动清理未知历史任务或业务文件。应用无网络API的静态检查不能替代运行时网络审计。

## Full / NVIDIA — BLOCKED

1. RF-DETR1.11.2[train]递归候选中存在B.1未允许许可。tqdm4.70.1实际wheel为MPL-2.0 AND MIT，certifi2026.10.23为MPL-2.0，不能简单选择MIT分支。未安装。
2. PyTorch2.14.1声明包含BSL-1.0与LLVM-exception组合；NumPy2.5.4还存在0BSD/Zlib/CC0声明及已实证Windows wheel GCC runtime GPL例外；SciPy和其他二进制内嵌库需逐工件审查。不能顶层BSD/MIT一票通过。
3. supervision0.31.2自身MIT，但传递绘图/图像/科学计算依赖未整体合规；其实际Detections/可视化调用已定位，不可盲目卸掉而声称训练仍可用。
4. 官方权重虽有Apache指定，具体文件未下载/校验、NVIDIA硬件与CUDA/SDK再分发未验证；训练不启用。

## 已自动解决和可行后续路径

标注端自主改用Windows内置运行组件和自研IDS/GUI，完全隔离训练许可问题；旧受限模型、NumPy GPL runtime、旧OpenCV/绘图/build副本已清理。使用本机媒体解码避免引入未经审查FFmpeg构建。

Full后续无需先申请许可例外：优先从固定Apache RF-DETR核心提取本地训练调用，去掉不需要的联网下载/Roboflow路径；以自研进度输出替换受限tqdm调用，并用OS证书信任的本地工件交付替代certifi下载路径。这些替换必须覆盖transformers等传递调用并跑训练回归，当前仅完成调用审计与阻断接口，未声称替换已完成。

科学计算可评估经审查的MSVC构建且不携带GNU runtime的NumPy/相关库，以及更小的COCO/图像依赖链；这是可研究替代路线，不是已取得合规二进制。本轮不通过伪造包元数据或删除许可证让训练“通过”。无需用户当前批准例外，证据缺口保持阻断。

专利、素材/商标权利及合同边界独立登记；不能由自动许可证扫描消除。
''',encoding='utf-8')
# Record the user's bounded portable authorization without changing Policy B.1 or normal freeze.
portable_auth=G/'portable-authorization-20261026.json'
if portable_auth.exists():
    a=json.loads(portable_auth.read_text(encoding='utf-8-sig'))
    blockers=G/'RELEASE_BLOCKERS.md';text=blockers.read_text(encoding='utf-8')
    text=text.replace('正式打包/签名/公开/分发未授权，持续冻结；无安装程序，首次安装、升级和卸载NOT TESTED。','2026-10-26用户仅授权一次Annotator本机Windows x64便携测试包交付；授权状态：'+a['status']+'。签名、公开发布、Full及后续新版打包不在授权内；常规冻结保持。无安装程序，安装/升级/卸载NOT TESTED。')
    if (E/'portable-independent.json').exists():
        local=json.loads((E/'portable-independent.json').read_text(encoding='utf-8-sig'))
        text=text.replace('当前只在本机开发环境测试','已有本机独立TEMP目录便携EXE执行记录（'+local['status']+'）；其他电脑未实测')
        text=text.replace('真正断网/网络拒绝、断电/硬杀崩溃恢复、海量数据','真正断网/网络拒绝、断电/任意时刻崩溃恢复、海量数据')
        text+='\n## 本次便携测试交付证据\n\n见evidence/portable-audit.json、portable-independent.json及windows_gui_portable_attempt.json。受控测试已验证在写完临时清单、原子替换前硬终止后恢复最后提交数据；不等于真实断电或任意资产阶段零丢失。纯4.8系统、其他电脑/显卡、物理快捷键仍NOT TESTED。\n'
    blockers.write_text(text,encoding='utf-8')
print('Governance documents regenerated from evidence; normal release freeze retained; explicit one-time authorization recorded separately')
