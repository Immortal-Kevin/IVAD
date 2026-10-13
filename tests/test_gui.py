import time
from pathlib import Path
from PySide6.QtCore import Qt, QTimer
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton
from ivad_app.gui.main_window import MainWindow, DEV, PRODUCTION

def make_window(qtbot, services):
    window = MainWindow(services, auto_probe=False); qtbot.addWidget(window); window.show()
    qtbot.waitUntil(lambda: not window.refresh_busy, timeout=5000)
    return window

def close_window(qtbot, window):
    window.close(); qtbot.waitUntil(lambda: window.may_close, timeout=10000)

def test_navigation_workspaces_placeholders(qtbot, services):
    window = make_window(qtbot, services)
    for mode, items in [(0, DEV), (1, PRODUCTION)]:
        window.workspace.setCurrentIndex(mode)
        assert window.nav.count() == len(items)
        for row, (_, key) in enumerate(items):
            window.nav.setCurrentRow(row)
            assert window.stack.currentWidget() is window.pages[key]
            if hasattr(window.pages[key], 'status'):
                assert 'Not Implemented' in window.pages[key].status.text()
    close_window(qtbot, window)

def test_gui_project_create_save_reopen_and_error(qtbot, services, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog
    window = make_window(qtbot, services); window.show_page('projects'); page = window.pages['projects']
    page.name.setText('GUI中文选煤厂'); page.site.setText('东厂区'); page.description.setPlainText('真实GUI操作')
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *a, **k: str(tmp_path))
    qtbot.mouseClick(page.create_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000)
    assert services.projects.current.name == 'GUI中文选煤厂'
    root = services.projects.current.root; uuid = services.projects.current.id
    page.name.setText('保存后的中文名称')
    qtbot.mouseClick(page.save_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000)
    assert services.projects.current.name == '保存后的中文名称'
    qtbot.mouseClick(page.close_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000); assert services.projects.current is None
    monkeypatch.setattr(QFileDialog, 'getExistingDirectory', lambda *a, **k: root)
    qtbot.mouseClick(page.open_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000); assert services.projects.current.id == uuid
    qtbot.mouseClick(page.check_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000); assert '检查通过' in window.notice.text()
    window.open_project(str(tmp_path / 'missing'))
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000); assert '路径无效' in window.notice.text()
    assert services.projects.current.id == uuid
    close_window(qtbot, window)

def test_job_gui_responsive_cancel_logs_and_copy(qtbot, services):
    window = make_window(qtbot, services); window.show_page('jobs')
    services.jobs.step_seconds = 0.05
    ticks = []; timer = QTimer(window); timer.timeout.connect(lambda: ticks.append(time.monotonic())); timer.start(10)
    page = window.pages['jobs']; qtbot.mouseClick(page.submit_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: bool(services.jobs.history()), timeout=5000)
    job = services.jobs.history()[0]['id']
    qtbot.wait(160); window.workspace.setCurrentIndex(1); window.workspace.setCurrentIndex(0)
    assert len(ticks) >= 5
    assert services.jobs.get(job)['state'] == 'RUNNING'
    window.show_page('jobs')
    qtbot.waitUntil(lambda: page.jobs.rowCount() > 0, timeout=5000)
    page.jobs.selectRow(0)
    qtbot.mouseClick(page.cancel_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: services.jobs.get(job)['state'] == 'CANCELLED', timeout=5000)
    qtbot.mouseClick(page.log_button, Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: not window.refresh_busy, timeout=5000)
    qtbot.mouseClick(window.findChild(QPushButton, 'copy_diagnostics'), Qt.MouseButton.LeftButton)
    from PySide6.QtWidgets import QApplication
    assert 'IVAD' in QApplication.clipboard().text()
    close_window(qtbot, window)

def test_unsaved_changes_cancel_close(qtbot, services, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox
    window = make_window(qtbot, services)
    window.create_project(str(tmp_path), '保存的项目', '', '')
    qtbot.waitUntil(lambda: not window.project_busy, timeout=5000)
    window.pages['projects'].name.setText('尚未保存的名称')
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Cancel)
    window.close_project()
    assert services.projects.current.name == '保存的项目'
    window.close(); assert not window.is_closing and window.isVisible()
    monkeypatch.setattr(QMessageBox, 'question', lambda *a, **k: QMessageBox.StandardButton.Discard)
    close_window(qtbot, window)

def test_gui_settings_save_without_manual_config(qtbot, services):
    from PySide6.QtWidgets import QPushButton
    window = make_window(qtbot, services); window.show_page('settings')
    page = window.pages['settings']; page.worker.setText(str(services.root / 'missing-python.exe'))
    qtbot.mouseClick(window.findChild(QPushButton, 'save_settings'), Qt.MouseButton.LeftButton)
    qtbot.waitUntil(lambda: services.settings.preferences().get('worker_python') == page.worker.text(), timeout=5000)
    qtbot.waitUntil(lambda: not window.probe_busy and bool(services.devices.snapshot()), timeout=15000)
    assert services.devices.snapshot()[0].status == 'Error'
    close_window(qtbot, window)

def test_shutdown_error_can_retry_without_deleting_data(qtbot, services, monkeypatch):
    window = make_window(qtbot, services)
    original = services.close
    attempts = []
    def close_with_one_failure():
        attempts.append(True)
        if len(attempts) == 1: raise RuntimeError('controlled shutdown failure')
        original()
    monkeypatch.setattr(services, 'close', close_with_one_failure)
    window.close()
    qtbot.waitUntil(lambda: '重试' in window.notice.text(), timeout=5000)
    assert not window.is_closing and not services.closed
    assert services.db.path.is_file()
    close_window(qtbot, window)

def test_slow_device_probe_does_not_freeze_gui(qtbot, services, monkeypatch):
    window = make_window(qtbot, services)
    def slow_probe(): time.sleep(0.3); return []
    monkeypatch.setattr(services.devices, 'probe', slow_probe)
    ticks = []; timer = QTimer(window); timer.timeout.connect(lambda: ticks.append(1)); timer.start(10)
    window.probe_devices(); window.show_page('projects'); qtbot.wait(180)
    assert window.probe_busy and len(ticks) >= 8
    qtbot.waitUntil(lambda: not window.probe_busy, timeout=5000)
    close_window(qtbot, window)

def test_resizable_layout_and_screenshot(qtbot, services):
    window = make_window(qtbot, services)
    for width, height in [(1440, 900), (1080, 720)]:
        window.resize(width, height); qtbot.wait(80)
        assert window.pages['projects'].create_button.width() >= 80
        assert window.nav.width() >= 170
        assert window.stack.width() >= 600
    window.resize(1440, 900); window.show_page('projects'); qtbot.wait(100)
    window.grab().save(str(services.root / 'artifacts/p1/gui-projects.png'))
    window.workspace.setCurrentIndex(1); qtbot.wait(100)
    window.grab().save(str(services.root / 'artifacts/p1/gui-production.png'))
    close_window(qtbot, window)
