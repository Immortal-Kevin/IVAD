"""P1串行非AI诊断队列；资源互斥接口用于以后GPU调度。"""
import queue, threading, traceback
from contextlib import contextmanager
from uuid import uuid4
from sqlalchemy import select, update
from ivad_app.core.contracts import AppError, utc_now, TERMINAL_STATES
from ivad_app.storage.models import JobRecord

class ResourceGate:
    def __init__(self):
        self.lock = threading.Lock(); self.resources: dict[str, threading.Lock] = {}

    @contextmanager
    def acquire(self, resource_id: str, cancel: threading.Event):
        if cancel.is_set(): raise AppError('JOB_CANCELLED', '任务已取消。')
        with self.lock: gate = self.resources.setdefault(resource_id, threading.Lock())
        while not gate.acquire(timeout=0.05):
            if cancel.is_set(): raise AppError('JOB_CANCELLED', '等待资源时任务取消。')
        try:
            if cancel.is_set(): raise AppError('JOB_CANCELLED', '任务已取消。')
            yield
        finally: gate.release()

class JobService:
    def __init__(self, db, logs, *, step_seconds: float = 0.1):
        self.db, self.logs, self.step_seconds = db, logs, step_seconds
        self.queue = queue.Queue()
        self.events: dict[str, threading.Event] = {}
        self.lock = threading.RLock()
        self.gate = ResourceGate()
        self.stopping = False
        with self.db.transaction() as session:
            recovered = session.execute(update(JobRecord).where(JobRecord.state.in_(['RUNNING', 'QUEUED'])).values(state='INTERRUPTED', error='应用上次退出后Worker已丢失，请重新提交。', updated_at=utc_now())).rowcount
        if recovered: self.logs.write('job', f'已将{recovered}个丢失Worker的任务恢复为INTERRUPTED。', level='WARNING')
        self.thread = threading.Thread(target=self._worker, name='IVAD-P1-Jobs', daemon=False)
        self.thread.start()

    def submit(self, kind: str = 'diagnostic', project_id: str | None = None) -> str:
        if kind not in {'diagnostic', 'diagnostic_failure'}:
            raise AppError('JOB_UNSUPPORTED', '当前P1仅支持非AI诊断任务，训练/推理尚未实现。')
        with self.lock:
            if self.stopping: raise AppError('JOB_SHUTDOWN', '应用正在关闭，不能创建任务。')
            job_id = str(uuid4()); now = utc_now()
            with self.db.transaction() as session:
                session.add(JobRecord(id=job_id, project_id=project_id, kind=kind, state='QUEUED', progress=0, created_at=now, updated_at=now, error=''))
            self.events[job_id] = threading.Event()
            self.logs.write('job', '非AI诊断任务已排队。', job_id=job_id)
            self.queue.put(job_id)
            return job_id

    def _change(self, job_id: str, state: str | None = None, progress: int | None = None, error: str = ''):
        with self.db.transaction() as session:
            row = session.get(JobRecord, job_id)
            if not row or row.state in TERMINAL_STATES: return
            if state: row.state = state
            if progress is not None: row.progress = progress
            row.error = error; row.updated_at = utc_now()

    def _worker(self):
        while True:
            job_id = self.queue.get()
            if job_id is None:
                self.queue.task_done(); return
            event = self.events[job_id]
            try:
                if event.is_set():
                    self._change(job_id, 'CANCELLED'); continue
                self._change(job_id, 'RUNNING')
                self.logs.write('job', '诊断开始：可取消的计时与进度测试，不执行AI。', job_id=job_id)
                row = self.get(job_id)
                for step in range(1, 31):
                    if event.wait(self.step_seconds): break
                    if row['kind'] == 'diagnostic_failure' and step == 6:
                        raise RuntimeError('P1 controlled diagnostic failure')
                    self._change(job_id, progress=round(step * 100 / 30))
                state = 'CANCELLED' if event.is_set() else 'SUCCEEDED'
                with self.lock: self._change(job_id, state)
                self.logs.write('job', '任务已取消。' if state == 'CANCELLED' else '非AI诊断成功。', job_id=job_id)
            except Exception:
                self._change(job_id, 'FAILED', error='诊断任务发生可控异常，请查看详细日志。')
                self.logs.exception('job', '任务失败，队列将继续处理后续任务。', job_id)
            finally:
                self.queue.task_done()

    def cancel(self, job_id: str):
        with self.lock:
            event = self.events.get(job_id)
            if not event or self.get(job_id)['state'] in TERMINAL_STATES: return
            event.set()
            if self.get(job_id)['state'] == 'QUEUED': self._change(job_id, 'CANCELLED')
            self.logs.write('job', '已请求取消任务。', job_id=job_id)

    def get(self, job_id: str) -> dict:
        with self.db.transaction() as session:
            row = session.get(JobRecord, job_id)
            if not row: raise AppError('JOB_MISSING', '任务不存在。')
            return {key: getattr(row, key) for key in ['id', 'kind', 'project_id', 'state', 'progress', 'created_at', 'updated_at', 'error']}

    def history(self) -> list[dict]:
        with self.db.transaction() as session:
            rows = session.scalars(select(JobRecord).order_by(JobRecord.created_at.desc()).limit(200))
            return [{key: getattr(row, key) for key in ['id', 'kind', 'state', 'progress', 'created_at', 'updated_at', 'error']} for row in rows]

    def request_shutdown(self):
        with self.lock:
            if self.stopping: return
            self.stopping = True
            for event in self.events.values(): event.set()
            self.queue.put(None)

    def close(self):
        self.request_shutdown()
        self.thread.join(timeout=10)
        if self.thread.is_alive(): raise AppError('JOB_SHUTDOWN', '后台任务尚未结束，数据库暂不关闭。')
