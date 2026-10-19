"""Render this round's Markdown reports from sealed local evidence."""
import json,re,hashlib,subprocess,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'artifacts/p37a-closure-20261019'
load=lambda p:json.loads(p.read_text(encoding='utf8'))
e=load(OUT/'data-final/acceptance-evidence.json');b=load(OUT/'before.json');integrity=load(OUT/'integrity.json');native=load(OUT/'native-real-final.json')
assert all(integrity.values()) and e['status']==native['status']=='PASS'
log=(OUT/'combined-native-final.log').read_text(encoding='utf8',errors='replace')
summary=next(line.strip('= \r') for line in reversed(log.splitlines()) if ' passed' in line and ' in ' in line)
project=Path(b['root']);job=e['cuda_job'];rid=job['result']['run_id'];result=load(OUT/'data-final/project-copy/training'/rid/'result.json')
assert not result.get('forbidden_imports')
frames=[dict(id=r['id'],matches=b['files'].get(str(project/r['path']))==r['sha256']) for r in b['tables']['frames']]
media=[]
for r in b['tables']['media_assets']:
    for role,p in [('managed',project/r['path'] if r.get('path') else None),('original',Path(r['original_path']) if r.get('original_path') else None)]:
        digest=b['files'].get(str(p.resolve())) if p else None
        media.append(dict(id=r['id'],role=role,path=str(p) if p else None,available=digest is not None,matches_registered=digest==r['sha256'] if digest else None,state=r['state']))
protection=dict(frames_checked=len(frames),frames_match_registered=all(r['matches'] for r in frames),media=media,unchanged=integrity)
(OUT/'provenance-check.json').write_text(json.dumps(protection,ensure_ascii=False,indent=2),encoding='utf8')
assert protection['frames_match_registered'] and all(r['matches_registered'] is not False for r in media)
def write(name,text):
    (ROOT/name).write_text(text.strip()+'\n',encoding='utf8')
def append(name,text):
    p=ROOT/name;old=p.read_text(encoding='utf8');marker='\n## 2026-10-19 收尾补充\n'
    if marker in old:old=old.split(marker)[0]
    p.write_text(old.rstrip()+marker+'\n'+text.strip()+'\n',encoding='utf8')

table='''| 验收领域 | 结果 | 证据与边界 |
|---|---|---|
| P3.7-A RF训练功能 | PASS | 沿用1f1db7d的真实GUI短训；本轮新队列/取消/历史测试、真实CUDA重载成功；未重复训练 |
| Qt原生GUI稳定性 | PARTIAL | 原始崩溃未归因；Windows原生单测/合并/重启/菜单压力测试通过相关操作，但有下述旧断言失败 |
| P2人工标注兼容 | PASS | box/polygon/ROI画布与P2真实GUI回归；原项目全表、251帧及所有保护文件不变 |
| P3 Native/COCO导出兼容 | PASS | 当前200图/402框/16正常副本两种导出校验；默认Native的原生GUI断言通过 |
| 训练历史清退 | PASS | 原项目3旧YOLO归档、2RF显示；合成夹具覆盖5种状态、项目切换、重新打开及队列取消 |
| Registry历史隔离 | PASS | 3旧模型归档、2RF显示；5模型及关联ONNX哈希验证；禁止旧模型登记/晋升/配置 |
| RF训练链路零Ultralytics | PASS | 本轮真实GPU重载、主进程导入阻断、Worker模块轨迹、隔离解释器及污染探针 |
| P3.5旧推理限制与保护 | PASS | 提交层/服务双重拒绝；5份完成缓存只读哈希验证；真实GUI历史缓存回放，未启动Worker |
| 全产品零Ultralytics迁移 | PARTIAL | 旧源码、环境、P0验证脚本和未来打包依赖仍保留；离线RF待B，不能声称发行闭包已无旧依赖 |
| 软件分发许可 | BLOCKED | 未完成Qt/FFmpeg/OpenCV/NVIDIA及部分通知/产权材料；保持冻结 |'''
common=f'''日期：2026-10-19。基线 `1f1db7d338903d93a4add4f600dda11a5db5de00`，分支 `feature/p37a-rfdetr-training`。总体 **PARTIAL**，未认定Qt原始异常彻底解决。

`PACKAGING_FREEZE=TRUE`；`DISTRIBUTION_STATUS=BLOCKED`。无打包、push、环境安装、系统Python/驱动修改、YOLO重训或P3.7-B/P4实施。IVAD自研源码继续内部专有。

本轮本地证据目录：`artifacts/p37a-closure-20261019`。原生合并最终结果：**{summary}**。不修改旧测试断言，也不把这次回归写成全绿。

最终RF与清退专项同进程41 PASS（15.51秒），含最后的UNKNOWN任务门禁；中立预检兼容3 PASS、数据泄漏保护7 PASS、最终串行150% DPI专项1 PASS。批次存在重叠，不相加为独立用例数。真实缓存GUI补充验证已等到首帧解码，并完成逐帧、播放/暂停及安全关闭，不能仅以loaded标志代替画面证据。

{table}

## 未通过/未执行的测试

最终合并批次中的 `test_four_tabs_filter_sort_draft_batch_freeze_and_export` 仍要求默认产生 `*-yolo_detect-*`，本轮按要求实际默认产生Native，所以15秒等待失败。原断言及原始失败日志保留；新原生控件测试及真实200图服务导出验证Native/COCO行为。该旧测试未更新，因此整个旧回归集不是PASS。已有 `test_real_copy_200_restart_versions_and_training_picker` 缺少它专用的初始副本，沿用自身SKIP；本轮另行核实当前真实冻结集及原生重启，不将SKIP算作通过。

早期本轮日志包含服务预检错误和测试容器复用超时，分别通过修复中立预检兼容入口与修正重启夹具解决，所有日志保留。合并r2在进程运行期间源码修复，终版单独启动新进程复验，以final日志为准。

未制造真实OOM/驱动物理失效，未测试净机发行、最终Qt库替换、RF离线视频推理。本轮未新增训练梯度运行；训练CUDA证据沿用原P3.7-A，新GPU任务仅为已登记权重的两次规范验证。

## 当前数据与真实GPU证据

当前真实项目：5训练、5模型、217标注、721修订、251帧、3摄像头、8媒体记录、1冻结版本。不能沿用旧报告3训练/3模型/720修订当作当前基线。

`8525test1 v1` / `{e['dataset']['version_id']}`：200图、402目标、16正常负样本，160/40/0划分；manifest SHA256 `{e['dataset']['sha256']}`。类别UUID、内部ID、矩形框合法性与Camera/Media/Frame关系均在独立副本核实；正常样本保留。Native及COCO export均实际执行、重新读取并计数200/402，原版本未改。

当前代码真实CUDA验证Job `{job['id']}`，TrainingRun `{rid}`，权重模型 `{job['payload']['initial_model_id']}`，最终 `{job['state']}`。40验证图，两次重载parity `{result.get('parity',{}).get('status')}`；P/R/mAP50/mAP50–95为 `{job['result']['metrics']}`。这是现存模型的当前结果，不替换旧模型实验成绩。详细模块轨迹、GPU前向证据与预测SHA见 `data-final/project-copy/training/{rid}/result.json`。

{len(b['files'])}个现存文件（含视频、缓存、权重、人工帧、冻结集、日志）前后SHA完全一致，全部SQLite表内容一致；251帧均匹配登记SHA。可读登记视频逐文件对照，缺失旧来源路径保留基线状态，不伪造恢复。两份用户已有未跟踪规划文档SHA不变且不提交。见 `before.json`、`after.json`、`integrity.json`、`provenance-check.json`。

## P3.7-B条件与停止

RF权重、显式类别映射、独立CUDA解释器、GPU锁、冻结数据转换及Registry已具备可复用基础。Qt原始异常仍需定位；旧回归中的默认YOLO断言需要单独审阅，不能据本轮声称无保留PASS。B仍需用户明确授权，才可实现独立RF离线Worker、缓存身份/隔离、导出及取消验收。本轮停止，不自动进入B/P4或打包。
'''
write('reports/P37_A_ACCEPTANCE_CLOSURE.md','# P3.7-A Final Acceptance Closure\n\n'+common)
append('reports/P37_A_ACCEPTANCE.md','当前基线与计数以2026-10-19实际快照为准；旧章节保留为2026-10-16历史证据。\n\n'+common)

write('reports/P37_A_QT_CRASH_INVESTIGATION.md',f'''# P3.7-A Windows Qt 原生异常调查

日期：2026-10-19。结论 **PARTIAL：根因未确认**。未据操作系统、驱动、Qt或Python模块名直接归因，也未声称修复原异常。

## 原始证据

原日志 `artifacts/p37a-20261016/regression.log` 原样保留，858字节，SHA256 `3908392558dd1448843376687ce2a49a5a5808b3e2545424104dfd3a9bbbbd9b`。含 `0x8001010d`、access violation及SQLAlchemy `engine/default.py:945` / `database.py:51` 工作线程片段，但没有失败nodeid、完整主线程或原始命令/测试顺序。33个进度点不能唯一确定触发用例，因此不能声称已经精确复现原始失败用例或完成因果二分。

本轮只读采集Application事件1000/1001，见 `windows-events.json`、`wer-details.txt`。2026-10-16 20:07:41事件1000报告Python312.dll、0xc0000005、offset0x287730；20:07:51 WER记录c000041d，与原日志20:07:52落盘时间相邻。异常模块位于Codex捆绑Python运行时，不是证明该运行时负责的证据。未找到可据此分析的完整原始内存转储/符号栈；不修改系统WER或COM配置。

## 排查与真实复验

使用`.venv-p1`、Python `-X faulthandler`、`PYTHONFAULTHANDLER=1`、必要Qt QPA日志；最终大批次设 `faulthandler_timeout=45`。平台实际为 `windows`，本轮没有用offscreen替代原生结果。

| 调查点 | 实际检查与结论 |
|---|---|
| QComboBox/QMenu及C++包装生命周期 | 原RF GUI单测；新增菜单弹出/关闭/deleteLater和异步刷新压力、两次窗口/服务重建。未复现原访问异常，不证明无所有权缺陷 |
| QWidget/QObject所有权 | QTimer以页面为父；QMenu压力夹具以页面为父。检查MainWindow/TrainingPage/AsyncRunner/VideoPlayer关闭代码；未定位与原异常相连的错误释放 |
| 跨线程signal/slot | AsyncRunner完成信号连接QObject Slot，后台不直接写训练控件；VideoPlayer通过队列关闭、解码信号回GUI。检查不替代线程竞态证明 |
| 定时器/异步结果 | 训练页刷新有busy和root/model门禁；本轮主任务列表新增项目ID门禁，防止切项目后旧查询回写 |
| Worker取消/关窗/GPU锁 | 原26项RF契约回归、当前队列取消、跨进程锁/自有进程树测试；真实副本CUDA验证完成，无模型误登记；未重复真实GPU训练关窗实验 |
| QApplication/fixture | pytest-qt qapp为session作用域；初次新增测试复用了被MainWindow.close关闭的服务容器导致等待超时，修正为真实新容器重启。这是本轮夹具缺陷，不能冒充旧原生崩溃根因 |
| Windows COM | 独立GUI探针通过CoGetApartmentType只读记录建QApplication前后状态（native-real.json）；没有调用CoInitializeEx改变线程模式；不足以解释历史异常 |
| 合并批次共享状态 | 最终合并 `{summary}`；没有原生访问异常。唯一旧GUI断言冲突及既有条件SKIP见Closure，未删除/屏蔽它们 |

原生单独压力测试15项通过，RF专项26项通过，150% DPI专项1项通过（最终串行复验日志见目录）；真实数据副本另行主窗口打开/缓存回放/关闭成功。较大批次当前未重现致命异常，因此没有可重复失败组合用于可信二分。不能推断历史问题只发生于合并批次。

## 修复与剩余条件

本轮修复的是后端/历史隔离、队列历史投影、兼容数据预检与项目回写门禁；未提交假设性的Qt生命周期重构。复验未复现不等于已归因。需要可重复原始命令/顺序或新的完整原生转储后才能做触发组合二分和最小Qt修复；对应验收保持PARTIAL。
''')

archive='''# P3.7 Legacy Training Read-only Archive

日期：2026-10-19。分类来自当前真实SQLite快照，不改写训练事实。明确架构yolo11n/yolo26n且无冲突backend的历史记录，作为LEGACY_READ_ONLY；backend缺失但明确架构作为分类证据，不能把未知架构猜成YOLO。冲突或信息不足返回UNKNOWN；当前真实记录UNKNOWN=0，合成冲突测试已覆盖。

只读归档是服务查询的派生分类，不新增migration、不更新details/state/revision，不改变任何UUID或已有关系。默认runs/versions仅返回ACTIVE_RFDETR；开发审计显式include_archived=True可查全部，verify仅读文件哈希，不反序列化历史权重。

| TrainingRun UUID | 架构 | 原状态 | DatasetVersion | ModelVersion | 查询分类 |
|---|---|---|---|---|---|
'''
for r in e['runs']:
    linked=','.join(m['id'] for m in e['models'] if m.get('run_id')==r['id'])
    archive+=f"| {r['id']} | {r['model']} | {r['state']} | {r.get('version_id')} | {linked} | {r['archive_classification']} |\n"
archive+='\n正式列表2条RF、隐藏3条YOLO。真实库开始和结束均5条；本轮验证只在独立副本新增验证TrainingRun，非新增训练或新模型。所有状态均通过后端过滤，不限定成功状态。排队时使用持久JobRecord投影及时显示，创建TrainingRun后按job_id去重；取消/预检失败没有TrainingRun时仍能看到真实Job状态，投影ID明确来自JobRecord，不伪造TrainingRun UUID。\n\n'
for r in e['runs']:
    if r['archive_classification']!='LEGACY_READ_ONLY':continue
    archive+=f"## {r['id']}\n\n原路径 `{r['path']}`；参数 `{json.dumps(r.get('parameters'),ensure_ascii=False)}`；Epoch `{r.get('progress',{}).get('epoch','未单列，见原结果日志')}`。日志、Checkpoint、验证指标及模型SHA仍在原目录和数据库，未归一化覆盖；缺字段不补猜。\n\n"
archive+='## 模型与SHA256\n\n| UUID | 架构 | 状态 | SHA256 | 关联Run |\n|---|---|---|---|---|\n'
for m in e['models']:archive+=f"| {m['id']} | {m['model']} | {m['state']} | {m['sha256']} | {m.get('run_id')} |\n"
archive+='\n5个权重及其登记ONNX均校验通过。逐文件SHA、完整原始details及所有表在本地before/after.json；不把审计分类写回原数据库。\n'
write('reports/P37_LEGACY_TRAINING_ARCHIVE.md',archive)

write('reports/P37_LEGACY_YOLO_RETIREMENT.md',f'''# P3.7 Legacy YOLO Retirement

日期：2026-10-19。正式训练仅Nano；旧事实与资产完整保留。共处置7个普通界面选项/操作：2个YOLO数据导出选项、2个YOLO基础模型选项、1个旧手工权重导入流程、离线新推理按钮与按配置复用旧引擎身份按钮2项。归档查询同时移除其派生模型选择项，不另按历史行数重复计入口。标注工作台未发现需删除的独立YOLO入口，保留box/polygon/ROI等人工功能；Nano仅目标检测，不宣称实例分割。

## 源码/调用与依赖矩阵

| 分类 | 实际文件/资产 | 可达关系、运行依赖与证据 |
|---|---|---|
| ACTIVE_RFDETR | compute/rfdetr_contract.py、rfdetr_probe.py、rfdetr_train_worker.py、rfdetr_evaluation.py、rfdetr_weights.py、gpu_lock.py | 正式Nano、独立解释器-I、官方RF API；实际CUDA Job及模块轨迹见Closure |
| ACTIVE_RFDETR | services/training_router.py、rfdetr_training_service.py、core/application.py | GUI→Router→RFService→RFWorker；旧路由方法直接拒绝，无动态旧import；预检拒绝旧初始化/环境 |
| ACTIVE_RFDETR | datasets/rfdetr.py | 从冻结人工真值直接产生COCO；类别UUID/内部ID/模型ID映射，未经过YOLO标签 |
| REPLACED | gui/training_page.py、training_controls.py | 新训练选择仅Nano，旧模型/恢复不可启动；排队/5状态/取消/重启测试 |
| REPLACED | gui/dataset_page.py | Native默认、COCO第二项；底层导出器未删 |
| LEGACY_READ_ONLY | datasets/exporters.py 的yolo_detect/yolo_segment分支 | 自身文本/坐标导出，无Ultralytics import或运行库；仅开发兼容工具，普通GUI不列出。YOLO格式不等于AGPL库 |
| LEGACY_READ_ONLY | services/model_service.py、TrainingRun/ModelVersion details | 服务默认查询只RF，显式归档读；原SHA/UUID/审核历史/数据集/Run关联不变；历史verify/export为文件校验/复制 |
| REMOVABLE_LATER | services/training_service.py、compute/train_worker.py、compute/model_adapters.py旧条目 | 旧训练服务启动/预检封禁；Worker保留YOLO/DetectionTrainer/NMS imports及历史证据，正式Router无调用；Adapter只描述符不是库 |
| BLOCKED | services/offline_demo_service.py历史run、compute/offline_worker.py | 普通提交和服务run均DEMO_MIGRATION_PENDING；历史实现保留，未启动；RF离线待P3.7-B |
| LEGACY_READ_ONLY | services/offline_cache.py、offline_demo_service.load/export/screenshot、demos目录 | 5完成缓存哈希核验；load仅读取manifest/成品视频，不导入Ultralytics；真实GUI历史回放验证，保留所有检测缓存 |
| REPLACED | jobs/manager.py、gui/main_window.py | 新旧YOLO提交拒绝；活动任务不按后端/项目丢弃，显示分类；完成AI历史按项目/正式后端过滤；cancel/get不按界面过滤 |
| LEGACY_READ_ONLY | .venv-nvidia、artifacts/p0、原YOLO PT/ONNX及训练目录 | 历史运行库和权重未删除/改名/卸载；普通GUI不使用此解释器；RF污染探针通过 |
| REMOVABLE_LATER | scripts/validate_p3_model.py、旧P0/P3/P3.5 GPU验证脚本 | 开发历史入口直接依赖Ultralytics；本轮未运行旧AI，不计入RF闭包，也未认证为可发行 |
| BLOCKED | packaging/nvidia/requirements-cuda.inventory.txt、packaging/requirements-distribution-lock.txt、packaging/ivad.spec及BUILD_PLAN | 未来构建方案/旧依赖材料仍有旧库；未构建最终payload，不改旧包、不宣称发行零依赖 |
| LEGACY_READ_ONLY | 旧报告/指南及licenses通知 | 保留真实历史与版权，不因字符串匹配就删除 |
| UNKNOWN（记录级） | backend缺失且架构不明确/冲突 | 默认排除正式选择，禁止新操作；当前真实0条；测试验证冲突不猜测 |

项目完整静态引用和动态导入检查在dependency-references.txt；检查直接imports、动态find_spec/模块阻断、Worker subprocess路径和三个环境实际包清单，不只查字符串。GUI21包、RF96包均find_spec无Ultralytics；旧环境48包保留。旧PYTHONPATH污染在-I下不可见；实际Worker forbidden_imports为空，主进程未导入旧training_service。

真实库3条旧YOLO训练和3个旧模型只读归档、2RF训练与2RF模型默认可见。归档明细与SHA见P37_LEGACY_TRAINING_ARCHIVE.md。活动GPU任务即使旧或UNKNOWN也保留可见；不重排旧任务，不终止无关GPU进程。已取消任务不会登记成功模型，沿用同事务门禁和GPU锁。

## 验收限制

{summary}，旧GUI默认YOLO断言失败保留，专用旧副本用例条件SKIP不计成功。新行为由独立原生GUI与200图导出验证。Qt根因未定，总体PARTIAL；不是全产品零Ultralytics发行认证。RF离线Worker、RF缓存身份与RF离线导出仍待B。

历史数据前后全表及{len(b['files'])}文件SHA不变；没有删除、迁移原数据库、重训YOLO、改系统环境或模型改名。`PACKAGING_FREEZE=TRUE`，`DISTRIBUTION_STATUS=BLOCKED`。
''')
append('legal/ULTRALYTICS_ISOLATION_AUDIT.md',f'''本补充替代上文“正式GUI仍可启动旧训练”的当前状态描述，历史审计原文保留。

正式GUI→training_router→RFDETRTrainingService→.venv-rfdetr -I→独立RF Worker。旧路由封禁，业务查询隐藏3旧训练/3旧模型；旧模型register/transition/configure_camera/record_validation拒绝，verify和文件复制导出仍可只读审计。P3.5新任务在JobService和OfflineDemoService双重拒绝，历史成品缓存可读。

本轮当前代码真实CUDA重载Job `{job['id']}`成功；主进程装配使用禁止Ultralytics导入的Finder，Worker保留其模块轨迹；旧PYTHONPATH污染探针通过。原始旧环境、YOLO权重、源码、通知和构建清单仍保留，不能声称全产品零依赖或版权链全部闭合。详细逐文件分类见 `reports/P37_LEGACY_YOLO_RETIREMENT.md`。

本轮未改依赖版本，不重新出具法律认证。沿用固定版本的P37_FREE_PROPRIETARY_LICENSE_AUDIT中未闭合项：Qt对应源码和可替换实测；FFmpeg/PyAV构建/codec对应；OpenCV捆绑视频库；NVIDIA逐DLL可分发清单/通知；部分包缺失通知、产权来源及最终payload审查。公司专有源码策略保持，未购买许可。`DISTRIBUTION_STATUS=BLOCKED`，`PACKAGING_FREEZE=TRUE`。''')
append('reports/P37_ZERO_ULTRALYTICS_DEPENDENCY.md',f'''当前Router不再延迟启动旧训练，所有普通新训练仅RF Nano。GUI/RF环境分别21/96包，无Ultralytics可导入；旧环境48包原样保留。当前GPU验证 `{job['id']}` / `{rid}` 成功，两次规范评估parity PASS，forbidden_imports为空；主进程导入阻断及-I旧PYTHONPATH污染探针通过。

本轮验证不是新梯度训练；既有P3.7-A短训证据保留。P3.5新旧引擎任务封禁，历史缓存只读，不声称RF已接管离线视频。全产品迁移PARTIAL、正式发行BLOCKED，Qt根因仍PARTIAL。''')
assets=ROOT/'reports/P37_A_CLOSURE_assets';assets.mkdir(exist_ok=True)
for name in ['training.png','dataset.png','models.png','offline-history.png']:
    source=OUT/'native-real-final'/name;target=assets/name
    if not target.exists():shutil.copyfile(source,target)
    else:assert hashlib.sha256(source.read_bytes()).digest()==hashlib.sha256(target.read_bytes()).digest()
changes=set(subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).splitlines())
changes.update(subprocess.check_output(['git','diff','--cached','--name-only'],cwd=ROOT,text=True).splitlines())
changes.update(subprocess.check_output(['git','ls-files','--others','--exclude-standard'],cwd=ROOT,text=True).splitlines())
changes-={'docs/P37_IMPLEMENTATION_PLAN.md','reports/P36_GIT_CLOSEOUT_AND_P37_PLANNING.md'}
with (ROOT/'reports/P37_A_ACCEPTANCE_CLOSURE.md').open('a',encoding='utf8') as f:
    f.write('\n## 修改文件\n\n'+''.join('- `'+name+'`\n' for name in sorted(changes)))
    f.write('\n## 本轮真实GUI截图\n\n以下截图来自独立项目副本；该截图会话显式关闭GPU探测，CUDA证据另见真实验证Job，不将空GPU选择器冒充CUDA测试。副本有原2条RF训练加本轮1条验证记录，故截图会话查询3条RF记录；原项目仍为2条。历史缓存模型显示不可用于新推理，回放仍为原模型UUID及缓存检测结果。\n\n')
    for name in ['training.png','dataset.png','models.png','offline-history.png']:f.write('!['+name+'](P37_A_CLOSURE_assets/'+name+')\n\n')
p=ROOT/'reports/P37_A_ACCEPTANCE_CLOSURE.md';p.write_text(p.read_text(encoding='utf8').rstrip()+'\n',encoding='utf8')
print(summary)
