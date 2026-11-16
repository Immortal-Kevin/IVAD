"""为 P0 子进程提供墙钟超时；超时仅结束自身启动的任务树。"""
import argparse
import subprocess
import sys
from pathlib import Path

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seconds', type=int, default=180)
    parser.add_argument('--log', required=True)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    with Path(args.log).open('w', encoding='utf-8') as log:
        process = subprocess.Popen(args.command, stdout=log, stderr=subprocess.STDOUT)
        try:
            code = process.wait(timeout=args.seconds)
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], stdout=log, stderr=subprocess.STDOUT, check=False)
            log.write(f'\nBLOCKED: wall-clock timeout {args.seconds}s\n')
            code = 124
    print(Path(args.log).read_text(encoding='utf-8', errors='replace'))
    sys.exit(code)
