"""只解析 P0 固定主版本依赖；官方 PyPI 哈希和 Windows cp314 标签。"""
import json
import gzip
import re
import urllib.request
from collections import deque
from pathlib import Path
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.tags import sys_tags
from pip._vendor.packaging.utils import canonicalize_name, parse_wheel_filename
from pip._vendor.packaging.version import Version

ROOT = Path(__file__).resolve().parents[2]


def metadata(name, version=None):
    local = ROOT / f'reports/raw/{name}_metadata_resume.json'
    if local.exists():
        candidate = json.loads(local.read_text(encoding='utf-8'))
        if version is None or candidate['info']['version'] == version:
            return candidate
    if version is None:
        request = urllib.request.Request(f'https://pypi.org/pypi/{name}/json', headers={'Accept-Encoding': 'gzip'})
        with urllib.request.urlopen(request, timeout=10) as response:
            stream = gzip.GzipFile(fileobj=response) if response.headers.get('Content-Encoding') == 'gzip' else response
            raw = b''
            for _ in range(4):
                raw += stream.read(65536)
                prefix = raw.decode('utf-8', errors='replace')
                info_start = prefix.index('"info":') + len('"info":')
                try:
                    info, _ = json.JSONDecoder().raw_decode(prefix[info_start:].lstrip())
                    break
                except json.JSONDecodeError:
                    continue
            else:
                raise RuntimeError(f'{name} info exceeds bounded metadata budget')
        version = info['version']
    suffix = f'/{version}' if version else ''
    request = urllib.request.Request(f'https://pypi.org/pypi/{name}{suffix}/json', headers={'Accept-Encoding': 'gzip'})
    with urllib.request.urlopen(request, timeout=10) as response:
        stream = gzip.GzipFile(fileobj=response) if response.headers.get('Content-Encoding') == 'gzip' else response
        return json.load(stream)


if __name__ == '__main__':
    fixed = {'torch': '2.14.1+xpu', 'torchvision': '0.29.1+xpu', 'numpy': '2.5.4', 'openvino': '2026.4.1', 'openvino-telemetry': '2025.2.0'}
    # 沿用上轮 pip 已解析版本，避免读取包含全部发行历史的大 JSON。
    for line in (ROOT / 'reports/raw/install_train.log').read_text().splitlines():
        match = re.search(r'Downloading ([A-Za-z0-9_]+)-([0-9][^- ]*)-[^ ]+\.whl\.metadata', line)
        if match:
            fixed.setdefault(canonicalize_name(match[1]), match[2])
    queue = deque(json.loads((ROOT / 'reports/raw/xpu_requires_dist.json').read_text()) + ['openvino==2026.4.1', 'numpy==2.5.4', 'openvino-telemetry==2025.2.0', 'psutil'])
    selected = {k: dict(version=v) for k, v in fixed.items() if k in ['torch', 'torchvision']}
    manifest = []
    saved = ROOT / 'reports/raw/train_dependency_manifest.json'
    if saved.exists():
        for entry in json.loads(saved.read_text()):
            if entry['package'] in fixed and entry['version'] != fixed[entry['package']]:
                continue
            selected[entry['package']] = entry
            manifest.append(entry)
            queue.extend(entry.get('requires_dist', []))
    tag_rank = {tag: i for i, tag in enumerate(sys_tags())}
    while queue:
        requirement = Requirement(queue.popleft())
        if requirement.marker and not requirement.marker.evaluate({'extra': ''}):
            continue
        name = canonicalize_name(requirement.name)
        if name in selected:
            assert Version(selected[name]['version']) in requirement.specifier, (name, selected[name]['version'], str(requirement))
            continue
        if name == 'triton-xpu':
            entry = next(e for e in json.loads((ROOT / 'reports/raw/xpu_download_manifest.json').read_text()) if e['package'] == name)
            selected[name] = entry
            manifest.append(entry)
            queue.extend(entry['requires_dist'])
            continue
        exact = next((s.version for s in requirement.specifier if s.operator == '==' and '*' not in s.version), None)
        data = metadata(name, fixed.get(name) or exact)
        version = data['info']['version']
        if Version(version) not in requirement.specifier:
            versions = sorted((Version(v) for v in data['releases'] if Version(v) in requirement.specifier and not Version(v).is_prerelease), reverse=True)
            assert versions, f'No version for {requirement}'
            version = str(versions[0])
            data = metadata(name, version)
        candidates = []
        for asset in data['urls']:
            if asset['packagetype'] != 'bdist_wheel' or asset['yanked']:
                continue
            _, _, _, tags = parse_wheel_filename(asset['filename'])
            ranks = [tag_rank[t] for t in tags if t in tag_rank]
            if ranks:
                candidates.append((min(ranks), asset))
        assert candidates, f'No compatible wheel for {name}=={version} on cp314 Windows'
        asset = min(candidates, key=lambda a: a[0])[1]
        deps = data['info']['requires_dist'] or []
        entry = dict(package=name, version=version, filename=asset['filename'], url=asset['url'], size=asset['size'], sha256=asset['digests']['sha256'], requires_dist=deps)
        selected[name] = entry
        manifest.append(entry)
        queue.extend(deps)
        (ROOT / 'reports/raw/train_dependency_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
        print(name, version, asset['filename'], asset['size'], flush=True)
    (ROOT / 'reports/raw/train_candidate_requirements.txt').write_text('\n'.join(f'{name}=={entry["version"]}' for name, entry in sorted(selected.items())) + '\n')
    print('RESOLUTION COMPLETE', len(selected), sum(e['size'] for e in manifest), flush=True)

