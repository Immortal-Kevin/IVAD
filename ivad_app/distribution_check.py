"""Explicit packaged Qt end-to-end verification. Never runs on normal startup."""
import sys,json,time,hashlib,traceback,zipfile
from pathlib import Path
from fractions import Fraction
import av
from PIL import Image,ImageDraw
from PySide6.QtCore import Qt,QPoint,QPointF
from PySide6.QtWidgets import QApplication,QPushButton,QFileDialog,QMessageBox,QScrollArea
from PySide6.QtTest import QTest
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow
from ivad_app.gui.label_dialog import LabelDialog
from ivad_app.services.diagnostic_export import export_diagnostics
from ivad_app.core.contracts import AppError

def run(directory):
    directory=Path(directory).resolve();directory.mkdir(parents=True,exist_ok=True)
    result={'status':'RUNNING','frozen':bool(getattr(sys,'frozen',False)),'steps':[],'ai':'DISABLED','loaded_torch':False,'environment_scope':'same physical developer PC; isolated PATH/environment, not a clean VM'}
    app=QApplication.instance() or QApplication(sys.argv[:1]);services=None;window=None
    def wait(predicate,timeout=25):
        until=time.monotonic()+timeout
        while time.monotonic()<until:
            app.processEvents();QTest.qWait(25)
            if predicate():return
        raise AssertionError('Timed out waiting for GUI result')
    def click(parent,text):
        b=next(b for b in parent.findChildren(QPushButton) if b.text()==text)
        ancestor=b.parentWidget()
        while ancestor:
            if isinstance(ancestor,QScrollArea):ancestor.ensureWidgetVisible(b);QTest.qWait(80);break
            ancestor=ancestor.parentWidget()
        QTest.mouseClick(b,Qt.MouseButton.LeftButton);app.processEvents()
    def record(name):
        result['steps'].append({'operation':name,'status':'PASS'})
        (directory/'deployment-progress.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    try:
        assert result['frozen'],'Deployment check must run from actual EXE'
        root=Path(sys._MEIPASS);services=ApplicationServices(root,directory/'应用数据',lite=True)
        window=MainWindow(services,auto_probe=False);window.resize(1400,950);window.show();wait(lambda:not window.refresh_busy)
        record('standalone GUI startup without development Python PATH')
        window.grab().save(str(directory/'first-start.png'))
        sources=directory/'中文 素材';sources.mkdir(exist_ok=True)
        for name,codec in [('h264.mp4','libx264'),('hevc.mp4','libx265'),('sample.avi','mpeg4'),('sample.mov','libx264'),('sample.mkv','libx264')]:
            path=sources/name
            with av.open(str(path),'w') as output:
                stream=output.add_stream(codec,rate=10);stream.width=320;stream.height=180;stream.pix_fmt='yuv420p'
                if codec=='libx265':stream.options={'x265-params':'log-level=error:pools=1:frame-threads=1'}
                for i in range(40):
                    image=Image.new('RGB',(320,180),(30+i*3,40,70));ImageDraw.Draw(image).rectangle((20+i,40,120+i,140),fill='orange')
                    frame=av.VideoFrame.from_image(image);frame.pts=i;frame.time_base=Fraction(1,10)
                    for packet in stream.encode(frame):output.mux(packet)
                for packet in stream.encode():output.mux(packet)
        record('bundled FFmpeg generates and decodes five owned codec/container samples')
        original=hashlib.sha256((sources/'h264.mp4').read_bytes()).hexdigest()
        QFileDialog.getExistingDirectory=lambda *a,**k:str(directory)
        window.show_page('projects');p=window.pages['projects'];p.name.setText('跨电脑 中文 测试项目');p.site.setText('离线测试');click(p,'新建项目…')
        wait(lambda:services.projects.current is not None and not window.project_busy);project=services.projects.current.root;record('GUI create project and migrations 0005 on Chinese space path')
        window.show_page('media');m=window.p2.media;wait(lambda:not window.p2.refreshing)
        QFileDialog.getOpenFileNames=lambda *a,**k:([str(x) for x in sources.iterdir()], '')
        click(m,'批量导入录像…');wait(lambda:len(m.media_rows)==5 and not window.p2.tracked,60)
        assert all(r['state']=='READY' for r in m.media_rows);record('GUI batch import H264 HEVC AVI MOV MKV')
        original_row=next(i for i,r in enumerate(m.media_rows) if r['name']=='h264.mp4');original_id=m.media_rows[original_row]['id']
        m.table.selectRow(original_row);wait(lambda:m.selected_media and m.selected_media['id']==original_id and m.player.last_image is not None);QTest.qWait(300)
        click(m.player,'播放');wait(lambda:m.player.position_us>100000);click(m.player,'暂停')
        m.player.goto.setValue(1);click(m.player,'跳转');wait(lambda:m.player.position_us>=1000000);record('GUI playback pause and timeline seek')
        m.start.setValue(1);m.end.setValue(3);m.tabs.setCurrentIndex(3);m.clip_name.setText('故障片段 中文');click(m,'保存视频片段')
        wait(lambda:any(r['kind']=='CLIP' for r in m.media_rows),60);clip=next(r for r in m.media_rows if r['kind']=='CLIP')
        assert hashlib.sha256((sources/'h264.mp4').read_bytes()).hexdigest()==original;record('GUI save real CLIP; original hash unchanged')
        m.table.selectRow(next(i for i,r in enumerate(m.media_rows) if r['id']==clip['id']));wait(lambda:m.selected_media['id']==clip['id'] and m.player.last_image is not None);QTest.qWait(300)
        m.tabs.setCurrentIndex(0);click(m.player,'播放');wait(lambda:m.player.position_us>0);click(m.player,'暂停');record('new CLIP actually plays')
        m.tabs.setCurrentIndex(1);m.start.setValue(0);m.end.setValue(2);m.interval.setValue(.2);m.maximum.setValue(10)
        old_question=QMessageBox.question;QMessageBox.question=lambda *a,**k:QMessageBox.StandardButton.Yes
        click(m,'确认范围并后台抽帧');wait(lambda:len(services.media.frames(project))==10 and not window.p2.tracked,60);record('fixed sampling creates ten actual images')
        m.sampling.setCurrentIndex(1);m.start.setValue(0);m.end.setValue(2);m.maximum.setValue(4);m.sensitivity.setValue(.1);m.baseline.setChecked(True)
        before=len(services.media.frames(project));click(m,'确认范围并后台抽帧');wait(lambda:len(services.media.frames(project))>before and not window.p2.tracked,60);record('change sampling and baseline run')
        window.show_page('annotation');a=window.p2.annotation;wait(lambda:a.frame_id and not a.loading)
        a.media_filter.setCurrentIndex(a.media_filter.findData(clip['id']));wait(lambda:not a.loading and a.frame_id)
        dialog=LabelDialog(services.annotations,window.runner,project,window.p2.refresh,window);dialog.show();wait(lambda:len(dialog.records)>=5)
        click(dialog,'新类别');dialog.name.setText('测试故障');click(dialog,'保存类别');wait(lambda:any(r['name']=='测试故障' for r in dialog.records));label=next(r for r in dialog.records if r['name']=='测试故障');click(dialog,'关闭');wait(lambda:a.classes.findData(label['id'])>=0);a.classes.setCurrentIndex(a.classes.findData(label['id']));record('GUI fault label create and select')
        def point(x,y):return a.canvas.mapFromScene(QPointF(x,y))
        a.tool.setCurrentIndex(1);QTest.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point(20,30));QTest.mouseMove(a.canvas.viewport(),point(150,150));QTest.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point(150,150));assert any(x['kind']=='box' for x in a.canvas.shapes)
        a.tool.setCurrentIndex(2)
        for x,y in [(170,30),(250,40),(240,140)]:QTest.mouseClick(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point(x,y))
        QTest.keyClick(a.canvas,Qt.Key.Key_Return);assert any(x['kind']=='polygon' for x in a.canvas.shapes)
        a.tool.setCurrentIndex(3);QTest.mousePress(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point(10,10));QTest.mouseMove(a.canvas.viewport(),point(280,160));QTest.mouseRelease(a.canvas.viewport(),Qt.MouseButton.LeftButton,pos=point(280,160))
        a.review.setCurrentText('REVIEWED');a.image_tag.setCurrentIndex(2);click(a,'保存标注');wait(lambda:not a.saving and not a.dirty);fid=a.frame_id;record('GUI rectangle polygon ROI review and save')
        window.grab().save(str(directory/'annotation.png'))
        window.show_page('dataset');d=window.p2.dataset;wait(lambda:not window.p2.refreshing);d.name.setText('兼容性测试数据集');click(d,'全选已审核图片');click(d,'检查选择');wait(lambda:not window.p2.refreshing)
        click(d,'冻结新版本');wait(lambda:len(d.version_rows)>0 and not window.p2.tracked,60);d.versions.selectRow(0)
        before_jobs=len(services.jobs.history());click(d,'导出选中冻结版本…');wait(lambda:len(services.jobs.history())>before_jobs and any(j['kind']=='p2_export' and j['state']=='SUCCEEDED' for j in services.jobs.history()) and not window.p2.tracked,60)
        record('GUI dataset freeze and YOLO export')
        for device in ['cpu','nvidia:any','']:
            try:services.devices.require_gpu(device)
            except AppError:pass
            else:raise AssertionError('Lite accepted an AI device')
        result['loaded_torch']='torch' in sys.modules;assert not result['loaded_torch'] and 'onnxruntime' not in sys.modules;record('Lite denies AI with CPU/GPU selections; no torch or ORT loaded')
        QFileDialog.getSaveFileName=lambda *args,**kwargs:(str(directory/'diagnostics.zip'),'')
        window.show_page('logs');click(window.pages['logs'],'导出诊断ZIP…')
        wait(lambda:(directory/'diagnostics.zip').is_file())
        QMessageBox.question=old_question
        with zipfile.ZipFile(directory/'diagnostics.zip') as z:assert len(z.namelist())==4
        window.grab().save(str(directory/'diagnostics.png'))
        record('GUI diagnostic ZIP export contains allowlisted JSON only')
        window.close();wait(lambda:window.may_close);services.close();services=ApplicationServices(root,directory/'重新启动 应用数据',lite=True)
        window=MainWindow(services,auto_probe=False);window.show();wait(lambda:not window.refresh_busy);window.open_project(project);wait(lambda:services.projects.current and not window.project_busy);window.show_page('annotation');wait(lambda:window.p2.annotation.frame_id and not window.p2.annotation.loading)
        a=window.p2.annotation;a.media_filter.setCurrentIndex(a.media_filter.findData(clip['id']));wait(lambda:not a.loading and a.frame_id==fid and len(a.canvas.shapes)>=3);record('new GUI window reopens project with persisted annotations and ROI')
        window.close();wait(lambda:window.may_close);services.close();services=None;result['status']='PASS';return 0
    except Exception:
        result['status']='FAIL';result['error']=traceback.format_exc();return 1
    finally:
        (directory/'deployment-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        if services:services.close()
