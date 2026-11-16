"""只读 DNS/代理/TLS 快照，代理 URL 不记录凭证或查询参数。"""
import json
import socket
import ssl
import urllib.parse
import urllib.request
import winreg
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
result = dict(dns={}, proxies={}, wininet={}, tls={})
for host in ['pypi.org', 'files.pythonhosted.org', 'download.pytorch.org', 'api.github.com', 'pypi.tuna.tsinghua.edu.cn']:
    result['dns'][host] = sorted({item[4][0] for item in socket.getaddrinfo(host, 443)})
for name, value in urllib.request.getproxies().items():
    if name != 'no':
        parsed = urllib.parse.urlsplit(value)
        result['proxies'][name] = dict(host=parsed.hostname, port=parsed.port, credentials_present=bool(parsed.username))
try:
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r'Software\Microsoft\Windows\CurrentVersion\Internet Settings') as key:
        for field in ['ProxyEnable', 'ProxyServer', 'AutoConfigURL']:
            try:
                value = winreg.QueryValueEx(key, field)[0]
                result['wininet'][field] = value if field == 'ProxyEnable' else bool(value)
            except FileNotFoundError:
                result['wininet'][field] = None
except OSError as error:
    result['wininet']['error'] = str(error)
context = ssl.create_default_context()
result['tls'] = dict(verify_mode=str(context.verify_mode), check_hostname=context.check_hostname, ca_stats=context.cert_store_stats(), ssl_version=ssl.OPENSSL_VERSION)
(ROOT / 'reports/raw/network_snapshot_resume.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps(result, indent=2))
