"""Synthetic-only LGPL FFmpeg CLI experiment, NOT IVAD or EXE acceptance."""
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/p37d-20261019'
BIN = next((OUT / 'lgpl-prototype').glob('*/bin'))
RESULT = OUT / 'video-prototype'


def command(args):
    process = subprocess.run([str(a) for a in args], capture_output=True, text=True,
                             encoding='utf8', errors='replace', timeout=45)
    return dict(args=[str(a) for a in args], returncode=process.returncode,
                stdout=process.stdout, stderr=process.stderr)


def probe(path):
    run = command([BIN / 'ffprobe.exe', '-v', 'error', '-select_streams', 'v:0',
                   '-show_frames', '-show_streams', '-of', 'json', path])
    if run['returncode']:
        raise RuntimeError(run)
    data = json.loads(run['stdout'])
    return dict(codec=data['streams'][0]['codec_name'],
                width=data['streams'][0]['width'], height=data['streams'][0]['height'],
                pts_us=[round(float(f['best_effort_timestamp_time']) * 1000000) for f in data['frames']])


def main():
    RESULT.mkdir(exist_ok=False)
    all_results = dict(scope='Synthetic CLI experiment only; no IVAD integration, no EXE, no final payload license approval.',
                       fixtures=json.loads((OUT / 'synthetic-fixtures.json').read_text()), cases={})
    for kind in ['cfr', 'vfr']:
        source = OUT / f'{kind}-h264.mp4'
        folder = RESULT / kind
        folder.mkdir()
        case = all_results['cases'][kind] = dict(source=probe(source))
        case['decode'] = command([BIN / 'ffmpeg.exe', '-nostdin', '-v', 'error', '-i', source,
                                  '-map', '0:v:0', '-f', 'null', '-'])
        case['extract'] = command([BIN / 'ffmpeg.exe', '-nostdin', '-n', '-v', 'error', '-i', source,
                                   '-fps_mode', 'passthrough', folder / '%04d.png'])
        case['extracted_count'] = len(list(folder.glob('*.png')))
        # MPEG-4 Part 2 is a free-code alternative, not an H.264 patent determination.
        for codec in ['mpeg4', 'h264_mf']:
            dest = folder / f'clip-{codec}.mp4'
            case[codec] = command([BIN / 'ffmpeg.exe', '-nostdin', '-n', '-v', 'error', '-i', source,
                                   '-ss', '0.2', '-t', '1', '-an', '-c:v', codec, '-b:v', '2M',
                                   '-bf', '0', '-fps_mode', 'passthrough', dest])
            if case[codec]['returncode'] == 0:
                actual = probe(dest)
                wanted = [t - 200000 for t in case['source']['pts_us'] if 200000 <= t < 1200000]
                actual['expected_pts_us'] = wanted
                actual['exact_pts_match'] = actual['pts_us'] == wanted
                actual['max_pts_error_us'] = (max(abs(a - b) for a, b in zip(actual['pts_us'], wanted))
                                               if len(wanted) == len(actual['pts_us']) else None)
                case[codec]['probe'] = actual
        case['decode_extraction_pass'] = (case['source']['codec'] == 'h264' and
                                          len(case['source']['pts_us']) == 40 and
                                          case['decode']['returncode'] == case['extract']['returncode'] == 0 and
                                          case['extracted_count'] == 40)
    (RESULT / 'results.json').write_text(json.dumps(all_results, ensure_ascii=False, indent=2), encoding='utf8')
    for kind, result in all_results['cases'].items():
        print(kind, 'CLI decode/extract:', result['decode_extraction_pass'],
              'encoders:', {c: {'returncode': result[c]['returncode'],
                               'probe': result[c].get('probe')} for c in ['mpeg4', 'h264_mf']})
    if not all(c['decode_extraction_pass'] for c in all_results['cases'].values()):
        raise SystemExit('CLI media experiment failed; retain original evidence')


if __name__ == '__main__':
    main()
