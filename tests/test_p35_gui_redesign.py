import json,os
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QPoint,QTimer
from PySide6.QtWidgets import QApplication,QListWidget,QDialog,QFileDialog,QMessageBox
from ivad_app.gui.time_range_slider import TimeRangeSlider
from tests.test_gui import make_window,close_window
from tests.test_p2_media import sample_videos

def test_dual_range_drag_keyboard_bounds(qtbot):
    r=TimeRangeSlider();qtbot.addWidget(r);r.resize(700,40);r.configure(20000000,40000);r.show()
    qtbot.mousePress(r,Qt.MouseButton.LeftButton,pos=QPoint(round(r.x_for(r.end)),20));qtbot.mouseMove(r,QPoint(round(r.x_for(15000000)),20));qtbot.mouseRelease(r,Qt.MouseButton.LeftButton,pos=QPoint(round(r.x_for(15000000)),20));assert abs(r.end-15000000)<30000
    r.active=0;r.setFocus();r.set_range(1000000,15000000);qtbot.keyClick(r,Qt.Key.Key_Right);assert r.start==1001000;qtbot.keyClick(r,Qt.Key.Key_Space);assert r.active==1
    r.set_range(19000000,200,handle=0);assert r.end-r.start>=40000 and 0<=r.start<r.end<=20000000
    r.set_range(-3000,30000000);assert r.start==0 and r.end==20000000

def open_real(qtbot,services):
    location=os.environ.get('IVAD_P35_GUI_COPY')
    if not location:pytest.skip('Independent real project copy explicitly required')
    services.projects.open(location);services.devices.probe();w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');p=w.pages['offline'];qtbot.waitUntil(lambda:not p.busy and len(p.model_rows)>0,timeout=15000);return w,p

def select_8525(qtbot,p):
    def choose():
        dialog=QApplication.activeModalWidget();items=dialog.findChild(QListWidget)
        for i in range(items.count()):
            if items.item(i).data(Qt.ItemDataRole.UserRole)=='12a11464-0581-4bf1-8977-47fbcd5364b7':items.setCurrentRow(i);dialog.accept();return
        dialog.reject()
    QTimer.singleShot(50,choose);p.select_button.menu().actions()[0].trigger();qtbot.waitUntil(lambda:p.preview.last_image is not None,timeout=15000)

def test_real_three_tabs_preview_history_export(qtbot,services,monkeypatch):
    w,p=open_real(qtbot,services);out=Path(os.environ['IVAD_P35_GUI_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        select_8525(qtbot,p);assert '8525' in p.camera.currentText() and p.model.currentData().startswith('4a1c7df7')
        assert [p.tabs.tabText(i) for i in range(3)]==['识别配置与视频选择','AI 识别演示','检测详情与导出'];assert p.tabs.currentIndex()==0
        p.range_slider.set_range(7600000,8000000);p.preview_seek(7600000);qtbot.waitUntil(lambda:p.preview.position_us>=7600000,timeout=15000)
        before=p.configuration_fingerprint();p.use_cache();qtbot.waitUntil(lambda:p.manifest is not None and p.player.last_image is not None,timeout=20000)
        assert p.tabs.currentIndex()==1 and '已加载缓存' in p.status_bar.text() and 'EXPERIMENTAL' in p.status_bar.text() and 'LIMITED' in p.experiment_status.text() and '0.25' in p.status_bar.text();assert not services.jobs.history()
        p.back_button.click();assert p.tabs.currentIndex()==0 and p.configuration_fingerprint()==before
        old=p.manifest;p.confidence.setValue(.4);assert '当前配置与已有缓存不一致' in p.cache_state.text();assert '0.25' in p.status_bar.text() and p.manifest is old
        p.use_cache();qtbot.waitUntil(lambda:not p.busy,timeout=15000);assert p.tabs.currentIndex()==0 and '没有完全匹配' in p.config_info.text() and not services.jobs.history()
        p.tabs.setCurrentIndex(2);p.show_all.setChecked(True);assert p.results.rowCount()==len(old['frames']);r=p.result_rows[1][0];p.results.selectRow(1);qtbot.waitUntil(lambda:p.tabs.currentIndex()==1 and abs(p.player.position_us-r['cache_time_us'])<1000,timeout=15000)
        p.player.next.click();qtbot.waitUntil(lambda:p.player.position_us>r['cache_time_us'],timeout=10000);p.player.goto.setValue(0);p.player.goto_button.click();qtbot.waitUntil(lambda:p.player.position_us==0,timeout=10000)
        geometry=[]
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(150)
            for tab in range(3):
                p.tabs.setCurrentIndex(tab);qtbot.wait(80);assert w.grab().save(str(out/f'tab-{tab+1}-{width}.png'))
            p.tabs.setCurrentIndex(1);pix=p.player.picture.pixmap();assert pix and abs(pix.width()/pix.height()-1280/720)<.02
            assert p.player.picture.geometry().bottom()<p.player.slider.geometry().top();assert p.status_bar.isVisible() and p.back_button.isVisible()
            geometry.append(dict(actual=[w.width(),w.height()],dpr=w.devicePixelRatioF(),image=[pix.width(),pix.height()],preview=[p.preview.picture.width(),p.preview.picture.height()]))
        p.tabs.setCurrentIndex(2);monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(out));p.export_button.click();qtbot.waitUntil(lambda:bool(list(out.glob('IVAD-offline-demo-*'))),timeout=15000);p.shot_button.click();qtbot.waitUntil(lambda:bool(list(out.glob('IVAD-demo-frame-*.png'))),timeout=15000)
        (out/'geometry.json').write_text(json.dumps(geometry,indent=2),encoding='utf8');assert not services.jobs.history()
    finally:close_window(qtbot,w)

def test_real_short_gpu_exact_cache_reuse(qtbot,services):
    w,p=open_real(qtbot,services);out=Path(os.environ['IVAD_P35_GUI_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        select_8525(qtbot,p);p.range_slider.set_range(7640000,7800000);qtbot.waitUntil(lambda:p.start_button.isEnabled(),timeout=10000);p.start_button.click()
        qtbot.waitUntil(lambda:p.job is not None,timeout=15000);assert p.tabs.currentIndex()==1;p.back_button.click();assert p.job and p.tabs.currentIndex()==0;p.tabs.setCurrentIndex(1);qtbot.waitUntil(lambda:p.manifest is not None or 'FAILED' in p.info.text(),timeout=60000);assert p.manifest,p.info.text();assert len(p.manifest['frames'])==4 and p.manifest.get('identity')
        path=p.run_path;qtbot.waitUntil(lambda:not p.busy and p.job is None,timeout=10000);jobs=len(services.jobs.history());assert jobs==1
        p.start();qtbot.waitUntil(lambda:not p.busy,timeout=15000);qtbot.wait(200);assert p.run_path==path and len(services.jobs.history())==jobs
        p.confidence.setValue(.8);p.use_cache();qtbot.waitUntil(lambda:not p.busy,timeout=15000);assert '没有完全匹配' in p.config_info.text() and len(services.jobs.history())==jobs
        p.confidence.setValue(.25);p.use_cache();qtbot.waitUntil(lambda:not p.busy,timeout=15000);qtbot.wait(200);assert p.run_path==path
        p.confidence.setValue(.8);p.range_slider.set_range(7600000,8400000);p.start();qtbot.waitUntil(lambda:p.job is not None,timeout=15000);cancel_id=p.job;qtbot.waitUntil(lambda:services.jobs.get(cancel_id)['progress']>0 and p.cancel_button.isEnabled(),timeout=30000);p.cancel_button.click();qtbot.waitUntil(lambda:p.job is None,timeout=20000);assert services.jobs.get(cancel_id)['state']=='CANCELLED';services.offline.load(path)
        (out/'gpu-reuse.json').write_text(json.dumps(dict(path=path,frames=len(p.manifest['frames']),jobs=jobs,cancel_job=cancel_id,cancel_state='CANCELLED',identity=p.manifest['identity'],gpu=p.manifest['gpu'],peak=p.manifest['gpu_peak_bytes'],seconds=p.manifest['seconds']),ensure_ascii=False,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)

@pytest.mark.parametrize('container,codec',[('mp4','libx264'),('avi','mjpeg'),('matroska','libx264'),('mov','libx264'),('mpegts','libx264'),('mp4-m4v','libx264'),('matroska-hevc','libx265')])
def test_external_formats_gui_probe_preview(qtbot,services,tmp_path,monkeypatch,container,codec):
    import av
    from PIL import Image
    from fractions import Fraction
    if codec not in av.codecs_available:pytest.skip('Encoder unavailable; format/codec NOT TESTED')
    suffix={'matroska':'mkv','mpegts':'ts','mp4-m4v':'m4v','matroska-hevc':'mkv'}.get(container,container);source=tmp_path/('owned-demo-'+codec+'.'+suffix)
    try:
        with av.open(str(source),'w',format={'mp4-m4v':'mp4','matroska-hevc':'matroska'}.get(container,container)) as output:
            stream=output.add_stream(codec,rate=25);stream.width=320;stream.height=180;stream.pix_fmt='yuvj420p' if codec=='mjpeg' else 'yuv420p'
            if codec=='libx265':stream.options={'x265-params':'log-level=error'}
            for i in range(12):
                frame=av.VideoFrame.from_image(Image.new('RGB',(320,180),(20+i*10,40,60)));frame.pts=i;frame.time_base=Fraction(1,25)
                for packet in stream.encode(frame):output.mux(packet)
            for packet in stream.encode():output.mux(packet)
    except Exception as exc:pytest.skip('Test encoder cannot create sample; NOT TESTED: '+str(exc))
    project=services.projects.create(str(tmp_path),'格式解码测试');w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');p=w.pages['offline']
    try:
        qtbot.waitUntil(lambda:not p.busy and p.select_button.isEnabled(),timeout=10000);monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(source),''));p.select_button.menu().actions()[1].trigger();qtbot.waitUntil(lambda:p.preview.last_image is not None or 'FAILED' in p.info.text(),timeout=15000);assert p.preview.last_image is not None,p.info.text()
        assert codec.replace('libx264','h264').replace('libx265','hevc') in p.media_info.text();assert p.preview.last_image.width()==320
        p.preview.goto.setValue(.2);p.preview.goto_button.click();qtbot.waitUntil(lambda:p.preview.position_us>=200000,timeout=10000);assert not any(r['kind']=='p35_offline' for r in services.jobs.history())
        # No filename-based camera assignment; selecting an existing camera is GUI-only.
        media=services.media.get(p.media.currentData());assert media['camera_id'] is None
        out=Path(os.environ.get('IVAD_P35_GUI_EVIDENCE',str(tmp_path/'evidence')));out.mkdir(parents=True,exist_ok=True);(out/f'format-{container}.json').write_text(json.dumps(dict(container=container,codec=codec,probe=p.media_info.text(),preview_pts=p.preview.info.text(),status='PASS'),ensure_ascii=False,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)

def test_invalid_video_import_no_gui_crash(qtbot,services,tmp_path,monkeypatch):
    services.projects.create(str(tmp_path),'坏文件测试');bad=tmp_path/'bad.avi';bad.write_bytes(b'not an encoded video');w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');p=w.pages['offline']
    try:
        qtbot.waitUntil(lambda:not p.busy,timeout=10000);monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(bad),''));p.import_video();qtbot.waitUntil(lambda:p.job is not None,timeout=10000);qtbot.waitUntil(lambda:p.job is None,timeout=15000);assert 'FAILED' in p.info.text() or 'failed' in p.info.text();assert bad.read_bytes()==b'not an encoded video' and not p.preview.loaded
    finally:close_window(qtbot,w)
