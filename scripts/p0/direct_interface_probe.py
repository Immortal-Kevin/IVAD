"""Windows 单连接直连探查；不更改系统路由、代理或 VPN 状态。"""
import argparse
import http.client
import json
import socket
import ssl
import struct
import time
import traceback
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--interface-index', type=int, required=True)
    parser.add_argument('--source-ip', required=True)
    args = parser.parse_args()
    manifest = json.loads((ROOT / 'reports/raw/offline_missing_manifest.json').read_text(encoding='utf-8'))
    urls = [next(e['url'] for e in manifest if e['package'] == name) for name in ['h11', 'torch']]
    results = []
    for url in urls:
        result = dict(url=url, outgoing_interface=args.interface_index, source_ip=args.source_ip, proxy_disabled=True, tls_verification=True)
        start = time.monotonic()
        raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            parsed = urllib.parse.urlsplit(url)
            raw.settimeout(8)
            # 微软 IPPROTO_IP / IP_UNICAST_IF 文档要求设置值为网络字节序。
            raw.setsockopt(socket.IPPROTO_IP, 31, struct.pack('!I', args.interface_index))
            assert raw.getsockopt(socket.IPPROTO_IP, 31) == args.interface_index
            raw.bind((args.source_ip, 0))
            remote = socket.getaddrinfo(parsed.hostname, 443, socket.AF_INET, socket.SOCK_STREAM)[0][4]
            result['remote'] = remote
            raw.connect(remote)
            result['local'] = raw.getsockname()
            context = ssl.create_default_context()
            with context.wrap_socket(raw, server_hostname=parsed.hostname) as connection:
                result['tls_version'] = connection.version()
                path = parsed.path + ('?' + parsed.query if parsed.query else '')
                connection.sendall((f'GET {path} HTTP/1.1\r\nHost: {parsed.hostname}\r\nRange: bytes=0-1023\r\nConnection: close\r\n\r\n').encode('ascii'))
                response = http.client.HTTPResponse(connection)
                response.begin()
                result.update(http_status=response.status, received_bytes=len(response.read(1024)))
                result['status'] = 'PASS' if response.status in [200, 206] else 'FAIL'
        except Exception:
            result.update(status='BLOCKED', traceback=traceback.format_exc())
        finally:
            raw.close()
        result['seconds'] = time.monotonic() - start
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
        (ROOT / 'reports/raw/direct_interface_probe_20261014.json').write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding='utf-8')
