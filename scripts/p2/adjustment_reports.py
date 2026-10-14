"""Write the four requested adjustment reports from final local evidence."""
import json,xml.etree.ElementTree as ET
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'artifacts/p2-adjustment'
def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
def write(name,text):(ROOT/'reports'/name).write_text(text.strip()+'\n',encoding='utf-8')
suite=ET.parse(out/'pytest.xml').getroot().find('testsuite');assert suite.get('failures')=='0' and suite.get('errors')=='0'
total=int(suite.get('tests'));preserved=read('preservation.json');assert preserved['status']=='PASS'
migration=read('migration-check.json');assert migration['status']=='PASS'
cases=suite.findall('testcase');counts=Counter(c.get('classname') for c in cases)
table='\n'.join(f'|{name}|{number}|0|' for name,number in sorted(counts.items()))
ui=read('ui-native.json');dpi=[read('ui-'+label+'.json') for label in ['100','native','200']]
dimensions='\n'.join(f"|{r['dpr']:.2f}|{r['window']}|{r['table']}|{r['rows']}|" for r in dpi)
limits='''只保存第一个视频轨的画面，未保存音频；重新编码H.264 CRF18并非无损拷贝。片段时间按实际显示帧边界，范围采用[start,end)，首帧时间会重置为0，末帧显示时长可能与输入秒数存在帧级差异。最短100毫秒且至少两帧；片段再次裁片段明确拒绝。4K/小时级录像/大规模数据/真实选煤厂标注质量/断电强杀恢复未测，不作工业精度承诺。重复保存使用新UUID，不覆盖或幂等复用旧片段。'''
shared=f'''日期：2026-10-14（Asia/Shanghai），P2补充修改；未进入P3–P6。基于原P2提交3b4b9ca增量实施，无第二套页面/业务系统，未新增环境或依赖。

主套{total} passed / 0 failed / 0 errors / 0 skipped，原有71项全部保留（其中P1为37项），新增13项。另100%/200%DPI各1项同GUI流程复测通过，不重复计入主套。XML/log、截图、布局尺寸和保护校验都保存在artifacts/p2-adjustment/。

所有测试录像为自制色块/文字素材；长录像20秒500帧，截取[5,7)实际50帧；没有工厂隐私视频或第三方素材，真实工业数据NOT TESTED。'''
write('P2_UI_ADJUSTMENT.md',f'''# P2视频管理界面补充调整

最终状态：PASS（本轮授权范围）。

{shared}

复核SRS、ARCHITECTURE、DECISIONS、P1_ACCEPTANCE、MediaPage/P2Controller、AnnotationPage、JobService和现有Schema0003后实施最小相关改动。

左侧保留原录像/方式/状态/时长/编码/分辨率六列，移除160px高度上限，以QSplitter分配左右宽度，可拖分隔条；表格横纵滚动/选中高亮，文件名列260逻辑像素、tooltip全文。可选摄像头/厂区/设备导入信息默认折叠，给多条录像留空间。右侧是QScrollArea，统一范围、实际播放器及原抽帧/片段标签，新增保存片段标签页。播放器控制拆为两行。

同页QTabBar统一未选海蓝#176a94/白字，hover及selected白底#111字，边框一致。Qt实际渲染像素断言未选中/激活/悬停颜色；悬停以Qt鼠标事件投递测试，截图在tabs-hover-*.png。未使用静态效果图冒充运行界面。

起终点有中文标签/tooltip、当前画面定位按钮和范围长度；8个抽帧关键项均有可直接阅读的灰色辅助说明及tooltip，明确1.000秒/帧、张数上限、PNG/JPEG、JPEG专用质量、0保留分辨率、阈值越小越敏感、保留基础样本。说明明确变化筛选不等于工业异常判断。PNG时质量控件禁用。取消按钮改为“取消当前录像抽帧”，实际只取消当前录像的抽帧；另有当前片段保存取消按钮，其他项目/任务不受影响。

|真实DPR|窗口逻辑尺寸|左列表逻辑尺寸|实际列表行|
|---:|---|---|---:|
{dimensions}

当前原生DPI列表高度{ui['table'][1]}，原最大160，改善为{ui['table'][1]/160:.2f}倍；六列完整保留，窄左栏用横向滚动查看后列。右侧内容增多会滚动，不把左表再压成顶端条。100%/200%截图及GUI操作通过，未修改系统显示设置。

截图目视修复了Windows深色主题导致的说明区低对比度，操作区明确浅色背景；已重新截图。参数说明直接显示，不以自动化环境不稳定的原生tooltip弹出断言作为验收依据。

{limits}
''')
write('P2_CLIP_SAVE_FEATURE.md',f'''# P2人工保存视频片段功能

最终状态：PASS。

{shared}

使用方法：选左侧原始录像→播放器定位，设置上方起点/终点或手填秒数→“保存视频片段”页填可选名称/备注→保存。界面与任务中心显示进度/结果；成功新增CLIP行。选CLIP可按普通媒体播放、抽帧、人工标注、审核、冻结和导出。

复用现有p2_clip JobService任务、MediaService、ProjectStore和PyAV wheel的FFmpeg/libx264，不安装系统FFmpeg，不调用模型或CPU AI。后台按实际PTS解码范围[start,end)，旋转落实到像素，减首帧时间后保留VFR间隔；H.264 CRF18/fast/bf0输出MP4。常规偶数分辨率yuv420p，奇数尺寸使用yuv444p（奇数分辨率未有专门样本，不扩张兼容声明）。

Schema0004只对media_assets增加kind（默认ORIGINAL）、parent_id、clip_info JSON；旧0003升迁前SQLite backup，原表列和值保持。SQLite parent_id为应用层关系，服务/一致性检查验证父记录、源hash及范围；不重建表。clip_info含请求范围、实际首末源PTS相对时间、生成时间、源hash、帧数、编码、旋转、备注，文件路径/UUID/生成任务仍用原媒体列。片段COPY落项目内，来源REFERENCE也不修改原文件。

UUID暂存→编码→完整重解码计数/实际PTS校验→源与目标SHA256→提交文件/数据库READY。失败/取消只清理本任务已知UUID文件，不登记假成功。提交前取消会停止；已完成发布返回媒体UUID的任务为SUCCEEDED/100%，末尾取消不把有效资源误记为未完成。写盘预检按范围估算并留余量，实际写盘失败会清理记录。强杀跨文件/数据库窗口仍需人工检查，不承诺断电绝对原子性。

真实测试：20秒REFERENCE源[5,7)产生50帧，源hash不变；新COPY CLIP真实播放、抽帧/标注/YOLO导出、一致性PASS；GUI点击保存→CLIP行→实际播放；倒序、50ms、越界、负数拒绝；可控编码错误不登记READY；编码中取消及真实队列取消均无残留.partial/CLIP记录；0003迁移原列和备份保留；VFR/noninteger/rotation裁剪输出每帧PTS与源区间首帧归零一致。

片段与原录像保留source_group_id，共同按原来源分组（camera优先），防止父子录像进不同数据集划分；既有标注/帧接口复用，未自动复制原录像目标框或推断故障类别。

{limits}
''')
write('P2_TEST_RESULTS.md',f'''# P2测试结果（补充修改后的当前版本）

{shared}

|模块|通过|失败|
|---|---:|---:|
{table}

命令：.venv-p1/Scripts/python.exe -m pytest tests -q --junitxml=artifacts/p2-adjustment/pytest.xml。本次耗时{suite.get('time')}秒。测试证据通过IVAD_TEST_EVIDENCE_DIR和IVAD_P2_GUI_EVIDENCE_DIR指向新目录；原artifacts/p2不覆盖。原2026-10-13的71项报告/证据保持在artifacts/p2及artifacts/p2-adjustment/history/。

新增13项：长REFERENCE片段/标注/数据集；4种无效时间范围；服务取消；模拟编码失败；0003→0004保留原媒体列和备份；真实GUI左右布局/标签色/帮助文字/保存及播放，切回长录像终点恢复完整时长；真实队列取消历史；VFR、非整数帧率、旋转分别裁剪校验。100/200%DPI各额外1项同GUI流程通过，原生175%在主套中通过。

额外迁移集成验证：从上一版真实P2持久化项目只读backup出副本，迁移0004后{migration['tables_preserved']}张旧表的全部原列和数据逐行相同，生成迁移备份；原项目不写入。结果migration-check.json，未重复计入主套用例数。

保护结果：preservation.json=PASS，{len(preserved['prior_p2_artifacts'])}份上一版P2原始证据hash不变，6份旧P2报告完整历史副本hash不变，P0/P1历史文件及原GPU/GUI全部包版本一致。没有下载新包、改驱动、全局Python或系统代理。本轮P1设备回归调用既有CUDA worker，未新增训练。

开发过程中修正测试注入路径、Qt自动化悬停事件投递及原生tooltip弹出测试。最终改为直接可见辅助说明并保留标准tooltip，验证可见文本；标签悬停色通过真实Qt事件渲染验证。最终没有未解决失败，不将故障注入称为现场断电/坏码流实验。

{limits}
''')
write('P2_ACCEPTANCE.md',f'''# P2验收报告（2026-10-14补充修改）

**PASS：P2工程功能及本轮UI/人工片段补强通过；尚未验收工业模型或真实选煤厂场景。**

{shared}

|本轮要求|结论|
|---|---|
|左右布局/更大列表/滚动/六列/长名|PASS，实际窗口/DPI截图与尺寸记录|
|标签蓝白/悬停与激活白黑|PASS，实际Qt渲染颜色断言|
|参数中文辅助说明/tooltip|PASS，可见说明及控件文本，明确非工业异常判断|
|人工截取实际视频文件|PASS，后台编码、解码/PTS/hash校验后发布CLIP|
|片段播放/抽帧/标注/数据集|PASS，服务与真实GUI闭环|
|错误范围/取消/编码失败|PASS，不登记错误READY或覆盖源|
|新增迁移且旧数据保留|PASS，0003→0004备份与原媒体列保持|
|原P0/P1/P2能力及历史证据|PASS，原71项回归+hash/环境清单|

修改模块限于现有MediaPage/P2Controller/VideoPlayer、MediaService、原任务状态、必要媒体关系迁移及DatasetService来源分组；没有新建第二套页面，AnnotationService/画布等原真值模块未重写。实现详见P2_UI_ADJUSTMENT.md、P2_CLIP_SAVE_FEATURE.md，测试详见P2_TEST_RESULTS.md。

本轮{total}通过/0失败，额外DPI各1通过；旧P2验收和原始证据保留。数据库/环境不重建，不修改ComfyUI/全局Python/CUDA或驱动，无新增安装包。源码本地nvidia-first提交记录以git log为准，没有远程推送。

操作：双击启动IVAD.cmd→项目管理打开原项目→视频管理。旧项目首次打开自动迁移0004并保留.migration-*.backup。新样例位于artifacts/p2-adjustment/demo/，仅为合法自制工程样本。操作步骤见docs/P2_USER_GUIDE.md补充部分。

{limits}

P3建议：界面与片段数据输入路径已具备继续开发的工程条件；正式工业训练仍需足量合法、多来源、人工审核真值及用户另行批准。本轮未开发训练/报警/RTSP/AI预标注/部署，已停止在P2等待审阅。
''')
print('reports updated',total,'tests')
