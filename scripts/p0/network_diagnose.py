"""有时间上限的只读网络诊断，验证 TLS，不输出代理凭证。"""
import concurrent.futures
import json
import socket
import ssl
import time
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def sanitized_proxy(value):
    parsed = urllib.parse.urlsplit(value if '://' in value else 'http://' + value)
    return dict(scheme=parsed.scheme, host=parsed.hostname, port=parsed.port, has_credentials=bool(parsed.username or parsed.password))


def probe(label, url, size=None, direct=False):
    start = time.monotonic()
    result = dict(label=label, url=url, direct=direct)
    try:
        headers = {'User-Agent': 'IVAD-P0', 'Accept-Encoding': 'identity'}
        if size:
            headers['Range'] = f'bytes=0-{size-1}'
        request = urllib.request.Request(url, headers=headers)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({})) if direct else urllib.request.build_opener()
        with opener.open(request, timeout=8) as response:
            result.update(status=response.status, length=response.headers.get('Content-Length'), range=response.headers.get('Content-Range'), server=response.headers.get('Server'), transfer=response.headers.get('Transfer-Encoding'))
            data = response.read(size or 65536)
            result['received'] = len(data)
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error))
    result['seconds'] = time.monotonic() - start
    print(json.dumps(result), flush=True)
    return result


if __name__ == '__main__':
    proxies = urllib.request.getproxies()
    result = dict(proxies={k: sanitized_proxy(v) for k, v in proxies.items() if k != 'no'}, no_proxy_configured=bool(proxies.get('no')), tls_verify='default certificate validation enabled', dns={})
    for host in ['pypi.org', 'files.pythonhosted.org', 'download.pytorch.org', 'api.github.com']:
        try:
            result['dns'][host] = sorted(set(item[4][0] for item in socket.getaddrinfo(host, 443)))
        except Exception as error:
            result['dns'][host] = str(error)
    (ROOT / 'reports/raw/network_config_resume.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)
    manifest = json.loads((ROOT / 'artifacts/p0/wheels/manifest.json').read_text())
    wheel = manifest[0]['url']
    tests = [('pypi_json', 'https://pypi.org/pypi/openvino/2026.4.1/json', None, False), ('xpu_index', 'https://download.pytorch.org/whl/xpu/torch/', None, False), ('github_json', 'https://api.github.com/repos/openvinotoolkit/openvino/releases/latest', None, False), ('wheel_1k', wheel, 1024, False), ('wheel_64k', wheel, 65536, False), ('wheel_1m', wheel, 1048576, False), ('wheel_64k_direct', wheel, 65536, True)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as pool:
        result['http'] = list(pool.map(lambda args: probe(*args), tests))
    (ROOT / 'reports/raw/network_diagnosis_resume.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result, indent=2), flush=True)

