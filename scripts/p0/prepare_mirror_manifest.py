"""仅为缺失文件核验可信TUNA索引，要求hash与官方元数据一致。"""
import concurrent.futures
import gzip
import hashlib
import html
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path
from direct_https import opener

ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'reports/raw'
entries=json.loads((RAW/'p0_full_offline_manifest.json').read_text(encoding='utf-8'))


def check(entry):
    entry=dict(entry)
    target=ROOT/'artifacts/p0/wheels'/entry['filename']
    if target.exists():
        with target.open('rb') as stream:
            if hashlib.file_digest(stream,'sha256').hexdigest()==entry['sha256']:
                return entry
    if urllib.parse.urlsplit(entry['url']).hostname!='files.pythonhosted.org':
        return entry
    index='https://pypi.tuna.tsinghua.edu.cn/simple/'+entry['package']+'/'
    request=urllib.request.Request(index,headers={'Accept-Encoding':'gzip'})
    with opener().open(request,timeout=8) as response:
        stream=gzip.GzipFile(fileobj=response) if response.headers.get('Content-Encoding')=='gzip' else response
        source=stream.read().decode('utf-8')
    links=re.findall(r'href="([^"]+)"',source)
    link=next(html.unescape(link) for link in links if urllib.parse.unquote(urllib.parse.urlsplit(html.unescape(link)).path).split('/')[-1]==entry['filename'])
    url=urllib.parse.urljoin(index,link)
    url,fragment=urllib.parse.urldefrag(url)
    assert urllib.parse.parse_qs(fragment)['sha256'][0]==entry['sha256']
    assert urllib.parse.urlsplit(url).hostname=='pypi.tuna.tsinghua.edu.cn'
    entry.update(official_url=entry['url'],url=url,mirror_index=index,mirror_hash_matched=True)
    print('MIRROR INDEX/HASH VERIFIED',entry['filename'],flush=True)
    return entry


with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    result=list(pool.map(check,entries))
(RAW/'p0_tuna_verified_manifest_20261014.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print('COMPLETE',sum(e.get('mirror_hash_matched',False) for e in result))
