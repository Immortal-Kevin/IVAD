"""本轮临时出口节点测试的独立恢复保护；不修改其他Tailscale设置。"""
import json
import argparse
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'reports/raw'
settings = json.loads((RAW / 'vpn_restore_settings_20261014.json').read_text(encoding='utf-8-sig'))
parser = argparse.ArgumentParser()
parser.add_argument('--token', default='20261014')
parser.add_argument('--delay', type=int, default=180)
args = parser.parse_args()
assert settings['RestoreAddress']
(RAW / f'vpn_watchdog_ready_{args.token}.json').write_text(json.dumps(dict(ready=True, delay_seconds=args.delay)))
time.sleep(args.delay)
if not (RAW / f'vpn_test_restored_{args.token}.json').exists():
    result = subprocess.run(['C:/Program Files/Tailscale/tailscale.exe', 'set', '--exit-node=' + settings['RestoreAddress']], capture_output=True, text=True, timeout=20)
    (RAW / f'vpn_watchdog_result_{args.token}.json').write_text(json.dumps(dict(returncode=result.returncode, stdout=result.stdout, stderr=result.stderr), ensure_ascii=False, indent=2), encoding='utf-8')
