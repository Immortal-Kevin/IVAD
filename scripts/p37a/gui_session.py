"""Launch the real main window against the test copy for operator/UI verification."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtWidgets import QApplication
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow
app=QApplication(sys.argv);s=ApplicationServices(ROOT,ROOT/'artifacts/p37a-20261016/gui-runtime')
s.projects.open(str(ROOT/'artifacts/p37a-20261016/project-copy'))
w=MainWindow(s,auto_probe=False);w.setWindowTitle('IVAD P3.7-A 独立测试项目');w.show();w.update_project_summary();w.show_page('training')
sys.exit(app.exec())
