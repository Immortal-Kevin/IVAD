"""Bounded PE dependency evidence, never a distribution approval.

Inputs are observed module lists and the previously audited runtime closure.
Only candidate roots are indexed. Historical Qt/YOLO/FFmpeg environments are not read.
"""
import argparse,base64,hashlib,importlib.metadata as md,json,os
from collections import defaultdict
from pathlib import Path
import pefile

def sha(p):
    with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--root',action='append',type=Path,required=True)
    ap.add_argument('--observed',action='append',type=Path,required=True);ap.add_argument('--prior',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    roots=[p.resolve() for p in args.root];index=defaultdict(list);owners={};packages={}
    for root in roots:
        for path in root.rglob('*'):
            if path.is_file() and path.suffix.lower() in {'.pyd','.dll'}:index[path.name.lower()].append(path)
        for dist in md.distributions(path=[str(root)]):
            name=dist.metadata['Name'];key=name+'=='+dist.version+'@'+str(roots.index(root))
            notices=[]
            for f in dist.files or []:
                path=Path(dist.locate_file(f)).resolve()
                if path.suffix.lower() in {'.pyd','.dll'}:owners[path]=(key,f.hash)
                if any(t in path.name.lower() for t in ('license','licence','notice','copying','third-party')) and path.is_file():
                    notices.append({'path':str(path),'sha256':sha(path)})
            packages[key]={'name':name,'version':dist.version,'license_expression':dist.metadata.get('License-Expression'),
                'license_metadata':dist.metadata.get('License'),'upstream':dist.metadata.get_all('Project-URL',[]),
                'notices':notices,'source_binding':'installed RECORD only; upstream wheel hash binding not established'}
    observed=[]
    for path in args.observed:
        data=json.loads(path.read_text(encoding='utf-8-sig'))
        observed.extend(data.get('loaded_modules',[]) if isinstance(data,dict) else data)
    observed=[Path(p).resolve() for p in observed if isinstance(p,str) and Path(p).is_file()]
    loaded={p.name.lower():p for p in observed};queue=list(observed);seen=set();rows=[]
    while queue:
        p=queue.pop()
        if p in seen:continue
        seen.add(p)
        if p.suffix.lower() not in {'.dll','.pyd','.exe'}:continue
        package,record=owners.get(p,(None,None));imports=[]
        is_system=p.is_relative_to(Path(os.environ['SystemRoot']).resolve())
        try:
            pe=pefile.PE(str(p),fast_load=True)
            pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_IMPORT'],pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_DELAY_IMPORT']])
            deps=[d.dll.decode() for attr in ('DIRECTORY_ENTRY_IMPORT','DIRECTORY_ENTRY_DELAY_IMPORT') for d in getattr(pe,attr,[])];pe.close()
        except pefile.PEFormatError:deps=[]
        for name in sorted(set(deps),key=str.lower):
            key=name.lower();found=loaded.get(key)
            if found is None and (p.parent/name).is_file():found=(p.parent/name).resolve()
            if found is None and len(index[key])==1:found=index[key][0]
            if found is not None:
                resolution='observed' if key in loaded else 'candidate-file'
                if not is_system:queue.append(found)
            else:resolution='windows-api-set' if key.startswith(('api-ms-','ext-ms-')) else 'AMBIGUOUS' if len(index[key])>1 else 'UNRESOLVED'
            imports.append({'name':name,'resolution':resolution,'path':str(found) if found else None})
        record_matches=None;checksum=sha(p)
        if record and record.mode=='sha256':record_matches=base64.urlsafe_b64encode(bytes.fromhex(checksum)).decode().rstrip('=')==record.value
        rows.append({'path':str(p),'sha256':checksum,'bytes':p.stat().st_size,'package':package,
            'record_hash_matches':record_matches,'origin':'Windows system prerequisite; do not copy' if is_system else 'candidate installed native file',
            'redistribution':'NOT_CLEARED','imports':imports})
    needed={r['package'] for r in rows if r['package']}
    result={'PACKAGING_FREEZE':True,'DISTRIBUTION_STATUS':'BLOCKED','prior_manifest_sha256':sha(args.prior),
        'scope':'observed native modules plus PE normal/delay imports; dynamic unexercised loads and statically linked components still require source evidence',
        'roots':[str(p) for p in roots],'observations':[{'path':str(p),'sha256':sha(p)} for p in args.observed],
        'packages':{k:v for k,v in packages.items() if k in needed},'files':sorted(rows,key=lambda r:r['path'].lower())}
    args.output.write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf8')
    print(json.dumps({'native_files':len(rows),'packages':len(needed),'unresolved_edges':sum(i['resolution'] in {'AMBIGUOUS','UNRESOLVED'} for r in rows for i in r['imports'])}))

if __name__=='__main__':main()
