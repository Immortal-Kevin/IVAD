"""Reuse historical sample files read-only; no transcoding to fake compatibility."""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/permissive-20261102/matrix'
CASES = {
    'core-ps': ROOT.parent / '示例项目/超高压压滤机/超高压车间8525压滤机_1026191715.mp4',
    'standard-mp4': ROOT / 'artifacts/p2/samples/sample.mp4',
    'avi': ROOT / 'artifacts/p2/samples/sample.avi',
    'mov': ROOT / 'artifacts/p2/samples/sample.mov',
    'mkv': ROOT / 'artifacts/p2/samples/sample.mkv',
    'vfr': ROOT / 'artifacts/p2/samples/vfr.mp4',
    'h265-mkv': ROOT / 'artifacts/p35-gui-20261016/pytest-main/test_external_formats_gui_prob6/owned-demo-libx265.mkv',
    'unicode': ROOT / 'artifacts/rf-bugfix-20261019/中文路径.mp4',
}

if __name__ == '__main__':
    OUT.mkdir(exist_ok=False)
    results = {}
    for name, path in CASES.items():
        if not path.is_file():
            results[name] = {'status': 'NOT TESTED', 'reason': 'sample not present'}
            continue
        target = OUT / (name + '.json')
        try:
            run = subprocess.run([sys.executable, str(ROOT / 'scripts/permissive/media_probe.py'), str(path), str(target)], capture_output=True, timeout=90)
            (OUT / (name + '.stdout')).write_bytes(run.stdout)
            (OUT / (name + '.stderr')).write_bytes(run.stderr)
            results[name] = json.loads(target.read_text(encoding='utf8')) if target.exists() else {'status': 'FAIL', 'returncode': run.returncode}
        except subprocess.TimeoutExpired:
            results[name] = {'status': 'FAIL', 'error': 'Owned probe timed out at 90s; terminated'}
        print(name, results[name]['status'], flush=True)
    brief = {k: {n: v[n] for n in ('status','error','frame_count','frame_rate','duration_ticks','size','container') if n in v} for k,v in results.items()}
    (OUT / 'summary.json').write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding='utf8')
