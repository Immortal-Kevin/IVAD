"""仅当前下载进程使用无代理IPv4 HTTPS；默认证书验证保持开启。"""
import http.client
import os
import socket
import ssl
import urllib.request


def ipv4_connect(address, timeout, source_address=None):
    error = None
    for _, _, _, _, remote in socket.getaddrinfo(address[0], address[1], socket.AF_INET, socket.SOCK_STREAM):
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        connection.settimeout(timeout)
        try:
            if source_address:
                connection.bind(source_address)
            connection.connect(remote)
            expected_source = os.environ.get('IVAD_DIRECT_SOURCE_IP')
            if expected_source and connection.getsockname()[0] != expected_source:
                raise OSError('Direct source interface mismatch; refusing VPN path')
            return connection
        except OSError as current:
            error = current
            connection.close()
    raise error or OSError('IPv4 address unavailable')


class DirectConnection(http.client.HTTPSConnection):
    def connect(self):
        self._create_connection = ipv4_connect
        super().connect()


class DirectHandler(urllib.request.HTTPSHandler):
    def https_open(self, request):
        return self.do_open(DirectConnection, request, context=self._context)


def opener():
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), DirectHandler(context=ssl.create_default_context()))
