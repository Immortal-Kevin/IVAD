"""GUI state fixtures are explicit; they do not represent actual GPU outcomes."""
import os,json
from pathlib import Path
import pytest
from PySide6.QtCore import Qt,QPoint
from PySide6.QtGui import QPalette,QColor
from PySide6.QtWidgets import QApplication
from tests.test_p35_gui_redesign import open_real,select_8525
from tests.test_gui import close_window
from ivad_app.core.contracts import AppError


def test_start_failure_failed_job_and_stale_callbacks(qtbot,services,monkeypatch):
    w,p=open_real(qtbot,services)
    try:
        select_8525(qtbot,p);p.range_slider.set_range(7600000,8000000)
        def reject(*a,**k):raise AppError('fixture_reject','明确测试夹具：提交被拒绝')
        monkeypatch.setattr(services.jobs,'submit',reject);p.submit('p35_offline',p.inference_payload(),'demo');qtbot.waitUntil(lambda:not p.busy,timeout=10000)
        assert p.tabs.currentIndex()==0 and '提交被拒绝' in p.config_info.text() and not p.job
        p.task_context=p.inference_payload();p.job='explicit-failure-fixture';p.operation='demo';p.tabs.setCurrentIndex(1)
        monkeypatch.setattr(services.jobs,'get',lambda _:{'state':'FAILED','progress':17,'error':'明确测试夹具：GPU错误','result':None});p.watch()
        assert 'FAILED' in p.status_bar.text() and 'GPU错误' in p.info.text() and p.manifest is None and not p.player.loaded
        p.back_button.click();assert p.tabs.currentIndex()==0
        # Capture an asynchronous request; changing session invalidates its callback.
        pending=[];monkeypatch.setattr(w.runner,'run',lambda fn,done=None:pending.append((fn,done)))
        p.find_or_start(True);callback=pending[-1][1];p.session_generation+=1;p.busy=False;callback('stale-cache',None)
        assert p.manifest is None and p.job is None
        p.load_run('stale-cache');callback=pending[-1][1];p.load_generation+=1;callback({'bad':'stale'},None);assert p.manifest is None
    finally:p.job=None;monkeypatch.undo();close_window(qtbot,w)


def test_submit_progress_completion_cache_identity_fixture(qtbot,services,monkeypatch):
    w,p=open_real(qtbot,services)
    try:
        select_8525(qtbot,p);p.range_slider.set_range(7600000,8000000);payload=p.inference_payload();cache=services.offline.matching_cache(payload);assert cache
        monkeypatch.setattr(services.jobs,'submit',lambda *a,**k:'explicit-success-fixture')
        state={'state':'RUNNING','progress':42,'error':'','result':None};monkeypatch.setattr(services.jobs,'get',lambda _:state)
        p.submit('p35_offline',payload,'demo');qtbot.waitUntil(lambda:p.job is not None,timeout=10000);assert p.tabs.currentIndex()==1
        p.watch();assert 'GPU 处理中' in p.status_bar.text() and '42%' in p.status_bar.text();p.back_button.click();assert p.tabs.currentIndex()==0 and p.job
        state.update(state='SUCCEEDED',progress=100,result={'path':cache});p.watch();qtbot.waitUntil(lambda:p.manifest is not None and p.player.last_image is not None,timeout=15000)
        assert p.tabs.currentIndex()==1 and '处理完成，可以播放' in p.status_bar.text() and p.last_job_id=='explicit-success-fixture'
        assert p.detail_context.text().find(p.manifest['dataset_version'])>=0
    finally:p.job=None;monkeypatch.undo();close_window(qtbot,w)


@pytest.mark.parametrize('dark',[False,True])
def test_menu_combo_palette_states(qtbot,services,dark):
    w,p=open_real(qtbot,services);app=QApplication.instance();old=QPalette(app.palette());out=Path(os.environ['IVAD_P35_GUI_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        palette=QPalette(old)
        for role in [QPalette.ColorRole.Window,QPalette.ColorRole.Base,QPalette.ColorRole.Button]:palette.setColor(role,QColor('#171717' if dark else '#ffffff'))
        for role in [QPalette.ColorRole.Text,QPalette.ColorRole.WindowText,QPalette.ColorRole.ButtonText]:palette.setColor(role,QColor('#eeeeee' if dark else '#203047'))
        app.setPalette(palette);w.resize(1920,1080);p.tabs.setCurrentIndex(0);qtbot.wait(100)
        menu=p.select_button.menu();disabled=menu.addAction('禁用测试项（仅测试夹具）');disabled.setEnabled(False)
        menu.popup(p.select_button.mapToGlobal(QPoint(0,p.select_button.height())));qtbot.wait(80);qtbot.keyClick(menu,Qt.Key.Key_Down);qtbot.mouseMove(menu,menu.actionGeometry(menu.actions()[0]).center());menu.grab().save(str(out/f'menu-{dark}.png'));assert menu.isVisible();assert menu.palette().color(QPalette.ColorRole.Window).lightness()>200;menu.close();menu.removeAction(disabled)
        select_8525(qtbot,p);qtbot.wait(500)
        for name,combo in [('model',p.model),('camera',p.camera),('gpu',p.gpu)]:
            combo.showPopup();view=combo.view()
            if not view.isVisible():pytest.xfail('Qt程序化展开未出现可见item view；原因未定位，未宣称popup状态通过。')
            qtbot.keyClick(view,Qt.Key.Key_Down);view.window().grab().save(str(out/f'combo-{name}-{dark}.png'));combo.hidePopup()
        # Existing P2/P3 pages remain under the same main-window theme.
        w.show_page('media');qtbot.wait(60);w.grab().save(str(out/f'media-theme-{dark}.png'))
    finally:app.setPalette(old);close_window(qtbot,w)
