import argparse, os, sys, traceback
from pathlib import Path
from PySide6.QtCore import QLockFile, QTimer, Qt, QStandardPaths
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QApplication, QMessageBox
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow
from ivad_app.services.logging_service import redact

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data-dir', type=Path)
    parser.add_argument('--smoke-seconds', type=float, default=0)
    args = parser.parse_args()
    root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parents[2]))
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
    app = QApplication(sys.argv[:1]); app.setApplicationName('IVAD Platform'); app.setOrganizationName('IVAD')
    from ivad_app.core.demo_policy import enabled
    if enabled():
        app.setApplicationName('IVAD Internal Demo')
    elif getattr(sys, 'frozen', False):
        app.setApplicationName('IVAD P2 Beta')
    data_dir = args.data_dir or (Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppLocalDataLocation)) / ('P37DLite' if enabled() else 'P2Beta') if getattr(sys, 'frozen', False) else root / 'runtime')
    services = None
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        instance = QLockFile(str(data_dir / 'application.lock'))
        if not instance.tryLock(0):
            QMessageBox.information(None, 'IVAD已运行', '同一应用数据目录已有运行实例，请切换到已打开的窗口。')
            return 0
        services = ApplicationServices(root, data_dir)
        window = MainWindow(services); window.show()
        if args.smoke_seconds: QTimer.singleShot(round(args.smoke_seconds * 1000), window.close)
        def exception_hook(kind, value, tb):
            services.logs.write('application', '应用发生异常，请复制诊断信息。', level='ERROR', trace=''.join(traceback.format_exception(kind, value, tb)))
            window.show_error('应用发生异常，请查看诊断日志。')
        sys.excepthook = exception_hook
        code = app.exec()
        services.close(); instance.unlock()
        return code
    except Exception:
        diagnostic = redact(traceback.format_exc())
        try:
            with (data_dir / 'startup-errors.log').open('a', encoding='utf-8') as log: log.write(diagnostic + '\n')
        except OSError: pass
        if services:
            services.logs.exception('application', '应用启动或关闭失败。')
            services.close()
        message = QMessageBox(QMessageBox.Icon.Critical, 'IVAD启动失败', '应用初始化失败。请检查目录权限、项目环境及runtime中的诊断日志；不会删除或重建已有数据库。')
        message.setDetailedText(diagnostic); message.exec()
        return 1

if __name__ == '__main__': raise SystemExit(main())
