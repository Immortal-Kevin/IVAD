"""结构化文件日志和SQLite索引；诊断先脱敏再持久化。"""
import json, re, threading, traceback
from pathlib import Path
from uuid import uuid4
from sqlalchemy import select
from ivad_app.core.contracts import utc_now
from ivad_app.storage.models import LogRecord

def redact(value: str) -> str:
    value = re.sub(r'(?i)(password|passwd|token|api[_-]?key|secret)(\s*[:=]\s*)[^\s,;]+', r'\1\2<redacted>', value)
    value = re.sub(r'\b[A-Za-z]:[\\/][^\n\"\']+', '<path>', value)
    value = re.sub(r'(?i)rtsp://[^\s]+', '<rtsp-redacted>', value)
    return value

class LoggingService:
    def __init__(self, db, directory: Path):
        self.db = db
        directory.mkdir(parents=True, exist_ok=True)
        self.path = directory / 'application.jsonl'
        self.lock = threading.Lock()

    def write(self, category: str, message: str, *, level: str = 'INFO', job_id: str | None = None, trace: str = '') -> None:
        values = dict(id=str(uuid4()), timestamp=utc_now(), level=level, category=category,
                      message=redact(message), job_id=job_id, trace=redact(trace))
        with self.lock:
            with self.path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(values, ensure_ascii=False) + '\n')
            try:
                with self.db.transaction() as session:
                    session.add(LogRecord(**values))
            except Exception:
                # 数据库故障时已保留文件证据，不递归写数据库日志。
                with self.path.open('a', encoding='utf-8') as stream:
                    stream.write(json.dumps({'timestamp': utc_now(), 'category': 'database', 'level': 'ERROR', 'message': '日志数据库索引写入失败', 'trace': redact(traceback.format_exc())}, ensure_ascii=False) + '\n')

    def exception(self, category: str, message: str, job_id: str | None = None):
        self.write(category, message, level='ERROR', job_id=job_id, trace=traceback.format_exc())

    def recent(self, job_id: str | None = None, limit: int = 150) -> list[dict]:
        query = select(LogRecord).order_by(LogRecord.timestamp.desc()).limit(limit)
        if job_id: query = query.where(LogRecord.job_id == job_id)
        with self.db.transaction() as session:
            return [{key: getattr(row, key) for key in ['timestamp', 'level', 'category', 'message', 'job_id', 'trace']} for row in session.scalars(query)]
