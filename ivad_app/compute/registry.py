"""Worker注册入口：NVIDIA当前实现；Intel独立后端由后续阶段注册。"""
from typing import Callable
from ivad_app.core.contracts import AppError, ComputeWorker

class WorkerRegistry:
    def __init__(self): self.factories: dict[str, Callable[..., ComputeWorker]] = {}

    def register(self, backend: str, factory: Callable[..., ComputeWorker]):
        if backend not in {'nvidia_cuda', 'intel_xpu', 'intel_openvino'}:
            raise AppError('BACKEND_UNSUPPORTED', '不支持该AI后端；禁止注册CPU-only AI。')
        self.factories[backend] = factory

    def create(self, backend: str, *args, **kwargs) -> ComputeWorker:
        if backend not in self.factories:
            raise AppError('BACKEND_NOT_IMPLEMENTED', '该Worker后端尚未实现或注册。')
        return self.factories[backend](*args, **kwargs)
