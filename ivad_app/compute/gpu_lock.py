"""Cross-process CUDA lease, compatible with historical IVAD lock names."""
from contextlib import contextmanager
from pathlib import Path
import re
import time

class ComputationCancelled(Exception):pass

@contextmanager
def gpu_lease(root,device_uuid,cancelled):
    import msvcrt
    if not re.fullmatch(r'[A-Za-z0-9_-]+',device_uuid):raise ValueError('Invalid GPU UUID')
    path=Path(root)/'runtime/gpu-locks'/f'{device_uuid}.lock';path.parent.mkdir(parents=True,exist_ok=True)
    handle=path.open('a+b');handle.seek(0);handle.write(b'0');handle.flush();acquired=False
    try:
        while not acquired:
            if cancelled():raise ComputationCancelled('等待GPU时取消')
            try:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_NBLCK,1);acquired=True
            except OSError:time.sleep(.05)
        if cancelled():raise ComputationCancelled('开始计算前取消')
        yield
    finally:
        if acquired:handle.seek(0);msvcrt.locking(handle.fileno(),msvcrt.LK_UNLCK,1)
        handle.close()
