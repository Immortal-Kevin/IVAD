"""Seal actual installed archive hashes and indexed original license evidence."""
import hashlib
import importlib.metadata as metadata
import json
import re
from pathlib import Path


def main():
    root=Path('artifacts/p36-rfdetr-20261016')
    packages=json.loads((root/'dependency-audit/p36-rfdetr/inventory.json').read_text(encoding='utf8'))['packages']
    archives={}
    for report in ('torch-install.json','rfdetr-install.json','export-deps-install.json'):
        data=json.loads((root/report).read_text(encoding='utf8'))
        for row in data['install']:
            name=re.sub('[-_.]+','-',row['metadata']['name']).lower()
            archives[(name,row['metadata']['version'])]=row['download_info']
    locks=['# Windows CPython 3.12 amd64; actual P36 evaluation runtime, not a distribution approval',
           '--index-url https://pypi.org/simple','--extra-index-url https://download.pytorch.org/whl/cu128']
    rows=['# RF-DETR 实验实际安装依赖索引','',
          '本清单列出全部实际安装包（含 pip 工具）。版权栏为原文摘要；完整版权、条款、NOTICE 和捆绑第三方内容以列出的原样证据为准。metadata 许可字段不是最终法律结论。无通知副本的组件尚需补齐正式发行材料。',
          '', '| 名称/版本 | 官方元数据项目地址 | 许可 | 版权摘要/原文 | 通知与再分发检查 |', '|---|---|---|---|---|']
    sealed=[]
    for row in packages:
        d=metadata.distribution(row['name'])
        key=(re.sub('[-_.]+','-',row['name']).lower(),row['version'])
        info=archives.get(key)
        if row['name'].lower()!='pip':
            if info is None:raise ValueError(f'Missing installation archive: {key}')
            digest=info['archive_info']['hashes']['sha256']
            locks.append(f"{row['name']}=={row['version']} --hash=sha256:{digest}")
            sealed.append(dict(name=row['name'],version=row['version'],**info))
        license=row['license_expression'] or row['license_field'] or '; '.join(row['license_classifiers'])
        copyright=[]
        for notice in row['license_files']:
            path=root/'dependency-audit/p36-rfdetr'/notice['audit_copy']
            assert hashlib.sha256(path.read_bytes()).hexdigest()==notice['sha256']
            text=path.read_text(encoding='utf8',errors='replace')
            if not license and 'Apache License' in text and 'Version 2.0' in text:license='Apache-2.0 (原文核验)'
            copyright.extend(x.strip() for x in text.splitlines() if re.search(r'copyright\s*(?:\(c\))?\s*(?:19|20)\d{2}|©\s*(?:19|20)\d{2}',x,re.I))
        license=' '.join(license.split())
        if len(license)>120:license=license[:120]+'…（完整见原文）'
        urls=d.metadata.get_all('Project-URL') or [d.metadata.get('Home-page') or '元数据未列出；待补核']
        owner=' / '.join(dict.fromkeys(copyright))[:300] or '元数据/原文未提取到简短声明；不推定无版权'
        references='<br>'.join(f"`{f['audit_copy']}`" for f in row['license_files']) or '**本 wheel 未列原样通知副本，发行待补齐**'
        def escape(value):return value.replace('|','\\|').replace('\n',' ')
        rows.append('| '+ ' | '.join(escape(str(v)) for v in [row['name']+' '+row['version'],'; '.join(urls)[:500],license or '字段为空，待核验',owner+'<br>'+references,'已采集 '+str(len(row['license_files']))+' 份；保留适用许可/版权/NOTICE，原生捆绑及发行义务仍待审定'])+' |')
    Path('experiments/p36_rfdetr/requirements.lock.txt').write_text('\n'.join(locks)+'\n',encoding='utf8')
    Path('legal/RFDETR_DEPENDENCY_INVENTORY.md').write_text('\n'.join(rows)+'\n',encoding='utf8')
    (root/'archive-lock.json').write_text(json.dumps(sealed,ensure_ascii=False,indent=2),encoding='utf8')
    print(dict(packages=len(packages),hash_locked_runtime=len(sealed),notice_copies=sum(len(p['license_files']) for p in packages)))


if __name__=='__main__':main()
