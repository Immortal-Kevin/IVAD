"""Inventory/scanning of the actual local onedir, never a development venv."""
import ast
import csv
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys
import types
import zipfile
import pefile
from PyInstaller.archive.readers import CArchiveReader

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'artifacts/p37d-lite-20261019'
CANDIDATE=ROOT/'dist/IVAD_P37D_Lite_Candidate'
EXE=CANDIDATE/'IVAD_Internal_Demo.exe'

def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def toc_rows(value):
    if isinstance(value,(tuple,list)):
        if len(value)==3 and all(isinstance(v,str) for v in value) and value[2] in {'BINARY','DATA','EXTENSION','EXECUTABLE'}:
            yield value
        else:
            for item in value:yield from toc_rows(item)

def constants(code):
    for value in code.co_consts:
        if isinstance(value,str):yield value
        elif isinstance(value,types.CodeType):yield from constants(value)

def file_version(path):
    try:
        pe=pefile.PE(str(path),fast_load=True)
        pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_RESOURCE']])
        for group in getattr(pe,'FileInfo',[]):
            for info in group:
                for table in getattr(info,'StringTable',[]):
                    if b'FileVersion' in table.entries:
                        value=table.entries[b'FileVersion'].decode('utf8',errors='replace');pe.close();return value
        pe.close()
    except pefile.PEFormatError:pass
    return ''

def main():
    assert CANDIDATE.is_dir() and EXE.is_file()
    archive=CArchiveReader(str(EXE));pyz=archive.open_embedded_archive(next(n for n in archive.toc if n.endswith('.pyz')))
    modules=sorted(pyz.toc)
    forbidden={'torch','torchvision','ultralytics','ultralytics_platform','ultralytics_thop','thop','rfdetr','onnxruntime','cv2'}
    bad_modules=[n for n in modules if n.split('.')[0] in forbidden or n in {
        'ivad_app.services.training_service','ivad_app.services.rfdetr_training_service',
        'ivad_app.services.offline_demo_service','ivad_app.compute.train_worker','ivad_app.compute.offline_worker'}]
    source_toc=ast.literal_eval((OUT/'build-minimal/ivad_lite/COLLECT-00.toc').read_text(encoding='utf8'))
    origins={name.replace('\\','/'):Path(path) for name,path,_ in toc_rows(source_toc)}
    owners={}
    cached_versions={r['sha256']:r.get('file_version') for r in json.loads((ROOT/'legal/licenses/p37l/BINARY_VERSIONS.json').read_text(encoding='utf8'))}
    for dist in importlib.metadata.distributions():
        for file in dist.files or []:owners[str(Path(dist.locate_file(file)).resolve()).lower()]=(dist.metadata['Name'],dist.version)
    before=json.loads((OUT/'protection-before.json').read_text(encoding='utf8'))
    # Only actual protected identifiers/paths, never short generic words.
    tokens=set()
    for row in before['tables'].get('media_assets',[]):
        if row.get('original_path'):tokens.add(row['original_path'])
    for table in ['cameras','model_versions','projects']:
        for row in before['tables'].get(table,[]):
            if row.get('id'):tokens.add(row['id'])
    tokens={s for s in tokens if len(s)>=12}
    encoded=[(hashlib.sha256(s.encode()).hexdigest(),s.encode('utf8'),s.encode('utf-16-le')) for s in tokens]
    private_hits=[];bad_files=[];records=[];content_markers=[];file_content_markers=[]
    for path in sorted(p for p in CANDIDATE.rglob('*') if p.is_file()):
        rel=path.relative_to(CANDIDATE).as_posix();key=rel.removeprefix('_internal/')
        source=origins.get(key) or origins.get(rel)
        component,version=owners.get(str(source.resolve()).lower(),('UNMAPPED','')) if source else ('DOCUMENTATION','')
        name=path.name.lower()
        if any(word in name for word in ['ultralytics','torch','cudnn','cublas','cudart','yolo','libx264','libx265']) or path.suffix.lower() in {'.pt','.pth','.ckpt','.onnx','.sqlite','.db'}:
            bad_files.append(rel)
        if '/av.libs/' in '/'+rel:component,version='FFmpeg (BtbN LGPL shared)','n7.1.5-12-g1fdbca85aa'
        if name.startswith(('vcruntime','msvcp')):component,version='Microsoft VC Runtime (wheel/base supplied)','see file resource and source'
        elif name in {'libssl-3-x64.dll','libcrypto-3-x64.dll'}:component,version='OpenSSL','3.5.8'
        elif name=='sqlite3.dll':component,version='SQLite','3.53.1'
        elif source and source.resolve().is_relative_to(Path(sys.base_prefix).resolve()):component,version='CPython','3.12.14'
        elif name.startswith('qt6') or '/plugins/' in rel:component,version='Qt','6.8.3'
        elif path==EXE:component,version='IVAD + PyInstaller bootloader','P37D Lite / 6.22.3'
        elif source and source.resolve().is_relative_to(ROOT/'ivad_app'):component,version='IVAD common application','P37D Lite'
        elif name=='base_library.zip':component,version='CPython standard library','3.12.14'
        if source:
            origin=str(source)
            for prefix,label in [(str(ROOT/'.venv-p37d-build'),'<BUILD_ENV>'),(str(Path(sys.base_prefix)),'<CPYTHON_BASE>'),(str(ROOT),'<REPOSITORY>')]:
                if origin.lower().startswith(prefix.lower()):origin=label+origin[len(prefix):];break
        else:origin='locally prepared public notices/sources' if rel.startswith('licenses/') else 'prepared application document'
        digest=sha(path)
        row=dict(path=rel,bytes=path.stat().st_size,sha256=digest,component=component,version=version,
                 file_version=cached_versions.get(digest) or (file_version(path) if path.suffix.lower() in {'.dll','.pyd','.exe'} else ''),source=origin)
        records.append(row)
        # Verified upstream source archives are separately indexed and inspected;
        # these bytes must match public official archives, not private additions.
        if path.name.endswith('.tar.xz'):continue
        raw=path.read_bytes()
        lower=raw.lower()
        terms=['ultralytics','detectiontrainer','ultralytics_platform','ultralytics_thop','libx264','libx265']
        matches=[term for term in terms if term.encode() in lower or term.encode('utf-16-le') in lower]
        if matches:file_content_markers.append(dict(path=rel,terms=matches))
        for token_hash,u8,u16 in encoded:
            if u8 in raw or u16 in raw:private_hits.append(dict(path=rel,protected_token_sha256=token_hash))
        if path.suffix=='.zip':
            with zipfile.ZipFile(path) as z:
                for entry in z.namelist():
                    body=z.read(entry)
                    for token_hash,u8,u16 in encoded:
                        if u8 in body or u16 in body:private_hits.append(dict(path=rel+'!'+entry,protected_token_sha256=token_hash))
    for name in modules:
        if not name.startswith('ivad_app.'):continue
        code=pyz.extract(name)
        if not isinstance(code,types.CodeType):continue
        for text in constants(code):
            for value in tokens:
                if value in text:private_hits.append(dict(module=name,protected_token_sha256=hashlib.sha256(value.encode()).hexdigest()))
            if any(word in text.lower() for word in ['ultralytics','libx264','yolo']):
                content_markers.append(dict(module=name,literal=text[:500]))
    summary=dict(status='PASS' if not (bad_files or bad_modules or private_hits) else 'FAIL',
                 scope='Actual candidate files, PYZ code constants/modules, base_library ZIP; public Qt archives separately hash/name inspected',
                 file_count=len(records),bytes=sum(r['bytes'] for r in records),exe_sha256=sha(EXE),exe_bytes=EXE.stat().st_size,
                 bad_files=bad_files,bad_modules=bad_modules,private_hits=private_hits,
                 policy_or_generic_format_literals=content_markers,
                 file_content_markers=file_content_markers,
                 note='Deny-list/generic format strings are not installed engines; all matches retained for review. No license approval is inferred.')
    (OUT/'payload-files.json').write_text(json.dumps(records,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'payload-modules.json').write_text(json.dumps(modules,indent=2),encoding='utf8')
    (OUT/'payload-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    with (ROOT/'reports/P37D_LITE_PAYLOAD_FILES.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(records[0]));writer.writeheader();writer.writerows(records)
    print({k:v for k,v in summary.items() if k!='policy_or_generic_format_literals'})
    if summary['status']!='PASS':raise SystemExit('Candidate scan failed; do not deliver')

if __name__=='__main__':main()
