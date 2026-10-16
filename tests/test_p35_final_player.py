import os,json
from pathlib import Path
from PySide6.QtCore import Qt,QPoint
from tests.test_p35_gui_redesign import open_real,select_8525
from tests.test_gui import close_window


def test_final_player_and_report_screens(qtbot,services):
    w,p=open_real(qtbot,services);out=Path(os.environ['IVAD_P35_GUI_EVIDENCE']);out.mkdir(parents=True,exist_ok=True);results=[]
    try:
        select_8525(qtbot,p);p.range_slider.set_range(7600000,8000000);p.use_cache();qtbot.waitUntil(lambda:p.player.last_image is not None,timeout=20000)
        path=p.run_path;position=p.player.position_us
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(200);p.tabs.setCurrentIndex(1);qtbot.wait(100)
            for mode in ['standard','focus']:
                if mode=='focus':p.focus_button.click();qtbot.wait(150);assert not w.sidebar.isVisible() and p.status_bar.isVisible() and p.focus_button.text()=='退出专注播放'
                pix=p.player.picture.pixmap();canvas=p.player.picture.size();fit=min(canvas.width()/1280,canvas.height()/720)
                assert abs(pix.width()/pix.height()-1280/720)<.02;assert abs(pix.height()-round(720*fit))<3
                assert p.player.slider.isVisible() and p.player.play_button.isVisible()
                results.append(dict(mode=mode,window=[w.width(),w.height()],dpr=w.devicePixelRatioF(),canvas=[canvas.width(),canvas.height()],image=[pix.width(),pix.height()],ratio=pix.width()/pix.height()))
                w.grab().save(str(out/f'{mode}-{width}.png'))
                if mode=='focus':qtbot.keyClick(p.focus_button,Qt.Key.Key_Escape);qtbot.wait(100);assert not p.focused and w.sidebar.isVisible() and p.player.position_us==position and p.run_path==path
        p.player.next.click();qtbot.waitUntil(lambda:p.player.position_us>position,timeout=10000);p.player.previous.click();qtbot.waitUntil(lambda:p.player.position_us==position,timeout=10000)
        qtbot.mousePress(p.player.slider,Qt.MouseButton.LeftButton,pos=QPoint(1,p.player.slider.height()//2));qtbot.mouseMove(p.player.slider,QPoint(p.player.slider.width()//2,p.player.slider.height()//2));p.player.slider.setValue(200);qtbot.mouseRelease(p.player.slider,Qt.MouseButton.LeftButton);qtbot.waitUntil(lambda:p.player.position_us>=200000,timeout=10000)
        p.player.goto.setValue(0);p.player.goto_button.click();qtbot.waitUntil(lambda:p.player.position_us==0,timeout=10000);p.player.play_button.click();qtbot.waitUntil(lambda:p.player.position_us>0,timeout=10000)
        if p.player.playing:p.player.play_button.click()
        assert not p.player.playing and 'EXPERIMENTAL' in p.status_bar.text() and 'LIMITED' in p.experiment_status.text()
        w.resize(1920,1080);p.tabs.setCurrentIndex(0);qtbot.wait(100);w.grab().save(str(out/'config.png'))
        for key in ['dashboard','projects','media','annotation','dataset','training','models','settings','devices']:
            w.show_page(key);qtbot.wait(500)
            if key=='media':
                page=w.pages[key];page.table.selectRow(next(i for i,r in enumerate(page.media_rows) if r['id']=='12a11464-0581-4bf1-8977-47fbcd5364b7'));qtbot.waitUntil(lambda:page.player.last_image is not None,timeout=15000)
            if key=='devices':
                w.pages[key].refresh_button.click();qtbot.waitUntil(lambda:not w.probe_busy,timeout=30000)
            if key=='annotation':
                page=w.pages[key];idx=page.camera_filter.findData('6cfade53-2a3d-4a78-b27b-415b567ab60d');page.camera_filter.setCurrentIndex(idx);qtbot.wait(150)
                for i in range(page.frames.count()):
                    page.frames.setCurrentRow(i);qtbot.wait(70)
                    if page.canvas.shapes:break
            if key=='training':
                page=w.pages[key]
                qtbot.waitUntil(lambda:not page.busy and bool(page.rows),timeout=15000);page.model.setCurrentText('yolo11n');page.runs.selectRow(next(i for i,r in enumerate(page.rows) if r['id'].startswith('7a01bcad')));qtbot.wait(100)
            w.grab().save(str(out/f'module-{key}.png'))
        (out/'player-results.json').write_text(json.dumps(results,indent=2),encoding='utf8');assert not services.jobs.history()
    finally:p.set_focus_playback(False);close_window(qtbot,w)
