"""Fetch exact-version publisher notices; never download company data."""
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'legal/licenses/native-media-20261102'
SOURCES={
    'libjpeg-turbo-3.1.0-LICENSE.md':'https://raw.githubusercontent.com/libjpeg-turbo/libjpeg-turbo/3.1.0/LICENSE.md',
    'libjpeg-turbo-3.1.0-README.ijg':'https://raw.githubusercontent.com/libjpeg-turbo/libjpeg-turbo/3.1.0/README.ijg',
    'FreeType-2.13.3-FTL.TXT':'https://raw.githubusercontent.com/freetype/freetype/VER-2-13-3/docs/FTL.TXT',
    'LittleCMS-2.17-LICENSE':'https://raw.githubusercontent.com/mm2/Little-CMS/lcms2.17/LICENSE',
    'libwebp-1.5.0-COPYING':'https://raw.githubusercontent.com/webmproject/libwebp/v1.5.0/COPYING',
    'libwebp-1.5.0-PATENTS':'https://raw.githubusercontent.com/webmproject/libwebp/v1.5.0/PATENTS',
    'OpenJPEG-2.5.3-LICENSE':'https://raw.githubusercontent.com/uclouvain/openjpeg/v2.5.3/LICENSE',
    'zlib-ng-2.2.4-LICENSE.md':'https://raw.githubusercontent.com/zlib-ng/zlib-ng/2.2.4/LICENSE.md',
    'libtiff-4.7.0-LICENSE.md':'https://gitlab.com/libtiff/libtiff/-/raw/v4.7.0/LICENSE.md',
}

if __name__=='__main__':
    OUT.mkdir(exist_ok=False)
    rows=[]
    for name,url in SOURCES.items():
        try:
            with urllib.request.urlopen(url,timeout=25) as response:content=response.read(1_000_001)
            if not 100<len(content)<1_000_000 or b'<html' in content[:1000].lower():raise ValueError('Not a license text')
            (OUT/name).write_bytes(content)
            rows.append(dict(file=name,url=url,sha256=hashlib.sha256(content).hexdigest(),status='FETCHED-notice-only'))
        except Exception as exc:rows.append(dict(file=name,url=url,status='UNVERIFIED',error=str(exc)))
        print(name,rows[-1]['status'],flush=True)
    (OUT/'SOURCES.json').write_text(json.dumps(rows,indent=2),encoding='utf8')
