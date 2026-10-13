"""Generate P2-only reports from final evidence; never rewrite P0/P1 reports."""
import json,sys,subprocess,xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];out=ROOT/'artifacts/p2'
def read(name):return json.loads((out/name).read_text(encoding='utf-8'))
def write(path,text):(ROOT/path).write_text(text.strip()+'\n',encoding='utf-8')
suite=ET.parse(out/'pytest.xml').getroot().find('testsuite');assert int(suite.get('failures'))==0 and int(suite.get('errors'))==0
total=int(suite.get('tests'));cases=suite.findall('testcase');p1=sum('test_p2_' not in c.get('classname','') for c in cases)
preserved=read('preservation.json');assert preserved['status']=='PASS'
media=read('media-validation.json');exports=read('export-validation.json');qt=read('qt-decode.json')
commit=subprocess.check_output(['git','rev-parse','--short','HEAD'],cwd=ROOT,text=True).strip()
counts=Counter(c.get('classname') for c in cases)
test_table='\n'.join(f'|{name}|{count}|0|' for name,count in sorted(counts.items()))
media_table='\n'.join(f"|{r['file']}|{r.get('metadata',{}).get('codec','—')}|{r.get('decoded_frames',0)}|{r.get('decoded_b_frames',0)}|{r['status']}|" for r in media)
export_table='\n'.join(f"|{r['format']}|{r['images']}|{r['objects']}|{r['splits']}|{r['status']}|" for r in exports[:4])
common=f'''执行日期：2026-10-13，Windows本机。P2最终自动化 {total} passed / 0 failed / 0 errors，P1回归 {p1} 项；证据 artifacts/p2/pytest.xml、pytest.log。源码本地 nvidia-first（报告生成时HEAD {commit}，最终提交见Git记录）。未经用户另行批准不得进入P3–P6。

所有视频为scripts/p2/make_samples.py自行生成：320×180、36帧、运动色块和文字；无第三方/工厂素材。人工测试几何只验证工具和格式，不代表选煤厂缺陷真值。真实厂区视频/标注质量/工业精度：NOT TESTED。'''
write('reports/P2_IMPLEMENTATION.md',f'''# P2 实施报告

状态：PASS（P2工程功能；工业场景未验收）。

{common}

复用ivad_app统一MainWindow、ApplicationServices、AsyncRunner、SQLite、JobService与日志。新增MediaService / AnnotationService / DatasetService、共享FileVideoSource及格式适配器；P2没有网络服务、第二套桌面入口、AI推理或训练。

COPY默认/REFERENCE、SHA256去重、后台导入、磁盘检查、失败状态、Missing引用重新定位；真实画面播放/暂停/速度/逐帧/跳转/捕获；实际PTS范围有限固定与变化抽帧，参数/任务/来源完整追溯。全部长操作后台执行，Qt信号回主线程。

真实鼠标矩形与多边形创建、移动、角点/顶点编辑、删除、撤销/重做、缩放/平移；视频/摄像头独立ROI、整帧/片段标签、标签库、审核、乐观修订与自动保存。源帧读取校验hash；保存失败阻止静默切换/退出。

人工已审核数据集检查、来源组划分、随机风险确认、精确重复去重/近重复警告、冻结图片与真值快照、版本查询、四种导出及hash清单。小来源组比例以实际统计为准，不伪造70/20/10。

Schema 0003新增业务表与任务payload/result，保留P1表及备份。完整模型见docs/DATABASE_SCHEMA.md。依赖仅给.venv-p1增加4个锁定包，P0未变。

截图 artifacts/p2/gui-annotation-native.png、gui-media-native.png、gui-dataset-native.png；额外100/200%截图及DPI JSON。原生DPR1.75；通过进程局部倍率得到DPR1.0/2.0，不修改Windows显示设置。截图目视发现属性拥挤后改为可滚动白色面板，已重新生成。

研发中发现并修复：list方法遮蔽类型注解；已有项目窗口表单初始化缺失；项目/视频切换旧回调污染；高DPI属性压缩；数据库提交异常导致目录未回退。最后全套通过。测试脚本初次证据生成缺少取消事件、测试末尾变量位置错误，修复后重跑，不计为未解决产品失败。

当前播放器不含音频；大规模/4K/长视频压力未测；多边形为简单单轮廓，洞/多部件/刷子Mask不支持。完整断电恢复、安装包、RTSP、AI辅助、工业报警和Intel独立验证不在P2。
''')
write('reports/P2_MEDIA_COMPATIBILITY.md',f'''# P2 媒体兼容性报告

{common}

|自制实际样本|实际codec|解码帧|B帧|结果|
|---|---|---:|---:|---|
{media_table}

每个正常文件实际解码36帧；随机定位与上一帧按实际PTS断言，不能把文件扩展名当codec保证。样本SHA256、时长、时间基、帧率、旋转、实际PTS差值记录在artifacts/p2/media-validation.json；样本文件在samples/，生成脚本可复现。H.264编码设bf=2、g=12，表内B帧数来自真实解码帧类型。

VFR实际PTS间隔不同；非整数标称30000/1001，实际微秒间隔33366/33367；90°矩阵旋转实际输出180×320。时间原点为流start_time或首帧PTS，拍摄日期保持未知。求帧索引只在从头顺序解码时可靠，seek后留空。整数微秒精度不等于知道现场绝对时钟。

Qt Multimedia 6.8.3真实QMediaPlayer+QVideoSink播放MP4：{qt['frames']}帧，时长{qt['duration_ms']}ms，错误{qt['errors']}，PASS。源Qt接口时间轴为毫秒；P2采用同一PyAV/FFmpeg解码器统一实际PTS播放与抽帧，避免两套定位语义。Qt探针记录qt-decode.json/log。

缺PTS、重复PTS、倒退PTS：明确拒绝，不用FPS补造。三种异常通过可控解码器故障注入测试；现实中缺PTS损坏容器尚未提供，NOT TESTED。损坏MP4样本实际拒绝，非直角旋转/未知时长明确不支持。

H.265、MJPEG、AV1、其他AVI/MOV组合、多视频轨、音频、超长/4K/网络录像及真实厂区来源：NOT TESTED。当前仅处理第一个视频轨，无音频，不宣称所有MP4/AVI兼容。
''')
write('reports/P2_ANNOTATION_VALIDATION.md',f'''# P2 标注验证报告

{common}

|类型|实际验证|状态|
|---|---|---|
|矩形框|Qt鼠标绘制、移动、角点调整、删除、撤销/重做、像素坐标|PASS|
|多边形|Qt逐点绘制/Enter完成、顶点移动、非法自交拒绝、真实GUI保存/重开|PASS|
|ROI矩形/多边形|独立文档/归一化、修订冲突、同摄像头跨媒体共享、视频隔离|PASS|
|整帧标签|正常/异常/未知、审核、正常负样本/未知禁止误导出|PASS|
|片段标签|实际视频范围、增改历史、逻辑删除与类别依赖|PASS|
|标签库|真实Qt新增中文类别、稳定UUID重命名、停用、删除引用限制|PASS|
|保存|350ms自动保存、CAS阻止覆盖、项目切换/关闭先保存、真实新窗口重开|PASS|
|DPI|原生175%、100%/200%实际画布各3项鼠标测试，1px容差|PASS|

坐标是解码并应用旋转后的图片原始像素；显示fit/zoom只是视图变换。ROI按视频显示坐标归一化，单独保留，不冒充训练目标。标注保存及每次修订均Human Generated；本阶段无AI预标注。几何验证有限值、边界、面积、顶点数量及自交。

真实完整GUI流程在test_p2_gui.py中执行：导入3录像→播放/暂停/速度/前后帧/跳转/捕获→后台抽帧→标签对话框新类别→鼠标绘制3个多边形→APPROVED自动保存→三组冻结/分割导出→新服务与窗口重开。没有用检测器输出替代人工真值。

只支持简单单轮廓多边形实例分割；像素画笔、洞/多部件Mask、跨人协作、工业审核质量/真实缺陷定位：NOT TESTED或未实现。默认类别类型存储在标签元数据，画布绘制类型由工具栏明确选择。
''')
write('reports/P2_DATASET_EXPORT.md',f'''# P2 数据集与导出报告

{common}

人工REVIEWED/APPROVED入选；DRAFT/REJECTED不入选。COPY冻结图片，标注修订/类别/媒体/ROI/片段快照写不可覆盖vNNNN；清单hash保存在SQLite。每次导出校验清单和图片，不修改原版本。

独立验证脚本scripts/p2/validate_outputs.py读回12个实际输出目录（3个DPI证据项目×4格式），全部PASS。每项目3张图片/3目标/3独立录像，真实train=1,val=1,test=1；精确hash无交叉，来源组不跨划分。以下为首个项目：

|格式|图片|目标|实际划分|结果|
|---|---:|---:|---|---|
{export_table}

YOLO Detection归一化中心宽高与原像素回算误差<1e-5；多边形转外接框明确警告，真多边形留native旁车。YOLO Segmentation为class+真实轮廓归一化坐标，含任何检测框时拒绝整个导出，不生成伪Mask或丢弃对象。data.yaml names类别与稳定UUID映射来自冻结版本，不随标签重命名变化。

COCO images/categories/annotations关系、真实polygon segmentation、bbox/area独立读回；Native保留所有原生语义、图片引用有效。四格式均附ivad_native.json和export_manifest.json，全部生成文件hash读回一致。无覆盖导出，目标带版本与UUID。

相同SHA256图片实际去重；dHash汉明距离≤4仅警告近重复。按camera或video分组，小组数导致比例近似，GUI显示真实统计。随机需明确风险选择；即使人工确认也保留泄漏警告。正常无目标导出空标签；异常/未知无目标不能当正常YOLO负样本。

新版本不会改变旧manifest字节；图片篡改拒绝导出；可捕获数据库提交失败实际回退.partial并回滚登记。强制断电的文件/数据库跨步骤窗口仍需人工一致性核对，未做电源故障实验。外部导出文件路径丢失会报告，程序不删除用户资源。

具备P3的合法工程输入：YES，已有真实可解析分割/检测文件和三份非空划分。具备选煤厂生产训练真值：NO，只有3张自制工程图片，不能评估模型泛化/工业准确率。未启动Ultralytics训练、未进行P3。
''')
write('reports/P2_TEST_RESULTS.md',f'''# P2 测试结果

最终结果：{total}通过，0失败，0错误，0跳过；主套耗时{suite.get('time')}秒。P1原有{p1}项回归保留通过，P2新增{total-p1}项。额外100/200%DPI画布各3项通过，作为同用例多环境复测，不重复计入主套总数。

{common}

|测试模块|通过|失败|
|---|---:|---:|
{test_table}

命令：.venv-p1/Scripts/python.exe -m pytest tests -q --junitxml=artifacts/p2/pytest.xml。PySide6实际Qt窗口/鼠标和真实解码，并非静态截图代替操作。测试数据在独立pytest临时目录；持久化截图/导出项目在artifacts/p2/gui-evidence-*，不使用用户厂区数据。

额外实际运行：QtMultimedia36帧播放；12份导出hash/坐标/COCO/native独立读回；8个媒体样本；三个DPI真实窗口截图；pip check无依赖错误；P0/P1历史文件/原有包版本只读比对PASS。详细JSON/XML/log位于artifacts/p2。

测试发现的问题已修复并重跑。最终主套无未解决失败；中间失败日志final-focused.log等保留研发痕迹，最终以pytest.xml为准。模拟磁盘不足、数据库提交失败和异常PTS标明故障注入；没有声称真实断电或现场坏码流试验通过。

未测试：真实厂区数据、工业标注质量、4K/小时录像、百万帧、大规模并发、恶意文件、全编码矩阵、断电恢复、Intel硬件、工业AI精度。P0训练/推理验收不在本轮重复执行；P1设备回归真实调用P0独立worker作CUDA张量检查，未升级GPU环境。
''')
write('reports/P2_ACCEPTANCE.md',f'''# P2 验收报告

**最终状态：PASS，限定于已批准P2工程功能与下述实际测试范围。**

{common}

统一GUI已经能以鼠标导入录像、实际播放定位、有限自动抽帧、人工框/多边形/独立ROI、整帧和片段标签、编辑类别、审核/自动保存、冻结数据集并导出四格式。完整GUI闭环包括关闭后新窗口重开，真实运行通过。

主测试{total}/0，P1回归{p1}/0；额外DPI各3/0；12实际导出回读全部PASS；MP4/AVI/MOV/MKV指定codec与VFR/非整数帧率/旋转/B帧实测；缺/异常PTS故障注入正确拒绝，损坏MP4实际拒绝。

P0/P1保护：preservation.json状态PASS；{len(preserved['p1_files'])}份历史文件hash一致，原P0根文件/报告hash与GPU包清单一致。P1既有依赖版本保持，只添加PyAV15.1.0/Pillow11.2.1/numpy2.2.5/PyYAML6.0.2。未修改ComfyUI、全局Python/CUDA或驱动。系统VPN未改，安装包均已成功，不存在待手动下载项。

数据安全：来源录像只读，UUID复制不会覆盖同名；取消保留已提交帧，Missing保留记录；Schema0002升级备份验证；人工修订/旧快照保留，篡改阻止导出，数据库提交异常回退暂存。不可捕获强杀/断电跨文件-数据库窗口、完整恢复GUI尚未验收。

未解决限制：真实选煤厂录像/工业真值NOT TESTED；当前无音频、简单单轮廓多边形、第一视频轨；H.265等未测编码不承诺；4K/长视频和海量帧性能未测；小来源组无法精确比例；摄像头编号由导入者维护。AI辅助/训练/工业检测报警/RTSP/Intel独立运行/P6安装包均未实现。

启动：双击根目录启动IVAD.cmd，沿用独立GUI环境；操作见docs/P2_USER_GUIDE.md。样例工程与4格式输出位于artifacts/p2/gui-evidence-native/，不作为工业数据。

P3建议：可由用户批准P3训练框架与合法工程样本接入验收；工业模型训练应先提供合法工厂视频、确认故障类别、人工审核足量多来源真值并评估许可。当前只有自制小样本，不建议宣称可以训练合格工业模型。本轮已停止在P2，未启动P3–P6。
''')
install=read('install.json');rows=[]
for item in install['install']:
    info=item['download_info'];meta=item['metadata'];rows.append(f"|{meta['name']}|{meta['version']}|{info['url']}|{info['archive_info']['hashes']['sha256']}|")
write('docs/P2_DEPENDENCIES.md','''# P2依赖与安装来源

仅追加到项目GUI .venv-p1，Python3.12.14；不新建第二套业务环境，不改变P0 GPU环境。requirements-p1.txt保持历史原状；P2入口requirements-p2.txt，全包锁定requirements-p2-lock.txt。pip check通过，所有P1原版本保持。来源官方PyPI files.pythonhosted.org；本次下载成功，无欠缺安装包。完整pip机器报告/安装日志保存在artifacts/p2/install.json及install.log。

|包|锁定版本|官方实际下载URL|SHA256|
|---|---|---|---|
'''+ '\n'.join(rows)+'''

PyAV wheel内置FFmpeg库，未安装系统ffmpeg/修改PATH；视频普通CPU解码属于P2非AI处理，GPU-only AI要求不变。PyAV/Pillow/NumPy/PyYAML和FFmpeg随包版权条款需要在未来正式安装/分发阶段保留与核对；此处不作商用法律结论。
''')
print('P2 reports written',total,'tests; P1',p1)
