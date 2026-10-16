"""Compile the captured actual environment inventories into reviewable compliance material."""
import json,shutil,hashlib,urllib.request
import re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];ART=ROOT/'artifacts/p37a-20261016';legal=ROOT/'legal'
archive_rows=json.loads((ROOT/'artifacts/p36-rfdetr-20261016/archive-lock.json').read_text(encoding='utf8'))
archives={(re.sub('[-_.]+','-',r['name']).lower(),r['version']):r for r in archive_rows}
sources={
 'LGPL-3.0-only.txt':'https://raw.githubusercontent.com/qt/qtbase/v6.8.3/LICENSES/LGPL-3.0-only.txt',
 'GPL-3.0-only.txt':'https://raw.githubusercontent.com/qt/qtbase/v6.8.3/LICENSES/GPL-3.0-only.txt',
 'QtSvg-LGPL-3.0-only.txt':'https://raw.githubusercontent.com/qt/qtsvg/v6.8.3/LICENSES/LGPL-3.0-only.txt',
 'NVIDIA-CUDA-12.8.1-EULA.html':'https://docs.nvidia.com/cuda/archive/12.8.1/eula/index.html',
 'NVIDIA-cuDNN-9.10.2-EULA.html':'https://docs.nvidia.com/deeplearning/cudnn/backend/v9.10.2/reference/eula.html',
 'FFmpeg-legal.html':'https://ffmpeg.org/legal.html',
}
folder=legal/'licenses/p37';folder.mkdir(exist_ok=True);fetch=[]
for name,url in sources.items():
    try:
        data=urllib.request.urlopen(url,timeout=30).read()
        if len(data)<1000:raise ValueError('Unexpected license payload')
        (folder/name).write_bytes(data);fetch.append(dict(file=name,url=url,sha256=hashlib.sha256(data).hexdigest(),status='DOWNLOADED'))
    except Exception as e:fetch.append(dict(file=name,url=url,status='UNRESOLVED',error=str(e)))
(folder/'SOURCES.json').write_text(json.dumps(fetch,ensure_ascii=False,indent=2),encoding='utf8')
lines=['# P3.7-A 实际依赖 SBOM','', '日期 2026-10-16。环境全量安装快照，不是安装包清单。RF正式训练环境、GUI环境及历史YOLO环境分开审计。版本不等于文件来源已证实；不把包顶层许可扩展到捆绑DLL。','', '静态metadata依赖闭包68包（不等于全部动态运行依赖）；RF环境全部96包；GUI静态闭包14包、全部21包（含测试工具）。旧CUDA环境保留，清单沿用已固定的P3.5审计，不作为RF依赖。','', '| 环境 | 名称 | 准确版本 | 许可字段/分类 | 状态 | 来源与原样版权材料 |','|---|---|---|---|---|---|']
for env in ['rf','gui']:
    inv=json.loads((ART/f'license-audit/{env}-all/inventory.json').read_text(encoding='utf8'))
    for r in inv['packages']:
        lic=r.get('license_expression') or r.get('license_field') or '; '.join(r['license_classifiers']) or '未声明'
        lic=' '.join(lic.split());lic=lic[:150].replace('|','/')
        name=r['name'].lower().replace('_','-')
        state='FREE WITH OBLIGATIONS'
        if name in {'av','opencv-python-headless'}:state='REPLACEMENT RECOMMENDED'
        elif name in {'flatbuffers','polygraphy','pycocotools','onnxsim'} or not r['license_files']:state='UNRESOLVED'
        elif name=='rfdetr':state='FREE & VERIFIED（本体）'
        archive=archives.get((name,r['version'])) if env=='rf' else None
        origin=archive['url'] if archive else f"https://pypi.org/project/{r['name']}/{r['version']}/"
        origin_note='实际归档 SHA256 `'+archive['archive_info']['hashes']['sha256']+'`' if archive else '元数据索引；准确原包下载凭证未补齐'
        paths='<br>'.join(f"`{x['audit_copy']}` SHA256 `{x['sha256']}`" for x in r['license_files']) or 'wheel未附完整通知；见补充材料及缺项表'
        lines.append(f"| {env} | {r['name']} | {r['version']} | {lic} | {state} | [来源]({origin})；{origin_note}；原样版权全文位于 artifacts/p37a-20261016/license-audit/{env}-all/{paths} |")
    native=json.loads((ART/f'license-audit/{env}-native.json').read_text(encoding='utf8'))
    resources=json.loads((ART/'nvidia-dll-versions.json').read_text(encoding='utf-8-sig'))+json.loads((ART/'qt-loaded-modules.json').read_text(encoding='utf-8-sig'))
    versions={r.get('Name') or r.get('ModuleName'):r.get('Version') or r.get('FileVersion') for r in resources}
    for row in native:
        name=row['path'].replace('\\','/').split('/')[-1]
        row.update(binary_file_version=versions.get(name),source='Installed wheel RECORD; package version is not binary provenance',copyright_notice_index=f'artifacts/p37a-20261016/license-audit/{env}-all/inventory.json',distribution_status='UNRESOLVED',obligation='Match bundled component license, source and notice to this exact SHA256; see P37_DISTRIBUTION_OBLIGATIONS.md')
        if name in {'Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Svg.dll','qwindows.dll'}:row.update(license_path='LGPLv3 available for audited modules; dynamic replacement/source obligations pending',distribution_status='FREE WITH OBLIGATIONS')
        elif row['component'].lower() in {'av','opencv-python-headless'}:row.update(distribution_status='REPLACEMENT RECOMMENDED',license_path='Top-level package license does not settle bundled codecs')
        else:row['license_path']='Package notices available; full bundled-binary legal mapping not yet verified'
    (legal/f'P37_{env.upper()}_NATIVE_BINARY_INVENTORY.json').write_text(json.dumps(native,ensure_ascii=False,indent=2),encoding='utf8')
    lines.extend(['',f'{env} 原生文件逐一记录：{len(native)} 个DLL/PYD，名称、所属发行版版本、长度与SHA256见 `P37_{env.upper()}_NATIVE_BINARY_INVENTORY.json`。缺少独立文件版本/来源的文件不得仅按包版本推断许可。'])
lines.extend(['','## 模型与外部程序','', '官方Nano权重 d8d6b9ee57d4d0ed2b1f305163624712a0532cb7bce0c747317984fc5457440d；固定上游源码7433d5919d0f7e72cc6cb78663e0a731afd499e0，Apache-2.0资产声明见P3.6审计。RF Plus不在环境中。','', '实际RF路径启动程序为独立venv python.exe及Windows taskkill.exe（仅超时停止本次子进程树）。NVIDIA驱动617.42属于本机驱动，不作为安装包payload；CUDA12.8、cuDNN与ORT原生文件另列。历史FFmpeg外部程序与构建工具没有在本轮新增或重分发。系统Windows DLL许可不因本SBOM变更。','', '版权权利人以逐文件原文及NOTICE为准，不能用单一包作者代表全部原生第三方。RF DINOv2/DETR等保留原始文件头，不修改IVAD自研授权。'])
(legal/'P37_DEPENDENCY_SBOM.md').write_text('\n'.join(lines)+'\n',encoding='utf8')
print(json.dumps(fetch))
