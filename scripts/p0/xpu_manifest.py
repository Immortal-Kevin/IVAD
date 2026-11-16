"""从官方 XPU simple 索引核查固定 wheel URL/hash/大小和 METADATA。"""
import email
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def fetch(url, limit=None, headers=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers or {}), timeout=10) as response:
        return response.read(limit)


if __name__ == '__main__':
    manifest = []
    requirements = []
    for name, version in [('torch', '2.14.1+xpu'), ('torchvision', '0.29.1+xpu'), ('triton-xpu', '3.8.0')]:
        index = (ROOT / f'reports/raw/xpu_{name}_index.html').read_text()
        filename = f'{name.replace("-", "_")}-{version}-cp314-cp314-win_amd64.whl'
        match = next(m for m in re.finditer(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', index) if html.unescape(m[3]) == filename)
        index_url, fragment = urllib.parse.urldefrag(html.unescape(match[1]))
        # 索引 R2 端点本机返回403；等价官方 CDN 已用1字节实测成功。
        url = index_url.replace('https://download-r2.pytorch.org/', 'https://download.pytorch.org/')
        digest = urllib.parse.parse_qs(fragment)['sha256'][0]
        with urllib.request.urlopen(urllib.request.Request(url, headers={'Range': 'bytes=0-0'}), timeout=10) as response:
            size = int(response.headers['Content-Range'].split('/')[-1])
            assert len(response.read(1)) == 1
        metadata = fetch(url + '.metadata')
        metadata_hash = re.search(r'data-core-metadata="sha256=([a-f0-9]+)"', match[2])[1]
        assert hashlib.sha256(metadata).hexdigest() == metadata_hash
        (ROOT / f'reports/raw/{name}_official.metadata').write_bytes(metadata)
        message = email.message_from_bytes(metadata)
        deps = message.get_all('Requires-Dist')
        requirements.extend(deps)
        manifest.append(dict(package=name, version=version, filename=filename, url=url, index_url=index_url, sha256=digest, size=size, abi='cp314', platform='win_amd64', requires_dist=deps))
        (ROOT / 'reports/raw/xpu_download_manifest.json').write_text(json.dumps(manifest, indent=2))
        print(name, version, size, digest, flush=True)
    (ROOT / 'reports/raw/xpu_requires_dist.json').write_text(json.dumps(requirements, indent=2))
