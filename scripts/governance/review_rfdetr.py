"""Metadata-only recursive resolver/audit; never installs or downloads weights.
Uses pip's vendored packaging strictly as registered development tooling.
Candidate metadata is NOT artifact/license approval.
"""
import concurrent.futures, hashlib, json, time, urllib.request, subprocess
from pathlib import Path
from pip._vendor.packaging.requirements import Requirement
from pip._vendor.packaging.version import Version, InvalidVersion
from pip._vendor.packaging.markers import default_environment
from pip._vendor.packaging.tags import cpython_tags,compatible_tags
from pip._vendor.packaging.utils import parse_wheel_filename
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'governance/evidence/rfdetr'; OUT.mkdir(parents=True,exist_ok=True)
env=default_environment(); env.update(python_version='3.12',python_full_version='3.12.0',sys_platform='win32',platform_system='Windows',platform_machine='AMD64',os_name='nt',extra='')
def get(url,path):
    if path.exists(): return path.read_bytes()
    tmp=path.with_suffix(path.suffix+'.pending')
    r=subprocess.run(['curl.exe','--fail','--location','--compressed','--silent','--show-error','--connect-timeout','8','--max-time','20','--max-filesize','12582912','--output',str(tmp),url],capture_output=True,timeout=25)
    if r.returncode:
        if tmp.exists(): tmp.unlink()
        raise RuntimeError(r.stderr.decode(errors='replace')[-600:])
    tmp.replace(path);return path.read_bytes()
def data(name,version=None):
    suffix=('/'+version) if version else ''
    return json.loads(get('https://pypi.org/pypi/'+name+suffix+'/json',OUT/(name+('-'+version if version else '')+'.json')))
def normalize(s): return s.lower().replace('_','-').replace('.','-')
def choose(name,specs):
    exact=[s.version for spec in specs for s in spec if s.operator=='==' and '*' not in s.version]
    if exact:
        v=Version(exact[0])
        if all(v in s for s in specs): return data(name,str(v))
    # Huge release-history documents: parse only the complete leading info object,
    # then request the small fixed-version document. Partial history is never trusted.
    if name in {'regex','aiohttp','multidict','yarl'}:
        prefix=OUT/(name+'.info-prefix')
        if not prefix.exists():
            subprocess.run(['curl.exe','--fail','--location','--compressed','--silent','--show-error','--connect-timeout','5','--max-time','8','--output',str(prefix),'https://pypi.org/pypi/'+name+'/json'],capture_output=True,timeout=12)
        text=prefix.read_text(encoding='utf-8',errors='replace')
        start=text.index('"info":')+7
        info,_=json.JSONDecoder().raw_decode(text[start:])
        if all(Version(info['version']) in s for s in specs):return data(name,info['version'])
        raise RuntimeError('Latest metadata does not meet constraints; explicit older-version audit required')
    base=data(name)
    candidates=[]
    for v,files in base.get('releases',{}).items():
        try: ver=Version(v)
        except InvalidVersion: continue
        if ver.is_prerelease or not files or all(f.get('yanked') for f in files): continue
        if not all(ver in s for s in specs): continue
        if not any(not f.get('requires_python') or Version('3.12.0') in __import__('pip._vendor.packaging.specifiers',fromlist=['SpecifierSet']).SpecifierSet(f['requires_python']) for f in files): continue
        candidates.append(ver)
    if not candidates: raise ValueError('No candidate '+name+' '+str(specs))
    return data(name,str(max(candidates)))
constraints={}; extras={'rfdetr':{'train'}}; selected={}; failures=[]
pending={'rfdetr'}
for round_number in range(18):
    if not pending: break
    names=sorted(pending); pending=set()
    def resolve(n):
        try: return n,choose(n,constraints.get(n,[])),None
        except Exception as e: return n,None,str(e)
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
        results=list(pool.map(resolve,names))
    for n,d,error in results:
        if error: failures.append({'name':n,'error':error}); continue
        selected[n]=d
        for raw in d['info'].get('requires_dist') or []:
            req=Requirement(raw)
            if req.marker and not any(req.marker.evaluate(dict(env,extra=e)) for e in {''}|extras.get(n,set())): continue
            dep=normalize(req.name)
            specs=constraints.setdefault(dep,[])
            if str(req.specifier) not in [str(s) for s in specs]: specs.append(req.specifier)
            old_extra=extras.get(dep,set()).copy(); extras.setdefault(dep,set()).update(req.extras)
            if dep not in selected or not all(Version(selected[dep]['info']['version']) in s for s in specs) or extras[dep]!=old_extra: pending.add(dep)
    print('round',round_number+1,'resolved',len(selected),'pending',len(pending),flush=True)
else: failures.append({'error':'Bounded resolver did not converge'})
rows=[]
compatible=set(cpython_tags((3,12),['cp312'],['win_amd64']))|set(compatible_tags((3,12),'cp312',['win_amd64']))
def target_wheel(filename):
    try:return bool(parse_wheel_filename(filename)[3]&compatible)
    except Exception:return False
for n,d in sorted(selected.items()):
    info=d['info']; license_text=info.get('license_expression') or info.get('license') or ''
    candidates=[u for u in d.get('urls',[]) if target_wheel(u['filename'])]
    rows.append(dict(name=n,version=info['version'],declared_license=license_text,
        classifiers=[c for c in info.get('classifiers',[]) if c.startswith('License')],
        dependencies=info.get('requires_dist') or [],extras=sorted(extras.get(n,set())),
        windows_candidates=[dict(filename=u['filename'],url=u['url'],sha256=u['digests']['sha256'],size=u['size']) for u in candidates],
        disposition='BLOCKED_PENDING_ARTIFACT_AND_BUNDLED_LICENSE_REVIEW'))
for n,d in selected.items():
    for raw in d['info'].get('requires_dist') or []:
        req=Requirement(raw)
        if req.marker and not any(req.marker.evaluate(dict(env,extra=e)) for e in {''}|extras.get(n,set())):continue
        dep=normalize(req.name)
        if dep not in selected or Version(selected[dep]['info']['version']) not in req.specifier:
            failures.append({'parent':n,'requirement':raw,'error':'Final closure dependency unsatisfied'})
root=selected.get('rfdetr',{}).get('info',{}).get('version')
if root:
    for name,path in [('pyproject.toml','pyproject.toml'),('LICENSE','LICENSE'),('README.md','README.md')]:
        try: get('https://raw.githubusercontent.com/roboflow/rf-detr/'+root+'/'+path,OUT/('upstream-'+name))
        except Exception as e: failures.append({'source':path,'error':str(e)})
report=dict(scope='Windows x64 CPython 3.12, rfdetr[train], metadata resolution only',root_version=root,
    status='BLOCKED',resolver='bounded constraint accumulation (not a complete backtracking solver)',
    packages=rows,errors=failures,pending=sorted(pending),weights_downloaded=False,installed=False)
(OUT/'resolution.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'candidate.lock.txt').write_text('\n'.join(r['name']+'=='+r['version'] for r in rows)+'\n',encoding='utf-8')
print('DONE',len(rows),'candidate packages, errors',len(failures),'root',root,flush=True)
