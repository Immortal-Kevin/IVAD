"""独立于Qt/数据库的v1服务契约与错误。"""
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Protocol, Any

API_VERSION = 'v1'

def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec='milliseconds')

class AppError(Exception):
    def __init__(self, code: str, message: str):
        self.code, self.message = code, message
        super().__init__(message)

@dataclass(frozen=True)
class ProjectInfo:
    id: str
    name: str
    description: str
    site: str
    root: str
    revision: int
    schema: str = '0005'

    def to_dict(self) -> dict:
        return asdict(self)

@dataclass(frozen=True)
class DeviceInfo:
    id: str
    name: str
    backend: str
    hardware_detected: bool
    backend_available: bool
    backend_validated: bool
    status: str
    details: dict

class Repository(Protocol):
    """未来PostgreSQL实现也需提供事务和完整性契约。"""
    def transaction(self) -> Any: ...
    def integrity_check(self) -> str: ...
    def close(self) -> None: ...

class ComputeWorker(Protocol):
    """独立worker进程；不注册CPU AI后端。"""
    def probe(self) -> list[DeviceInfo]: ...
    def require_gpu(self, device_id: str) -> DeviceInfo: ...

JOB_STATES = {'QUEUED', 'RUNNING', 'SUCCEEDED', 'FAILED', 'CANCELLED', 'INTERRUPTED'}
TERMINAL_STATES = JOB_STATES - {'QUEUED', 'RUNNING'}
