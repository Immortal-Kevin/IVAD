# SPDX-License-Identifier: Apache-2.0
"""Explicit one-delivery packaging; stdlib build tool, never a runtime dependency."""
import datetime, hashlib, json, re, shutil, struct, sys, zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
E = ROOT / 'governance/evidence'
AUTH = ROOT / 'governance/portable-authorization-20261026.json'
FILES = {'IVAD.Annotator.exe', 'IVAD.Annotator.exe.config', 'LICENSE', 'NOTICE',
         'THIRD_PARTY_NOTICES.txt', 'README_中文.txt', 'RUNTIME_REQUIREMENTS.txt',
         'DISTRIBUTION_COMPLIANCE.txt', '检查运行环境.cmd', 'BUILD.json', 'SBOM.json', 'checksums.sha256'}
SOURCES = ['src/Ids/Ids.cs', 'src/Ids/Work.cs'] + ['src/Annotator/'+s for s in
    ['Media.cs','VideoJobs.cs','Workflow.cs','App.cs','Interface.cs','UiChecks.cs',
     'AppDiagnostics.cs','DeploymentChecks.cs','Theme.xaml','Portable.config','Portable.manifest']]
ALLOWED_REFS = {'mscorlib','System','System.Core','System.Web.Extensions','System.IO.Compression',
    'System.IO.Compression.FileSystem','System.Windows.Forms','System.Drawing','System.Xaml',
    'WindowsBase','PresentationCore','PresentationFramework'}
def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p, value): Path(p).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def now(): return datetime.datetime.now(datetime.timezone.utc).isoformat()
def require(value, message):
    if not value: raise RuntimeError(message)
def active():
    a = read(AUTH)
    require(a['status']=='ACTIVE_SINGLE_DELIVERY' and a['authorization_id']=='IVAD-ANNOTATOR-PORTABLE-20261026-ONCE', 'Packaging authorization consumed or invalid')
    return a
def pe_imports(b):
    pe=struct.unpack_from('<I',b,0x3c)[0]
    require(b[pe:pe+4]==b'PE\0\0' and struct.unpack_from('<H',b,pe+4)[0]==0x8664, 'Not x64 PE')
    opt=pe+24
    require(struct.unpack_from('<H',b,opt)[0]==0x20b, 'Not PE32+')
    require(struct.unpack_from('<II',b,opt+112+14*8)[1]>=72, 'Missing CLR header')
    sec=opt+struct.unpack_from('<H',b,pe+20)[0]
    sections=[struct.unpack_from('<IIII',b,sec+40*i+8) for i in range(struct.unpack_from('<H',b,pe+6)[0])]
    def offset(rva):
        for vs,va,rs,rp in sections:
            if va<=rva<va+max(vs,rs): return rp+rva-va
        raise RuntimeError('Unmapped PE RVA')
    rva=struct.unpack_from('<I',b,opt+112+8)[0]
    names=[]
    if rva:
        pos=offset(rva)
        while any(b[pos:pos+20]):
            n=offset(struct.unpack_from('<I',b,pos+12)[0]);names.append(b[n:b.index(b'\0',n)].decode('ascii').lower());pos+=20
    return names
def inspect_payload(blobs, inspection):
    require(set(blobs)==FILES, 'Payload differs from exact allowlist')
    require(blobs['LICENSE']==(ROOT/'governance/licenses/Apache-2.0.txt').read_bytes(), 'LICENSE differs from audited Apache text')
    require(inspection['target_framework']=='.NETFramework,Version=v4.8', 'Wrong target framework')
    require(all(r.split(',')[0] in ALLOWED_REFS and 'PublicKeyToken=null' not in r for r in inspection['assembly_references']), 'Unexpected assembly reference')
    require(set(inspection['pinvoke'])=={'mfplat.dll','mfreadwrite.dll'}, 'Unexpected native dynamic dependency')
    require(inspection['resources']==['Ivad.Theme.xaml'], 'Unexpected embedded resource')
    require(not any(t.startswith('Ivad.Full') for t in inspection['types']), 'Private Full code leaked')
    native=pe_imports(blobs['IVAD.Annotator.exe'])
    # Pure managed x64 images can use the CLR directory with no native import thunk.
    require(set(native) in (set(),{'mscoree.dll'}), 'Unexpected native PE import')
    for name, data in blobs.items():
        for encoding in ['utf-8','utf-16-le']:
            text=data.decode(encoding, errors='ignore').lower()
            require(not re.search(r'[a-z]:[\\/]users[\\/]',text), 'Personal absolute path in '+name)
            require('kevin' not in text and 'ivad project' not in text, 'Personal/project path token in '+name)
        if name.endswith('.exe'):
            combined=data.decode('utf-8',errors='ignore')+' '+data.decode('utf-16-le',errors='ignore')
            require(not re.search(r'\b(?:ultralytics|rfdetr|torch|cuda|python\.exe|python3\d*\.dll)\b',combined,re.I), 'Unapproved runtime token in executable')
    checks={line.split('  ',1)[1]:line.split('  ',1)[0] for line in blobs['checksums.sha256'].decode('utf-8').splitlines()}
    require(set(checks)==FILES-{'checksums.sha256'}, 'Hash manifest membership differs')
    require(all(hashlib.sha256(blobs[n]).hexdigest()==v for n,v in checks.items()), 'Payload SHA256 mismatch')
    return native
def verify():
    c=read(E/'portable-candidate.json');zpath=ROOT/c['zip']
    require(sha(zpath)==c['zip_sha256'], 'ZIP digest differs from recorded candidate')
    inspection=read(ROOT/c['inspection'])
    with zipfile.ZipFile(zpath) as z:
        require(z.testzip() is None, 'ZIP CRC failure')
        require(len(z.namelist())==len(FILES) and set(z.namelist())=={'IVAD-Annotator/'+n for n in FILES}, 'Unexpected ZIP entries')
        blobs={n:z.read('IVAD-Annotator/'+n) for n in FILES}
    native=inspect_payload(blobs,inspection)
    build=json.loads(blobs['BUILD.json'])
    require(all(sha(ROOT/c['stage']/'source'/p)==v for p,v in build['source_sha256'].items()), 'Archived build sources changed')
    audit=dict(recorded_utc=now(),status='PASS',scope='actual ZIP contents; Policy B.1; one-time private test delivery only',zip=c['zip'],zip_sha256=c['zip_sha256'],file_count=len(FILES),files=[dict(path=n,bytes=len(blobs[n]),sha256=hashlib.sha256(blobs[n]).hexdigest(),license='Apache-2.0 self-authored/documentation') for n in sorted(blobs)],assembly_references=inspection['assembly_references'],pinvoke=inspection['pinvoke'],pe_imports=native,embedded_resources=inspection['resources'],third_party_bundled=[],runtime_bundled=False,privacy_scan='PASS: exact allowlist, no private path tokens/data/model/Full/credentials/log files',other_computers='NOT TESTED',normal_release_frozen=True)
    write(E/'portable-audit.json',audit)
    print(json.dumps(dict(audit='PASS',zip=c['zip'],files=len(FILES)),ensure_ascii=False))
    return c
def build(stage):
    a=active();stage=Path(stage).resolve()
    require(stage.is_relative_to(ROOT/'build/portable'), 'Stage outside build/portable')
    payload=stage/'IVAD-Annotator';inspection=read(stage/'binary-inspection.json')
    shutil.copyfile(ROOT/'src/Annotator/Portable.config',payload/'IVAD.Annotator.exe.config')
    shutil.copyfile(ROOT/'src/Annotator/LICENSE',payload/'LICENSE')
    (payload/'NOTICE').write_bytes((ROOT/'src/Annotator/NOTICE').read_bytes()+b'\n'+(ROOT/'src/Ids/NOTICE').read_bytes())
    for name in ['THIRD_PARTY_NOTICES.txt','README_中文.txt','RUNTIME_REQUIREMENTS.txt','DISTRIBUTION_COMPLIANCE.txt','检查运行环境.cmd']:
        shutil.copyfile(ROOT/'packaging/annotator'/name,payload/name)
    sourcehash={s:sha(ROOT/s) for s in SOURCES}
    for s in SOURCES:
        archived=stage/'source'/s;archived.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/s,archived)
    buildinfo=dict(product='IVAD Annotator',version=a['build_id'],file_version=a['file_version'],build_utc=now(),architecture='Windows x64',language='C# 5',target='.NET Framework 4.8 / CLR v4.0',compiler=inspection['compiler_file_version'],reference_environment='.NET Framework 4.8.1 Windows system assemblies; pure 4.8 target machine NOT TESTED',mode='framework-dependent; runtime NOT bundled',configuration='optimized, debug symbols disabled, asInvoker, system DPI aware',source_sha256=sourcehash,assembly_references=inspection['assembly_references'],native_prerequisites=inspection['pinvoke'],command='csc /target:winexe /platform:x64 /langversion:5 /optimize+ /debug-; explicit Annotator/Ids sources; embedded own theme; version metadata; manifest',authorization=a['authorization_id'],signed=False)
    write(payload/'BUILD.json',buildinfo)
    write(payload/'SBOM.json',dict(bomFormat='CycloneDX',specVersion='1.5',version=1,metadata={'timestamp':now(),'component':{'bom-ref':'ivad-annotator','type':'application','name':'IVAD Annotator','version':a['build_id'],'licenses':[{'license':{'id':'Apache-2.0'}}],'hashes':[{'alg':'SHA-256','content':sha(payload/'IVAD.Annotator.exe')}]}},components=[{'bom-ref':'ivad-ids','type':'library','name':'IVAD IDS','version':'1.0','licenses':[{'license':{'id':'Apache-2.0'}}],'properties':[{'name':'ivad:linkage','value':'self-authored code compiled into application'}]}],dependencies=[{'ref':'ivad-annotator','dependsOn':['ivad-ids']},{'ref':'ivad-ids','dependsOn':[]}],properties=[{'name':'ivad:external-runtime','value':'Windows .NET Framework 4.8+ / WPF / Media Foundation; Microsoft terms, NOT bundled, NOT Apache'},{'name':'ivad:third-party-bundled-count','value':'0'},{'name':'ivad:distribution','value':'one-time local private test ZIP; other computers NOT TESTED'}]))
    (payload/'checksums.sha256').write_text(''.join(sha(payload/n)+'  '+n+'\n' for n in sorted(FILES-{'checksums.sha256'})),encoding='utf-8')
    require({p.name for p in payload.iterdir()}==FILES,'Unexpected staging files')
    inspect_payload({n:(payload/n).read_bytes() for n in FILES},inspection)
    target=ROOT/'dist/candidates'/('IVAD-Annotator-'+a['build_id']+'-'+stage.name+'.zip');target.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(target,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for n in sorted(FILES): z.write(payload/n,'IVAD-Annotator/'+n)
    write(E/'portable-candidate.json',dict(created_utc=now(),zip=target.relative_to(ROOT).as_posix(),zip_sha256=sha(target),bytes=target.stat().st_size,stage=stage.relative_to(ROOT).as_posix(),inspection=(stage/'binary-inspection.json').relative_to(ROOT).as_posix(),build_id=a['build_id'],binary_sha256=sha(payload/'IVAD.Annotator.exe'),status='CANDIDATE_NOT_YET_DELIVERED'))
    verify()
def finalize():
    a=active();c=verify();local=read(E/'portable-independent.json');gate=read(E/'release_gate.json')
    require(local['candidate_sha256']==c['zip_sha256'] and local['status']=='PASS', 'Independent execution must pass for exact candidate')
    require(gate['engineering_status']=='PASS','Post-package full Release Gate must pass')
    build=read(ROOT/c['stage']/'IVAD-Annotator/BUILD.json')
    require(all(sha(ROOT/p)==v for p,v in build['source_sha256'].items()),'Current sources differ before finalization; rebuild this candidate')
    target=ROOT/'dist/IVAD-Annotator-v1.1-win-x64-portable.zip'
    require(not target.exists(), 'Final file already exists; refuse overwrite')
    shutil.copyfile(ROOT/c['zip'],target)
    require(sha(target)==c['zip_sha256'],'Final copy mismatch')
    c['candidate_archive']=c['zip'];c['zip']=target.relative_to(ROOT).as_posix();c['status']='FINAL_PRIVATE_TEST_DELIVERY';write(E/'portable-candidate.json',c)
    verify()
    a.update(status='CONSUMED_FROZEN',completed_utc=now(),delivered_zip=c['zip'],delivered_sha256=c['zip_sha256']);write(AUTH,a)
    (target.parent/(target.name+'.sha256')).write_text(c['zip_sha256']+'  '+target.name+'\n',encoding='utf-8')
    print(json.dumps(dict(delivered=c['zip'],bytes=c['bytes'],sha256=c['zip_sha256'],packaging_authorization='CONSUMED_FROZEN'),ensure_ascii=False))

if __name__=='__main__':
    try:
        if sys.argv[1]=='build': build(sys.argv[2])
        elif sys.argv[1]=='verify': verify()
        elif sys.argv[1]=='finalize': finalize()
        else: raise RuntimeError('Unknown action')
    except Exception as e:
        write(E/('portable-failure-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.json'),dict(status='FAIL',error=str(e),recorded_utc=now()))
        raise
