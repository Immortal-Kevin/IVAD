"""原子目录发布；稳定UUID清单、事务配置保存、打开一致性检查。"""
import json, os, re, threading, sqlite3
from pathlib import Path
from uuid import UUID, uuid4
from sqlalchemy import select
from ivad_app.core.contracts import AppError, ProjectInfo, utc_now
from ivad_app.storage.database import Database
from ivad_app.storage.models import ProjectRecord

class ProjectService:
    def __init__(self, settings, logs):
        self.settings, self.logs = settings, logs
        self.lock = threading.RLock()
        self.current: ProjectInfo | None = None
        self.db: Database | None = None

    @staticmethod
    def validate_fields(name: str, description: str, site: str):
        if not name.strip() or len(name.strip()) > 120:
            raise AppError('PROJECT_NAME', '项目名称不能为空且不超过120个字符。')
        if len(description) > 10000 or len(site) > 200:
            raise AppError('PROJECT_FIELDS', '描述或厂区信息过长。')

    def create(self, parent: str, name: str, description: str = '', site: str = '') -> ProjectInfo:
        with self.lock:
            self.validate_fields(name, description, site)
            base = Path(parent).resolve()
            if not base.is_dir():
                raise AppError('PROJECT_PATH', '存储目录不存在，请选择已有可写目录。')
            project_id = str(uuid4())
            # 目录名不依赖显示名称，名称修改不改变路径或身份。
            final = base / f'IVAD-{project_id}'
            staging = base / f'.ivad-staging-{project_id}'
            database = None
            try:
                staging.mkdir()
                database = Database(staging / 'project.sqlite', create=True)
                now = utc_now()
                with database.transaction() as session:
                    session.add(ProjectRecord(id=project_id, name=name.strip(), description=description, site=site, created_at=now, updated_at=now, revision=1))
                database.integrity_check()
                database.close(); database = None
                for directory in ['media', 'datasets', 'models', 'evidence']:
                    (staging / directory).mkdir()
                manifest = {'format': 'ivad-project', 'format_version': 1, 'id': project_id, 'database': 'project.sqlite'}
                temp = staging / 'project.json.tmp'
                with temp.open('w', encoding='utf-8') as stream:
                    json.dump(manifest, stream, ensure_ascii=False, indent=2)
                    stream.flush(); os.fsync(stream.fileno())
                temp.replace(staging / 'project.json')
                staging.rename(final)
            except Exception as exc:
                if database: database.close()
                # 失败时只处理本次创建的已知文件/空目录，绝不递归删除用户目录。
                if staging.exists():
                    for item in ['project.json', 'project.json.tmp', 'project.sqlite', 'project.sqlite-journal']:
                        (staging / item).unlink(missing_ok=True)
                    for item in ['media', 'datasets', 'models', 'evidence']:
                        folder = staging / item
                        if folder.is_dir(): folder.rmdir()
                    try: staging.rmdir()
                    except OSError: pass
                self.logs.exception('project', '新建项目失败，原有项目未删除。')
                raise AppError('PROJECT_CREATE', '项目创建失败，请检查目录权限与可用空间。') from exc
            return self.open(str(final))

    def _load(self, root: str) -> tuple[Database, ProjectInfo]:
        path = Path(root).resolve()
        if not path.is_dir() or path.name.startswith('.ivad-staging-'):
            raise AppError('PROJECT_MISSING', '项目路径无效或是未完成的暂存目录。')
        try:
            manifest = json.loads((path / 'project.json').read_text(encoding='utf-8-sig'))
            if manifest.get('format') != 'ivad-project' or manifest.get('format_version') != 1:
                raise ValueError('unsupported project format')
            project_id = str(UUID(manifest['id']))
            relative = Path(manifest['database'])
            dbpath = (path / relative).resolve()
            if relative.is_absolute() or dbpath.parent != path or relative.name != 'project.sqlite':
                raise ValueError('invalid database path')
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            raise AppError('PROJECT_MANIFEST', '项目配置格式错误或路径越界，已停止打开。') from exc
        if not dbpath.is_file(): raise AppError('DB_MISSING', '项目数据库不存在，请确认目录完整。')
        try:
            with sqlite3.connect(dbpath.as_uri() + '?mode=ro', uri=True) as raw:
                identifiers = raw.execute('SELECT id FROM projects').fetchall()
            if identifiers != [(project_id,)]:
                raise AppError('PROJECT_MISMATCH', '项目目录UUID与数据库记录不一致，已停止打开。')
        except sqlite3.Error as exc:
            raise AppError('DB_INVALID', '数据库无法读取，原有文件未重建。') from exc
        database = Database(dbpath)
        try:
            database.integrity_check()
            with database.transaction() as session:
                rows = list(session.scalars(select(ProjectRecord)))
                if len(rows) != 1 or rows[0].id != project_id:
                    raise AppError('PROJECT_MISMATCH', '项目目录UUID与数据库记录不一致，已停止打开。')
                row = rows[0]
                info = ProjectInfo(row.id, row.name, row.description, row.site, str(path), row.revision)
            return database, info
        except Exception:
            database.close(); raise

    def open(self, root: str) -> ProjectInfo:
        with self.lock:
            database, info = self._load(root)  # 验证成功才切换当前项目。
            try: self.settings.remember(info)
            except Exception:
                database.close(); raise
            self.close()
            self.db, self.current = database, info
            self.logs.write('project', f'项目打开成功，UUID={info.id}')
            return info

    def save(self, name: str, description: str, site: str, expected_revision: int) -> ProjectInfo:
        with self.lock:
            self.validate_fields(name, description, site)
            if not self.db or not self.current:
                raise AppError('PROJECT_NONE', '尚未打开项目。')
            with self.db.transaction() as session:
                row = session.get(ProjectRecord, self.current.id)
                if not row or row.revision != expected_revision:
                    raise AppError('PROJECT_CONFLICT', '项目已被其他操作修改，请重新打开后保存。')
                row.name, row.description, row.site = name.strip(), description, site
                row.revision += 1; row.updated_at = utc_now()
                info = ProjectInfo(row.id, row.name, row.description, row.site, self.current.root, row.revision)
            self.current = info
            self.settings.remember(info)
            self.logs.write('project', '项目配置已事务保存。')
            return info

    def check(self) -> dict:
        with self.lock:
            if not self.current: raise AppError('PROJECT_NONE', '尚未打开项目。')
            database, info = self._load(self.current.root)
            database.close()
            return {'status': 'PASS', 'uuid': info.id, 'schema': info.schema, 'integrity': 'ok'}

    def close(self):
        with self.lock:
            if self.db: self.db.close()
            self.db = None; self.current = None
