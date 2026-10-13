import subprocess, sys, time
from pathlib import Path
from ivad_app.core.application import ApplicationServices

def test_real_process_crash_and_restart(tmp_path):
    root = Path(__file__).resolve().parents[1]
    data = tmp_path / 'crash-runtime'
    code = '''
import sys,time
from pathlib import Path
from ivad_app.core.application import ApplicationServices
a=ApplicationServices(Path.cwd(),Path(sys.argv[1]),step_seconds=1)
j=a.jobs.submit()
while a.jobs.get(j)['state']!='RUNNING': time.sleep(.01)
print(j,flush=True)
time.sleep(60)
'''
    child = subprocess.Popen([sys.executable, '-u', '-c', code, str(data)], cwd=root, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        deadline = time.monotonic() + 10
        # 数据库中的RUNNING状态已commit后子进程输出，再有意终止专属测试进程。
        from concurrent.futures import ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=1) as pool:
            job = pool.submit(child.stdout.readline).result(timeout=10).strip()
        assert job
        child.terminate(); child.wait(timeout=10)
        restored = ApplicationServices(root, data)
        try:
            assert restored.db.integrity_check() == 'ok'
            assert restored.jobs.get(job)['state'] == 'INTERRUPTED'
        finally: restored.close()
    finally:
        if child.poll() is None: child.kill(); child.wait(timeout=10)
