"""实际Qt窗口截图及DPI证据；所有测试数据存放在artifacts/p1。"""
import os, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow

app = QApplication([])
services = ApplicationServices(ROOT, ROOT / 'artifacts/p1/gui-evidence')
window = MainWindow(services, auto_probe=True); window.show()
out = ROOT / 'artifacts/p1'
label = os.environ.get('IVAD_EVIDENCE_LABEL', 'native')

def capture():
    if window.probe_busy or not services.devices.snapshot():
        QTimer.singleShot(100, capture); return
    window.show_page('devices'); app.processEvents()
    window.grab().save(str(out / f'gui-devices-{label}.png'))
    window.show_page('projects'); app.processEvents()
    window.grab().save(str(out / f'gui-projects-{label}.png'))
    window.workspace.setCurrentIndex(1); app.processEvents()
    window.grab().save(str(out / f'gui-production-{label}.png'))
    screen = app.primaryScreen()
    evidence = {'device_pixel_ratio': screen.devicePixelRatio(), 'logical_dpi': screen.logicalDotsPerInch(), 'screen': [screen.geometry().width(), screen.geometry().height()], 'window': [window.width(), window.height()], 'nav_width': window.nav.width(), 'center_width': window.stack.width(), 'visible': window.isVisible()}
    (out / f'gui-dpi-{label}.json').write_text(json.dumps(evidence, indent=2), encoding='utf-8')
    QTimer.singleShot(100, window.close)
QTimer.singleShot(200, capture)
QTimer.singleShot(110000, window.close)
app.exec()
