"""Windows-trusted server CAs for pinned Requests without Mozilla/certifi data.

Does not disable TLS verification. Certificates are read from Windows stores;
no private keys, industrial files or credentials are exported or uploaded.
"""
import atexit
import os
from pathlib import Path
import ssl
import tempfile
import threading

_lock=threading.Lock()
_path=None

def where():
    global _path
    if os.name!='nt':raise RuntimeError('IVAD Windows trust adapter requires Windows')
    with _lock:
        if _path is not None:return str(_path)
        certificates=set()
        for store in ('ROOT','CA'):
            for value,encoding,trust in ssl.enum_certificates(store):
                if encoding=='x509_asn' and (trust is True or ssl.Purpose.SERVER_AUTH.oid in trust):
                    certificates.add(ssl.DER_cert_to_PEM_cert(value))
        if not certificates:raise RuntimeError('Windows provided no trusted server CA certificates')
        descriptor,name=tempfile.mkstemp(prefix='ivad-system-trust-',suffix='.pem')
        with os.fdopen(descriptor,'w',encoding='ascii') as stream:
            stream.write(''.join(sorted(certificates)))
        _path=Path(name)
        atexit.register(lambda p=_path:p.unlink(missing_ok=True))
        return name
