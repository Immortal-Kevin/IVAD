"""SQLite仓库：每次操作独立Session，迁移前完整性检查/备份。"""
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from uuid import uuid4
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import sessionmaker
from alembic.config import Config
from alembic import command
from ivad_app.core.contracts import AppError

SCHEMA_HEAD = '0007'
MIGRATION_LOCK = threading.Lock()  # Alembic使用模块级代理，不并发运行迁移。

class Database:
    def __init__(self, path: Path, *, create: bool = False, revision: str = SCHEMA_HEAD):
        self.path = Path(path)
        self.lock = threading.RLock()
        needs_migration = True
        if not create and not self.path.is_file():
            raise AppError('DB_MISSING', '项目数据库不存在，请确认目录完整。')
        if self.path.exists():
            try:
                # 只读检查：错误或未知版本时不重建/覆盖用户数据库。
                uri = self.path.resolve().as_uri() + '?mode=ro'
                with sqlite3.connect(uri, uri=True) as raw:
                    if raw.execute('PRAGMA integrity_check').fetchone()[0] != 'ok':
                        raise AppError('DB_CORRUPT', '数据库完整性检查失败，已停止打开。')
                    current = raw.execute('SELECT version_num FROM alembic_version').fetchone()[0]
                if current not in {'0001', '0002', '0003', '0004', '0005', '0006', SCHEMA_HEAD}:
                    raise AppError('SCHEMA_UNSUPPORTED', '数据库版本不受支持，请使用兼容版本。')
                needs_migration = current != revision
                if current != revision:
                    backup = self.path.with_name(self.path.name + f'.migration-{uuid4().hex}.backup')
                    with sqlite3.connect(uri, uri=True) as src, sqlite3.connect(backup) as dst:
                        src.backup(dst)
            except AppError:
                raise
            except sqlite3.Error as exc:
                raise AppError('DB_INVALID', '数据库无法打开或格式无效，原文件未重建。') from exc
        self.engine = create_engine(URL.create('sqlite', database=str(self.path)), connect_args={'check_same_thread': False, 'timeout': 5})
        @event.listens_for(self.engine, 'connect')
        def connect(dbapi, _):
            dbapi.isolation_level = None
            dbapi.execute('PRAGMA foreign_keys=ON')
            dbapi.execute('PRAGMA busy_timeout=5000')
        @event.listens_for(self.engine, 'begin')
        def begin(connection):
            connection.exec_driver_sql('BEGIN')
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        try:
            cfg = Config()
            cfg.set_main_option('script_location', str(Path(__file__).parent / 'migrations'))
            if needs_migration:
                with MIGRATION_LOCK, self.engine.begin() as connection:
                    cfg.attributes['connection'] = connection
                    command.upgrade(cfg, revision)
        except Exception as exc:
            self.engine.dispose()
            raise AppError('DB_MIGRATION', '数据库迁移失败，已停止打开；请查看诊断日志及迁移备份。') from exc

    @contextmanager
    def transaction(self):
        with self.lock, self.sessions.begin() as session:
            yield session

    def integrity_check(self) -> str:
        with self.lock, self.engine.connect() as connection:
            value = connection.exec_driver_sql('PRAGMA integrity_check').scalar()
            if value != 'ok':
                raise AppError('DB_CORRUPT', '数据库完整性检查失败。')
            revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalar()
            if revision != SCHEMA_HEAD:
                raise AppError('SCHEMA_UNSUPPORTED', '数据库Schema版本不匹配。')
            return 'ok'

    def close(self) -> None:
        with self.lock:
            self.engine.dispose()
