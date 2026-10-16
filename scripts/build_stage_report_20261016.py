"""Management report builder. Run with bundled document Python; no GPU imports."""
from pathlib import Path
import json,hashlib
from docx import Document
from docx.shared import Cm,Pt,RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.enum.text import WD_ALIGN_PARAGRAPH
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];E=ROOT/'artifacts/p35-final-20261016';OUT=ROOT/'reports/IVAD_Platform_P0-P3.5_阶段研发报告_20261016.docx'
d=Document();sec=d.sections[0];sec.page_width=Cm(21);sec.page_height=Cm(29.7);sec.top_margin=Cm(1.8);sec.bottom_margin=Cm(1.7);sec.left_margin=Cm(2.1);sec.right_margin=Cm(2.1)
for name,size in [('Normal',10.5),('Title',24),('Subtitle',15),('Heading 1',17),('Heading 2',12),('Caption',9)]:
 s=d.styles[name];s.font.name='Microsoft YaHei';s.font.size=Pt(size);s.font.color.rgb=RGBColor(0,0,0);s.font.italic=False;s.element.get_or_add_rPr().rFonts.set(qn('w:eastAsia'),'Microsoft YaHei');s.paragraph_format.space_after=Pt(6);s.paragraph_format.line_spacing=1.3
s=d.styles['Normal'];s.paragraph_format.space_after=Pt(6)
sec.header.paragraphs[0].text='IVAD Platform   阶段研发成果';sec.header.paragraphs[0].style='Caption'
f=sec.footer.paragraphs[0];f.alignment=WD_ALIGN_PARAGRAPH.RIGHT;f.add_run('研发验证版  |  ')
fld=OxmlElement('w:fldSimple');fld.set(qn('w:instr'),'PAGE');f._p.append(fld)
settings=d.settings.element;update=OxmlElement('w:updateFields');update.set(qn('w:val'),'true');settings.append(update)
sources=[];figcount=0

def para(text,bold=False):
 p=d.add_paragraph();p.add_run(text).bold=bold;return p

def heading(text):d.add_heading(text,1)
def page(title):d.add_page_break();heading(title)
def table(headers,rows,widths=None):
 t=d.add_table(rows=1,cols=len(headers));t.autofit=False
 for i,h in enumerate(headers):t.rows[0].cells[i].text=h
 for row in rows:
  cells=t.add_row().cells
  for i,x in enumerate(row):cells[i].text=str(x)
 for ri,row in enumerate(t.rows):
  trPr=row._tr.get_or_add_trPr();cant=OxmlElement('w:cantSplit');trPr.append(cant)
  if ri==0:repeat=OxmlElement('w:tblHeader');trPr.append(repeat)
  for ci,c in enumerate(row.cells):
   if widths:c.width=Cm(widths[ci])
   pr=c._tc.get_or_add_tcPr();sh=OxmlElement('w:shd');sh.set(qn('w:fill'),'DDEBF7' if ri==0 else ('F4F7FA' if ri%2==0 else 'FFFFFF'));pr.append(sh)
   borders=OxmlElement('w:tcBorders')
   for name in ['top','left','bottom','right']:
    e=OxmlElement('w:'+name);e.set(qn('w:val'),'single');e.set(qn('w:sz'),'4');e.set(qn('w:color'),'D9D9D9');borders.append(e)
   pr.append(borders)
   for p in c.paragraphs:
    p.paragraph_format.space_after=Pt(3);p.paragraph_format.space_before=Pt(3);p.paragraph_format.line_spacing=1.15
    for run in p.runs:run.font.size=Pt(9);run.bold=ri==0
 return t

def picture(path,caption,width=16.2,crop=False):
 global figcount
 path=Path(path);im=Image.open(path)
 if crop:
  w,h=im.size;box=(round(w*.15),round(h*.175),w-18,min(h-42,round(h*.62)))
  if path.name=='module-projects.png':box=(round(w*.15),round(h*.175),round(w*.88),round(h*.435))
  if path.name=='module-dashboard.png':box=(0,0,w,round(h*.20))
  if path.name=='module-annotation.png':box=(round(w*.15),round(h*.175),w-18,h-42);width=13
  im=im.crop(box)
  target=E/'report-images'/path.name;target.parent.mkdir(exist_ok=True);im.save(target);actual=target
 else:actual=path
 p=d.add_paragraph();p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.paragraph_format.space_after=Pt(2);p.add_run().add_picture(str(actual),width=Cm(width));p.paragraph_format.keep_with_next=True
 figcount+=1;cap=d.add_paragraph(f'图 {figcount}  {caption}','Caption');cap.paragraph_format.space_after=Pt(7)
 sources.append({'figure':figcount,'caption':caption,'source':str(path.relative_to(ROOT)),'embedded':str(actual.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'crop':crop})

G=E/'report-gui';F=E/'gui100'
d.add_paragraph('IVAD Platform 工业视觉异常检测平台','Title');d.add_paragraph('P0–P3.5 阶段研发成果报告','Subtitle');para('2026年10月16日');para('报告版本 1.0  |  软件源码版本 1.0.0-P3-Dev.2')
para('面向公司管理层',True);para('平台已初步打通现场录像、人工标注、数据集、GPU训练、模型注册和离线视频识别的工程链路。目前适合研发与演示验证，尚不属于正式工业报警产品。')
picture(F/'focus-1920.png','现有实验模型的离线视频回放，检测框为真实预测，尚未确认工业故障。',width=14.5)


page('成果摘要与目录')
para('已经做成：在同一中文软件中管理录像、截取片段、抽帧和人工标注；建立可追溯数据版本，完成NVIDIA GPU训练与模型注册，再用已有模型对录像执行离线检测。')
para('已经验证：RTX 5070 Ti上两种模型的基础训练与推理兼容性；8525压滤机YOLO11n实验训练、模型完整性、真实GPU检测及结果导出。')
para('尚未形成：独立工业准确率结论、实时摄像头报警、PLC联动或正式厂区部署。下一步应优先补充不同日期和工况的数据，明确现场故障及报警规则。')
d.add_heading('目录',2);p=d.add_paragraph();toc=OxmlElement('w:fldSimple');toc.set(qn('w:instr'),r'TOC \o "1-1" \h \z \u');p._p.append(toc)

page('一 项目背景与研发目标')
para('选煤厂监控录像能够保留现场过程，但连续人工盯屏难以覆盖长时段、多设备和短时故障。故障样本往往分散在长录像中，整理、标注和复核成本较高。')
para('IVAD首先将这些工作集中到统一软件，再通过可追溯的实验模型验证识别能力。未来目标是辅助发现落料口堵煤、压滤板破裂、皮带异物等问题，减少人工盯屏并自动保存异常证据；这些目标需要逐场景验证。')
heading('二 平台总体架构')
para('摄像头录像 → 导入与片段截取 → 自动抽帧 → 人工标注 → 数据集冻结 → GPU训练 → 模型版本管理 → 离线AI识别',True)
para('未来扩展：实时视频接入 → 连续帧与持续时间规则 → 报警证据 → 人工复核与运维平台对接。目前该扩展尚未开发。')
heading('三 P0–P3.5 阶段成果')
table(['阶段','实际成果','当前状态'],[
['P0','RTX 5070 Ti；YOLO26n/YOLO11n真实训练、推理和导出对照','本机工程验收通过'],['P1','统一中文工作空间；项目、任务、日志、设备和设置','基础平台验收通过'],['P2','录像复制/引用、片段、抽帧、摄像头关联、人工标注与正常/异常管理','源码功能验收通过'],['P3','数据集草稿/划分/冻结；GPU训练；模型仓库与版本追溯','工程链路通过'],['P3.5','真实模型离线视频识别、缓存回放、检测结果与导出','工程实验；GUI限制保留']], [1.5,11.3,3.8])
para('后续阶段不因本报告自动启动；软件打包继续冻结。',True)

page('四 软件功能板块图解')
d.add_heading('项目管理',2);para('创建和打开厂区项目，维护项目名称、厂区和说明。摄像头管理与项目表单分别位于独立标签页，共享当前项目。')
picture(G/'module-projects.png','项目管理，项目与摄像头分区维护。',crop=True)
d.add_heading('视频管理',2);para('录像可复制到项目，也可引用原文件；支持片段保存和指定范围抽帧。保留视频来源与时间关联，便于从图片追溯原录像。')
picture(G/'module-media.png','视频管理与抽帧，原始录像保持独立。',crop=True)

page('人工标注与数据准备')
d.add_heading('标注工作台',2);para('操作员绘制矩形或多边形并选择故障类别；正常画面可以无框保存。支持连续操作、剔除和恢复，保留修改历史；人工标注不等于AI已经学会识别。')
picture(G/'module-annotation.png','8525压滤机既有人工标注，仅展示，不新增或改写真值。',crop=True)
d.add_heading('数据集管理',2);para('筛选已保存图片，加入数据集草稿，再检查划分并冻结版本。冻结后保留来源与类别映射，勾选图片不等于已经加入数据集。')
picture(G/'module-dataset.png','数据集图片筛查与管理。',crop=True)

page('模型训练与版本管理')
d.add_heading('AI训练',2);para('简易和高级模式提供参数配置、数据预检、GPU后台任务、指标及日志。YOLO11n与YOLO26n已进行真实GPU工程测试，本报告案例沿用已训练的YOLO11n，不重复训练。')
picture(G/'module-training.png','训练记录7a01bcad已存在，截图未启动新训练。',crop=True)
d.add_heading('模型仓库',2);para('保存模型版本、类别、训练来源及实验级别。现有案例模型4a1c7df7为EXPERIMENTAL；注册成功不等于工业生产准入。')
picture(G/'module-models.png','模型仓库及版本追溯。',crop=True)

page('离线AI识别演示')
para('三Tab分别负责配置与视频选择、AI演示、检测详情与导出。选择模型和视频范围后，由GPU预处理生成真实检测结果；完成后自动载入缓存，不是实时摄像头推理。')
picture(F/'standard-1920.png','标准播放，保留模型/摄像头状态和实际阈值。',width=13)
para('专注播放临时收起导航和装饰，扩大画面；Esc退出后恢复界面和播放位置。检测详情支持回到对应帧，并导出带框视频、CSV/JSON和截图。')
picture(F/'focus-1920.png','专注播放，保持16比9，无拉伸或裁切。',width=13)

page('总览与运行环境')
d.add_heading('总览',2);para('汇总当前项目和基础工作状态，作为进入各模块的入口。生产监控、报警等后续页面仍为规划或占位。')
picture(G/'module-dashboard.png','总览页面。',width=14,crop=True)
d.add_heading('系统设置与设备后端',2);para('系统设置维护本地工作偏好；设备页检查NVIDIA后端及环境。Intel检测到硬件不等于训练和推理兼容性验收通过。')
picture(G/'module-devices.png','设备与后端页面，当前案例使用RTX 5070 Ti。',width=14,crop=True)
para('系统设置也已通过真实GUI读取；日常操作可经中文界面完成，不要求操作员编写代码。')

page('五 8525压滤机实际案例')
para('该案例验证了从人工数据到实验模型再到离线回放的工程链路。类别在历史数据中命名为“压滤版破裂”，本报告沿用原记录，不擅自改写标签。')
table(['项目','核实结果'],[['摄像头 / 数据集','8525压滤机 / 示例数据集 v1'],['冻结数据','200张图片，402个标注目标'],['训练 / 验证 / 独立测试','160 / 40 / 0张'],['训练 / 模型短版本','7a01bcad / 4a1c7df7'],['实际训练','YOLO11n，20轮，RTX 5070 Ti，800次优化器更新'],['模型级别','EXPERIMENTAL；LIMITED；非生产发布']], [5,11.6])
d.add_heading('原始记录中的验证指标',2)
table(['Precision','Recall','mAP50','mAP50–95'],[['0.9290','0.9211','0.9593','0.4269']], [4.1,4.1,4.2,4.2])
para('指标为该次训练验证记录，非独立测试或工业泛化准确率。Precision反映预测的准确程度，Recall反映样本中目标被发现的程度；mAP综合不同判定条件评估目标检测。')
para('LIMITED：主要来自同源录像，训练和验证画面相似，缺少独立Test集及独立人工复核。因此不能向现场承诺误报率、漏报率或生产识别率。',True)
para('模型权重完整性、GPU重载和PT/ONNX输出对照已通过；实际GPU计算节点也已核实。离线演示有背景低置信度框，仍需现场复核，不能当作已确认压滤板故障。')
para('性能须区分口径：纯模型前向曾测约13–15毫秒，但不含视频处理；整套离线演示含解码、传输和编码，处理速度明显更低，不承诺实时25或30帧/秒。')

page('六 当前限制与验证边界')
table(['事项','当前结论','下一步'],[['工业识别质量','独立性不足，误报/漏报未充分验证','补独立日期及故障样本'],['NVIDIA兼容范围','本机RTX 5070 Ti通过','其他GPU和跨机器单独验收'],['Intel GPU','历史阻断保留，未独立验收','后续分开测试训练与推理'],['实时输入及报警','RTSP、连续帧规则、生产报警未实现','明确规则后另行开发'],['部署和联动','局域网服务器、PLC联动未完成','现场架构及安全边界评审'],['商业许可','相关许可与再分发事项未闭合','生产或商用前专项核查'],['GUI及稳定性','旧combo自动化XFAIL和历史Qt问题保留','现场人工复核与长期稳定性测试']], [3.1,7.5,6])
para('本轮只改善P3.5播放器和报告。QMenu颜色已由用户人工确认正常，没有再次进行全局主题重构；历史QComboBox自动化限制不被抹去。')
para('真实训练记录曾显示epoch=21/计划20，而实际训练证据为20轮；这一历史显示差异仍保留。版本注册和有限软件测试不代表工业认证，也不等于已经具备生产报警能力。')
para('数据保护：本轮以开始时的最新原项目为基线，包括3次训练和3个模型。界面操作使用独立副本，不回退、覆盖或清理用户新增成果。')

page('七 未来P4–P10研发规划')
para('以下分开列出现有路线与建议方向，均未因本报告获得开发授权。现有SRS正式定义至P6；P7–P10尚无正式阶段定义。',True)
table(['阶段','现有路线或建议内容','定位'],[['P4','ROI识别范围、视频时序、连续帧与持续时间、报警逻辑及证据','SRS既定阶段，尚未启动'],['P5','AI辅助标注、人工复核、误识别样本回收及数据再版本化','SRS既定阶段，尚未启动'],['P6','集成测试、备份恢复、中文操作说明和Windows部署包','SRS既定阶段，打包仍冻结'],['P7–P10','RTSP多摄像头、厂区服务器、多模型调度、API/运维平台推送、跨GPU兼容和长期稳定性','建议路线，需另行定义及批准']], [2.1,10.7,3.8])
d.add_heading('优先推进的现场方向',2)
para('落料口堵煤：在已有标注能力基础上，补充堵煤发生前后、正常落料和扬尘遮挡录像，验证持续时间及误报边界。')
para('压滤板破裂：增加不同日期、不同压滤周期的正常与故障样本，先验证跨录像识别可靠性。')
para('皮带异物：收集多种异物尺寸、皮带速度、光照和遮挡情况，再评估识别及报警规则。当前未宣称已建成该场景检测模型。')
para('长期目标是减少人工盯屏、记录可追溯证据并对接运维平台。不能将目标写作已交付能力；尤其控制联动须另行安全评估，不擅自向PLC下发控制命令。')

page('八 下阶段研发计划与现场支持需求')
para('阶段总结：平台已初步建立“录像—人工数据—训练—模型版本—离线识别”的工程链路。本周工作在播放器修复与报告交付后停止，等待下一阶段明确授权。')
para('下阶段建议先补齐独立验证，再讨论工业报警开发和现场试运行。研发重点是可靠性与证据闭环，不以同源录像回放替代现场验证。',True)
table(['现场支持事项','建议提供内容','用途'],[['不同日期录像','同一摄像头跨日期、跨班次及不同工况录像','建立独立验证集'],['正常与故障样本','堵煤、压滤板破裂、异物及相似非故障场景；注明发生区间','减少误报和漏报'],['人工故障确认','由熟悉设备人员确认类型、区域与不确定画面','统一标注口径'],['测试摄像头','明确编号、位置、视角、分辨率及测试访问方式','评估后续视频接入'],['报警规则反馈','持续时间、严重程度、冷却/去重、允许误报及漏报边界','设计可解释规则'],['运维协同','接收人员、证据保存周期、运维平台接口需求','确定通知与记录流程']], [3.1,9,4.5])
para('建议组织一次研发与现场人员联合评审，确定优先摄像头、样本交付清单和验收口径；具体排期以资源与下一阶段授权为准。')
para('当前约束：不进入P4–P10，不重训已有模型，不制作EXE、Portable或安装包。',True)

OUT.parent.mkdir(exist_ok=True);d.core_properties.title='IVAD Platform 工业视觉异常检测平台阶段研发报告';d.core_properties.author='IVAD研发项目';d.core_properties.subject='P0–P3.5管理层阶段汇报';
for container in [d.element,d.styles.element]:
 for border in list(container.xpath('.//w:pBdr')):border.getparent().remove(border)
d.save(OUT)
(E/'report-figures.json').write_text(json.dumps(sources,ensure_ascii=False,indent=2),encoding='utf8');print(str(OUT));print('figures',figcount)
