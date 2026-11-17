"""Local crash diagnostics; never contains frame bytes or uploads anything."""
import faulthandler
import json
import os
from pathlib import Path
import sys
import time
import traceback

_handles = []

def install(directory, role):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    fatal = (directory / (role + '-fatal.log')).open('a', encoding='utf8')
    _handles.append(fatal)
    faulthandler.enable(file=fatal, all_threads=True)
    if role == 'gui':
        stderr = (directory / 'gui-stderr.log').open('a', encoding='utf8', buffering=1)
        _handles.append(stderr)
        sys.stderr = stderr
    record(directory, role, 'startup', pid=os.getpid(), argv=sys.argv)
    return directory

def record(directory, role, event, **data):
    with (Path(directory) / (role + '-events.jsonl')).open('a', encoding='utf8') as f:
        f.write(json.dumps(dict(time=time.time(), event=event, **data), ensure_ascii=False, default=str) + '\n')

def exception(directory, role, exc):
    record(directory, role, 'exception', type=type(exc).__name__, message=str(exc),
           traceback=''.join(traceback.format_exception(exc)))
