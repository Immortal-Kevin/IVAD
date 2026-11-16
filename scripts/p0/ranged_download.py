"""从已核实 URL 下载小分段；最终官方 SHA256 相符后才能安装。"""
import argparse
import concurrent.futures
import hashlib
import json
import sys
import threading
import time
import urllib.request
from pathlib import Path


def download(entry, directory, workers=16, direct=False, deadline=None, range_segments=1):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    target = directory / entry['filename']
    if target.exists() and hashlib.file_digest(target.open('rb'), 'sha256').hexdigest() == entry['sha256']:
        print('HASH VERIFIED existing', target.name, flush=True)
        return
    partial = target.with_suffix('.whl.segments')
    journal = target.with_suffix('.whl.segments.json')
    chunk = 65536
    state = dict(url=entry['url'], sha256=entry['sha256'], size=entry['size'], chunk=chunk, completed=[])
    if journal.exists() and partial.exists():
        previous = json.loads(journal.read_text())
        if all(previous.get(k) == state[k] for k in ['sha256', 'size', 'chunk']):
            state = previous
            if state['url'] != entry['url']:
                state.setdefault('previous_urls', []).append(state['url'])
                state['url'] = entry['url']
    completed = set(state['completed'])
    partial.touch(exist_ok=True)
    lock = threading.Lock()
    started = time.monotonic()
    total = (entry['size'] + chunk - 1) // chunk
    if direct:
        from direct_https import opener
        open_url = opener().open
    else:
        open_url = urllib.request.urlopen

    def save_state():
        state['completed'] = sorted(completed)
        temporary = journal.with_suffix(journal.suffix + '.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(journal)

    def fetch(index):
        if deadline and time.monotonic() >= deadline:
            raise TimeoutError('DIRECT WINDOW FINISHED')
        needed = [i for i in range(index, min(total, index + range_segments)) if i not in completed]
        if not needed:
            return
        first = min(needed)
        last = max(needed)
        start = first * chunk
        end = min(entry['size'] - 1, (last + 1) * chunk - 1)
        request = urllib.request.Request(entry['url'], headers={'Range': f'bytes={start}-{end}', 'Accept-Encoding': 'identity', 'User-Agent': 'IVAD-P0'})
        for attempt in range(2):
            try:
                with open_url(request, timeout=8 if direct else 20) as response:
                    assert response.status == 206
                    assert response.headers['Content-Range'] == f'bytes {start}-{end}/{entry["size"]}'
                    if direct and deadline:
                        expected = end - start + 1
                        parts = []
                        received = 0
                        pending = bytearray()
                        next_index = first
                        while received < expected:
                            if time.monotonic() >= deadline:
                                raise TimeoutError('DIRECT WINDOW FINISHED')
                            part = response.read1(min(65536, expected - received))
                            if not part:
                                break
                            parts.append(part)
                            received += len(part)
                            pending.extend(part)
                            while pending:
                                segment_size = min(chunk, entry['size'] - next_index * chunk)
                                if len(pending) < segment_size:
                                    break
                                segment = bytes(pending[:segment_size])
                                del pending[:segment_size]
                                with lock:
                                    with partial.open('r+b') as output:
                                        output.seek(next_index * chunk)
                                        output.write(segment)
                                    completed.add(next_index)
                                    if len(completed) % 32 == 0 or len(completed) == total:
                                        save_state()
                                        print(target.name, f'{len(completed)}/{total}', f'{time.monotonic()-started:.1f}s', flush=True)
                                next_index += 1
                        data = b''.join(parts)
                    else:
                        data = response.read(end - start + 1)
                assert len(data) == end - start + 1, f'Incomplete segment {index}'
                break
            except Exception as error:
                print('SEGMENT ERROR', index, type(error).__name__, str(error), flush=True)
                if attempt == 1:
                    raise
                if deadline and time.monotonic() >= deadline:
                    raise TimeoutError('DIRECT WINDOW FINISHED')
                time.sleep(1)
        with lock:
            with partial.open('r+b') as output:
                output.seek(start)
                output.write(data)
            completed.update(range(first, last + 1))
            if len(completed) % 32 == 0 or len(completed) == total:
                save_state()
                print(target.name, f'{len(completed)}/{total}', f'{time.monotonic()-started:.1f}s', flush=True)

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(fetch, i) for i in range(0, total, range_segments) if any(j not in completed for j in range(i, min(total, i + range_segments)))]
        try:
            for future in concurrent.futures.as_completed(futures):
                future.result()
        except Exception:
            for future in futures:
                future.cancel()
            with lock:
                save_state()
            raise
    with partial.open('rb') as output:
        digest = hashlib.file_digest(output, 'sha256').hexdigest()
    assert digest == entry['sha256'], f'HASH MISMATCH: {digest}'
    partial.replace(target)
    print('HASH VERIFIED', target.name, digest, flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('manifest')
    parser.add_argument('--directory', required=True)
    parser.add_argument('--workers', type=int, default=16)
    parser.add_argument('--direct', action='store_true')
    parser.add_argument('--window-seconds', type=int)
    parser.add_argument('--range-segments', type=int, default=1)
    args = parser.parse_args()
    deadline = time.monotonic() + args.window_seconds if args.window_seconds else None
    for entry in json.loads(Path(args.manifest).read_text(encoding='utf-8')):
        if deadline and time.monotonic() >= deadline:
            break
        try:
            download(entry, args.directory, args.workers, args.direct, deadline, args.range_segments)
        except TimeoutError as error:
            if str(error) == 'DIRECT WINDOW FINISHED':
                print('WINDOW PAUSED; completed segments journal saved; file not yet verified', flush=True)
                sys.exit(0)
            raise
