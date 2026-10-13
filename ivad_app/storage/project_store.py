"""项目作用域快照：任务绑定提交时项目，不因GUI切换写入错误项目。"""
import json, hashlib, os
from contextlib import contextmanager
from pathlib import Path
from sqlalchemy import select
from ivad_app.core.contracts import AppError
from ivad_app.storage.database import Database
from ivad_app.storage.models import ProjectRecord

def file_hash(path: Path, check=None) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            if check: check()
            digest.update(chunk)
    return digest.hexdigest()

def safe_path(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()): raise AppError('PATH_TRAVERSAL', '资源路径越界，已停止操作。')
    return path

def atomic_json(path: Path, value: dict):
    temp = path.with_name(path.name + '.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush(); os.fsync(stream.fileno())
    temp.replace(path)

def row_dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}

class ProjectStore:
    def __init__(self, projects): self.projects = projects
    def root(self) -> str:
        if not self.projects.current: raise AppError('PROJECT_NONE', '请先打开项目。')
        return self.projects.current.root
    @contextmanager
    def open(self, root: str | None = None):
        path = Path(root or self.root()).resolve()
        try: manifest = json.loads((path / 'project.json').read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc: raise AppError('PROJECT_INVALID', '项目清单无法读取。') from exc
        if manifest.get('format')!='ivad-project' or manifest.get('format_version')!=1 or manifest.get('database')!='project.sqlite':raise AppError('PROJECT_INVALID','项目清单格式无效。')
        db = Database(safe_path(path,'project.sqlite'))
        try:
            with db.transaction() as session:
                row = session.get(ProjectRecord, manifest['id'])
                if not row: raise AppError('PROJECT_MISMATCH', '项目与数据库身份不一致。')
            yield path, db, row.id
        finally: db.close()
