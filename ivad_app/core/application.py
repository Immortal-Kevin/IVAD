"""应用组合根；GUI依赖服务，不直接执行CRUD或GPU操作。"""
from pathlib import Path
import sys
from ivad_app.storage.database import Database
from ivad_app.services.logging_service import LoggingService
from ivad_app.services.settings_service import SettingsService
from ivad_app.services.project_service import ProjectService
from ivad_app.services.device_service import DeviceService
from ivad_app.jobs.manager import JobService
from ivad_app.storage.project_store import ProjectStore
from ivad_app.services.media_service import MediaService
from ivad_app.services.annotation_service import AnnotationService
from ivad_app.services.dataset_service import DatasetService
from ivad_app.services.camera_service import CameraService
from ivad_app.services.model_service import ModelService
from ivad_app.services.training_service import TrainingService

class ApplicationServices:
    def __init__(self, root: Path, data_dir: Path | None = None, *, step_seconds: float = 0.1, lite: bool | None = None):
        self.root = Path(root)
        self.lite = bool(getattr(sys, 'frozen', False)) if lite is None else lite
        self.data_dir = Path(data_dir) if data_dir else self.root / 'runtime'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.db = Database(self.data_dir / 'catalog.sqlite', create=not (self.data_dir / 'catalog.sqlite').exists())
        self.logs = LoggingService(self.db, self.data_dir / 'logs')
        self.settings = SettingsService(self.db)
        self.projects = ProjectService(self.settings, self.logs)
        self.devices = DeviceService(self.db, self.settings, self.logs, self.root, lite=self.lite)
        self.jobs = JobService(self.db, self.logs, step_seconds=step_seconds)
        self.store = ProjectStore(self.projects)
        self.media = MediaService(self.store, self.logs)
        self.annotations = AnnotationService(self.store, self.media, self.logs)
        self.cameras = CameraService(self.store,self.logs)
        self.datasets = DatasetService(self.store, self.logs)
        self.models = ModelService(self.store,self.logs)
        self.training = TrainingService(self.store,self.datasets,self.models,self.devices,self.logs,self.root,self.settings)
        from ivad_app.services.offline_demo_service import OfflineDemoService
        self.offline = OfflineDemoService(self)
        self.jobs.register('p2_import', self.media.import_batch)
        self.jobs.register('p2_extract', self.media.extract)
        self.jobs.register('p2_clip', self.media.save_video_clip)
        self.jobs.register('p2_freeze', self.datasets.freeze)
        self.jobs.register('p2_export', self.datasets.export)
        if not self.lite:
            self.jobs.register('p3_train', self.training.train);self.jobs.register('p3_validate',self.training.validate)
            self.jobs.register('p35_offline',self.offline.run)
        self.logs.write('application', 'IVAD源码模式P3训练基础设施；P4–P6尚未实现。' if not self.lite else 'Lite不启用AI Worker。')
        self.closed = False

    def close(self):
        if self.closed: return
        self.jobs.close()
        self.projects.close()
        self.logs.write('application', '应用正常关闭，Worker与数据库已结束。')
        self.db.close(); self.closed = True
