"""Repeatable B.1 gate. Does not package, sign, upload or modify system settings."""
import ast,hashlib,importlib.metadata as md,json,re,sys,zipfile,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];G=ROOT/'governance';E=G/'evidence'
def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
policy=json.loads((G/'release-policy.json').read_text(encoding='utf-8'))
checks=[]
def check(code,status,mode,detail):checks.append(dict(id=code,status=status,mode=mode,detail=detail))
installed=[];forbidden=[]
if not policy.get('release_frozen'):forbidden.append('Release freeze unexpectedly disabled')
if policy.get('ffmpeg_enabled') or policy.get('training_enabled'):forbidden.append('Backend enabled without implemented artifact approval gate')
for env in (ROOT/'.venvs').iterdir():
    for d in md.distributions(path=[str(env/'Lib/site-packages')]):
        name=d.metadata['Name'];lic=d.metadata.get('License-Expression') or d.metadata.get('License') or 'UNKNOWN'
        installed.append(dict(environment=env.name,name=name,version=d.version,license=lic[:2000],scope='retired legacy / audit tooling; NEVER candidate'))
        if name.lower().startswith('ultralytics') or re.search(r'\b(?:A?GPL(?:[- ]|v?\d)|PML[- ]?1)',lic):forbidden.append(name)
    # Also inspect vendored distributions (top-level inventory is insufficient).
    for path in (env/'Lib/site-packages').rglob('*.dist-info/METADATA'):
        text=path.read_text(encoding='utf-8',errors='replace')
        if re.search(r'^Name: ultralytics',text,re.M|re.I):forbidden.append(str(path.relative_to(ROOT)))
write(E/'installed_scan.json',installed)
wheel_scan=[]
for p in (ROOT/'artifacts').rglob('*.whl'):
    record=dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=sha(p),scope='retired cache, excluded')
    try:
        with zipfile.ZipFile(p) as z:
            metas=[n for n in z.namelist() if n.endswith('.dist-info/METADATA')]
            texts=[z.read(n).decode(errors='replace') for n in metas]
            if any(re.search(r'^Name: ultralytics',t,re.M|re.I) for t in texts):forbidden.append(str(p.relative_to(ROOT)))
            record['metadata_names']=[re.search(r'^Name: (.+)',t,re.M).group(1) for t in texts if re.search(r'^Name: (.+)',t,re.M)]
    except Exception as ex:record['error']=str(ex);forbidden.append(str(p.relative_to(ROOT)))
    wheel_scan.append(record)
write(E/'wheel_scan.json',wheel_scan)
runtime_files=list((ROOT/'src/Annotator').rglob('*.cs'))+list((ROOT/'src/Ids').rglob('*.cs'))
runtime_files+=list((ROOT/'src/Annotator').rglob('*.xaml'))
code='\n'.join(p.read_text(encoding='utf-8-sig') for p in runtime_files)
bad_code=[s for s in ['ultralytics','rfdetr','torch','cuda','xpu','System.Net','HttpClient','WebClient','Socket'] if re.search(r'\b'+re.escape(s)+r'\b',code,re.I)]
references=json.loads((E/'assembly_references.json').read_text(encoding='utf-8-sig'))
allowed={'mscorlib','System','System.Core','System.Web.Extensions','System.IO.Compression','System.IO.Compression.FileSystem','System.Windows.Forms','System.Drawing','System.Xaml','WindowsBase','PresentationCore','PresentationFramework'}
bad_refs=[r['Name'] for r in references if r['Name'] not in allowed]
last=Path((ROOT/'build/test-data/latest.txt').read_text().strip());tests=json.loads((last/'results.json').read_text(encoding='utf-8-sig'))
wpf_path=last/'wpf-checks/results.json'
wpf=json.loads(wpf_path.read_text(encoding='utf-8-sig')) if wpf_path.exists() else {'passed':0,'failed':1}
ui=(E/'annotator-smoke.png').exists() and not (E/'annotator-smoke.png.error.txt').exists()
exe=ROOT/'build/dev/Ivad.Annotator.Dev.exe';binary=exe.read_bytes();pe=struct.unpack_from('<I',binary,0x3c)[0];machine=struct.unpack_from('<H',binary,pe+4)[0]
candidates=[]
for rel in policy['candidate_files']:
    p=ROOT/rel
    if p.resolve().parent!=(ROOT/'build/dev').resolve() or p.name!='Ivad.Annotator.Dev.exe':forbidden.append('unexpected candidate '+rel)
    candidates.append(dict(path=rel,sha256=sha(p),bytes=p.stat().st_size,license='Apache-2.0',role='development-only not installer'))
unexpected=[p.name for p in (ROOT/'build/dev').iterdir() if p.is_file() and p.name not in {'Ivad.Annotator.Dev.exe','Ivad.Tests.exe'}]
for p in (ROOT/'build').rglob('*'):
    if p.is_file() and (p.suffix.lower() in {'.msi','.msix','.appx'} or p.name.lower().startswith(('setup.','installer.'))):forbidden.append('Unauthorized installer '+str(p.relative_to(ROOT)))
environment=[]
for name in ['mf.dll','mfplat.dll','mfreadwrite.dll']:
    p=Path(__import__('os').environ['WINDIR'])/'System32'/name
    environment.append(dict(name=name,path=str(p),sha256=sha(p),license='Microsoft Windows OS terms (NOT Apache)',redistributed=False))
write(G/'SBOM.json',dict(bomFormat='CycloneDX',specVersion='1.5',version=1,metadata={'component':{'type':'application','name':'IVAD Annotator','version':'1.1-dev'}},components=[{'type':'application','name':'IVAD Annotator / IDS self-authored code','version':'1.1-dev','licenses':[{'license':{'id':'Apache-2.0'}}],'hashes':[{'alg':'SHA-256','content':sha(exe)}]}],properties=[{'name':'ivad:distribution-status','value':'NOT VERIFIED'},{'name':'ivad:external-runtime','value':'Windows .NET Framework / Media Foundation; not bundled'}]))
write(E/'runtime_environment.json',environment)
write(E/'candidate_manifest.json',dict(release_frozen=policy['release_frozen'],files=candidates,external_assemblies=references,unexpected_files=unexpected))
missing=[f for f in policy['mandatory_materials'] if not (G/f).exists()]
for relative in ['src/Annotator/LICENSE','src/Annotator/NOTICE','src/Ids/LICENSE','src/Ids/NOTICE','src/Full/LICENSE']:
    if not (ROOT/relative).is_file():missing.append(relative)
for component in ['Annotator','Ids']:
    license_file=ROOT/'src'/component/'LICENSE'
    if license_file.exists() and sha(license_file)!=sha(G/'licenses/Apache-2.0.txt'):missing.append(component+' LICENSE differs from recorded original')
gui_path=E/'windows_gui_attempt.json'
gui=json.loads(gui_path.read_text(encoding='utf-8')) if gui_path.exists() else {'status':'NOT TESTED','reason':'No real GUI evidence'}
# A startup screenshot or internal service calls never satisfy interactive acceptance.
gui_status='NOT TESTED'
check('A','PASS' if tests['failed']==0 else 'FAIL','actual service / media / child-process tests','Persistence, geometry, full/delta IDS, hashes, cancellation and rollback; no real mouse workflow claim')
check('B','NOT TESTED' if tests['failed']==0 and wpf['failed']==0 and ui else 'FAIL','actual WPF startup; in-process controls / synthetic layout; real GUI NOT TESTED',str(tests['passed'])+' service/media passed / '+str(tests['failed'])+' failed; '+str(wpf['passed'])+' WPF checks passed / '+str(wpf['failed'])+' failed; computer-use rejected: '+gui.get('raw_launch_response','No GUI evidence'))
check('C','PASS' if machine==0x8664 else 'FAIL','actual compilation and PE inspection','Windows x64 development EXE; installer NOT TESTED')
check('D','PASS' if not bad_code and not bad_refs else 'FAIL','static source + actual assembly dependency inspection','Unexpected code tokens='+str(bad_code)+'; unexpected assembly refs='+str(bad_refs)+'; Full separately BLOCKED')
check('E','PASS' if not forbidden else 'FAIL','installed dist-info + wheel identity + source/PE inventory','Retired package/binary provenance is excluded, never automatically approved; violations='+str(forbidden))
check('F','PASS','not applicable, absence checked','No FFmpeg in candidate; exception is not exercised')
check('G','BLOCKED','official pinned source/metadata/artifact review','RF-DETR Full closure, weights and NVIDIA run not approved; no downloaded weights or active model dependency')
check('H','NOT TESTED','environment registry + static boundary','Windows OS APIs not redistributed; clean target/CUDA SDK distribution not verified')
check('I','PASS' if not missing else 'FAIL','static documents and file hashes','Missing materials='+str(missing)+'; actual installer content NOT TESTED')
check('J','PASS' if not unexpected and len(candidates)==1 else 'FAIL','explicit development candidate allowlist','Only self-built Annotator EXE; no dataset/model/font/private Full in candidate; full repository is NOT a distribution')
check('K','NOT TESTED','static no-network source/assembly check; actual local execution','No network API in application; physical network-denied run NOT TESTED; no system proxy/firewall changes')
check('L','NOT TESTED','actual IDS rollback tests + static lifecycle design','Installer/upgrade/uninstall/clean machine and power-loss recovery NOT TESTED; no installer authorized')
annotator='BLOCKED' if any(c['status']=='FAIL' for c in checks) else 'NOT VERIFIED'
full='BLOCKED'
engineering='FAIL' if any(c['status']=='FAIL' for c in checks) else 'PASS'
write(E/'release_gate.json',dict(recorded_utc=__import__('datetime').datetime.now(__import__('datetime').timezone.utc).isoformat(),policy='B.1',release_frozen=True,engineering_status=engineering,gui_status=gui_status,products={'Annotator':annotator,'Full/NVIDIA':full},checks=checks,tests=str(last.relative_to(ROOT)),gui_evidence=str(gui_path.relative_to(ROOT)),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in runtime_files}))
lines=['# Release Readiness — IVAD v1.1','','工程检查: **'+engineering+'**；真实 GUI: **'+gui_status+'**。','Annotator: **'+annotator+'**  ','Full / NVIDIA: **'+full+'**  ','正式发行冻结：**true**。开发EXE不是安装程序。','','| 检查 | 状态 | 证据方式 | 范围/限制 |','|---|---|---|---|']
lines += ['| '+c['id']+' | '+c['status']+' | '+c['mode']+' | '+c['detail']+' |' for c in checks]
lines+=['','原始结果：evidence/release_gate.json、installed_scan.json、wheel_scan.json、candidate_manifest.json、assembly_references.json、runtime_environment.json和build/test-data。','', '任何历史环境、审计下载、候选元数据均不属于已批准发行依赖。未完成的证据不能由此脚本自动升级为READY。']
if (E/'portable-candidate.json').exists():
    candidate=json.loads((E/'portable-candidate.json').read_text(encoding='utf-8-sig'))
    audit=json.loads((E/'portable-audit.json').read_text(encoding='utf-8-sig')) if (E/'portable-audit.json').exists() else {}
    local=json.loads((E/'portable-independent.json').read_text(encoding='utf-8-sig')) if (E/'portable-independent.json').exists() else {}
    material=audit.get('status','NOT TESTED') if audit.get('zip_sha256')==candidate['zip_sha256'] else 'NOT TESTED'
    independent=local.get('status','NOT TESTED') if local.get('candidate_sha256')==candidate['zip_sha256'] else 'NOT TESTED'
    lines+=['','## 本次一次性 Annotator 便携测试交付','','- A 实际ZIP内容/材料审计：'+material+'（脚本随后再次核对实际ZIP）。','- B 本机独立目录可执行/内部WPF验收：'+independent+'；真实鼠标/物理快捷键仍NOT TESTED。','- C 其他Windows电脑：NOT TESTED。','- 指定包：'+candidate['zip']+'；普通发行/后续打包冻结保持，详见portable-authorization-20261026.json。']
(G/'RELEASE_READINESS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
print(json.dumps(dict(annotator=annotator,full=full,tests=tests['passed'],failures=tests['failed'],forbidden=forbidden,missing=missing),ensure_ascii=False))
sys.exit(1 if annotator=='BLOCKED' else 0)
