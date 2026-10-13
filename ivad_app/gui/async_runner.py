"""后台服务调用经Qt信号回到GUI线程，不从线程修改QWidget。"""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
from PySide6.QtCore import QObject, Signal, Slot
from ivad_app.core.contracts import AppError

class AsyncRunner(QObject):
    completed = Signal(str, object, str)
    error = Signal(str)

    def __init__(self, logs, parent=None):
        super().__init__(parent)
        self.logs = logs
        self.pool = ThreadPoolExecutor(max_workers=3, thread_name_prefix='IVAD-Service')
        self.callbacks = {}
        self.completed.connect(self.finish)
        self.closing = False

    def run(self, operation, callback=None):
        if self.closing: return
        token = str(uuid4())
        self.callbacks[token] = callback
        def execute():
            try:
                result = operation()
                self.completed.emit(token, result, '')
            except Exception as exc:
                message = exc.message if isinstance(exc, AppError) else '操作失败，请查看诊断日志。'
                try: self.logs.exception('application', message)
                except OSError: pass  # 日志目录故障也必须把错误通知GUI。
                self.completed.emit(token, None, message)
        self.pool.submit(execute)
        return token

    @Slot(str, object, str)
    def finish(self, token, result, error):
        callback = self.callbacks.pop(token, None)
        if self.closing: return
        if error: self.error.emit(error)
        if callback: callback(result, error)

    def stop(self):
        self.closing = True
        self.pool.shutdown(wait=True, cancel_futures=True)
