"""应用组合根；GUI依赖服务，不直接执行CRUD或GPU操作。"""
from pathlib import Path
from ivad_app.storage.database import Database
from ivad_app.services.logging_service import LoggingService
from ivad_app.services.settings_service import SettingsService
from ivad_app.services.project_service import ProjectService
from ivad_app.services.device_service import DeviceService
from ivad_app.jobs.manager import JobService

class ApplicationServices:
    def __init__(self, root: Path, data_dir: Path | None = None, *, step_seconds: float = 0.1):
        self.root = Path(root)
        self.data_dir = Path(data_dir) if data_dir else self.root / 'runtime'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database(self.data_dir / 'catalog.sqlite', create=not (self.data_dir / 'catalog.sqlite').exists())
        self.logs = LoggingService(self.db, self.data_dir / 'logs')
        self.settings = SettingsService(self.db)
        self.projects = ProjectService(self.settings, self.logs)
        self.devices = DeviceService(self.db, self.settings, self.logs, self.root)
        self.jobs = JobService(self.db, self.logs, step_seconds=step_seconds)
        self.logs.write('application', 'IVAD P1启动，后续阶段未实现。')
        self.closed = False

    def close(self):
        if self.closed: return
        self.jobs.close()
        self.projects.close()
        self.logs.write('application', '应用正常关闭，Worker与数据库已结束。')
        self.db.close(); self.closed = True
