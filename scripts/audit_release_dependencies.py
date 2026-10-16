"""Read installed metadata and license notices only; no pip/install or GPU imports."""
import argparse,csv,hashlib,json,sys,shutil
from pathlib import Path
from importlib import metadata
from packaging.requirements import Requirement
from packaging.utils import canonicalize_name
p=argparse.ArgumentParser();p.add_argument('--label',required=True);p.add_argument('--output',required=True);p.add_argument('--roots',nargs='+',required=True);a=p.parse_args();out=Path(a.output)/a.label;out.mkdir(parents=True,exist_ok=False)
dists={canonicalize_name(d.metadata['Name']):d for d in metadata.distributions() if d.metadata.get('Name')};pending=list(a.roots);selected={};missing=[]
while pending:
 name=canonicalize_name(pending.pop())
 if name in selected:continue
 if name not in dists:missing.append(name);continue
 d=dists[name];selected[name]=d
 for raw in d.requires or []:
  req=Requirement(raw)
  if req.marker is None or req.marker.evaluate({'extra':''}):pending.append(req.name)
rows=[]
for name,d in sorted(selected.items()):
 files=[];binaries=[]
 for f in d.files or []:
  fn=Path(str(f)).name.lower();src=Path(d.locate_file(f))
  if not src.is_file():continue
  if src.suffix.lower() in ['.dll','.pyd']:binaries.append({'path':str(f),'bytes':src.stat().st_size})
  if any(x in str(f).lower() for x in ['license','licence','copying','notice','copyright']) and src.suffix.lower() not in ['.dll','.pyd','.py','.pyc']:
   # Keep each wheel's original notices unmodified under a distinct component folder.
   target=out/'notices'/name/str(f).replace('..','_parent_');target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(src,target)
   files.append({'installed_path':str(f),'audit_copy':str(target.relative_to(out)),'sha256':hashlib.sha256(src.read_bytes()).hexdigest()})
 meta=d.metadata;rows.append({'name':meta['Name'],'version':d.version,'license_expression':meta.get('License-Expression'),'license_field':meta.get('License'),'license_classifiers':[x for x in meta.get_all('Classifier',[]) if x.startswith('License ::')],'requires_python':meta.get('Requires-Python'),'requires_dist':d.requires or [],'license_files':files,'native_binaries':binaries,'metadata_sha256':hashlib.sha256((d.read_text('METADATA') or '').encode()).hexdigest(),'direct_url':d.read_text('direct_url.json')})
result={'label':a.label,'python':sys.version,'roots':a.roots,'missing':sorted(set(missing)),'packages':rows,'limitation':'installed runtime closure snapshot, not a wheel hash lock or final payload SBOM'}
(out/'inventory.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8');(out/'requirements-installed.txt').write_text('\n'.join(r['name']+'=='+r['version'] for r in rows)+'\n',encoding='utf8');print(json.dumps({'label':a.label,'packages':len(rows),'missing':result['missing'],'notice_files':sum(len(r['license_files']) for r in rows),'native_files':sum(len(r['native_binaries']) for r in rows)}))
