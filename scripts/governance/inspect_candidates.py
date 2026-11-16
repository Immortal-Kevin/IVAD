"""Download small candidate wheels for LICENSE review only, never install/import them."""
import hashlib,json,subprocess,zipfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];OUT=ROOT/'governance/evidence/rfdetr'
report=json.loads((OUT/'resolution.json').read_text(encoding='utf-8'))
rows=[]
for p in report['packages']:
    if p['name'] not in {'rfdetr','tqdm','certifi','supervision','torch-hungarian'}:continue
    candidates=[c for c in p['windows_candidates'] if 'none-any' in c['filename'] and c['size']<3_000_000]
    if not candidates:continue
    c=candidates[0];tmp=OUT/(c['filename']+'.review-only');dest=OUT/(p['name']+'-artifact-evidence');dest.mkdir(exist_ok=True)
    r=subprocess.run(['curl.exe','--fail','--location','--silent','--show-error','--connect-timeout','8','--max-time','30','--output',str(tmp),c['url']],capture_output=True,timeout=35)
    row=dict(name=p['name'],version=p['version'],url=c['url'],expected_sha256=c['sha256'],installed=False)
    try:
        if r.returncode:raise RuntimeError(r.stderr.decode(errors='replace'))
        sha=hashlib.sha256(tmp.read_bytes()).hexdigest()
        if sha!=c['sha256']:raise RuntimeError('Hash mismatch')
        row['sha256']=sha;row['files']=[];row['source_calls']=[]
        with zipfile.ZipFile(tmp) as z:
            for n in z.namelist():
                if 'license' in n.lower() or n.endswith('/METADATA') or n.lower().endswith('notice'):
                    b=z.read(n);fn=n.replace('/','__');(dest/fn).write_bytes(b);row['files'].append(dict(path=fn,sha256=hashlib.sha256(b).hexdigest()))
                if n.endswith('.py') and p['name']=='rfdetr':
                    for i,line in enumerate(z.read(n).decode(errors='replace').splitlines(),1):
                        if any(t in line for t in ['import tqdm','from tqdm','import requests','from requests','import supervision','from supervision','import roboflow','from roboflow','download_pretrain']):
                            row['source_calls'].append(dict(file=n,line=i,text=line.strip()[:250]))
        row['status']='ARTIFACT_INSPECTED_NOT_APPROVED'
    except Exception as e:row['status']='BLOCKED';row['error']=str(e)
    finally:
        # Inspection-only wheel is not retained as an installable/redistributable artifact.
        if tmp.exists():tmp.unlink()
    rows.append(row)
(OUT/'artifact_review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
print([(r['name'],r['status']) for r in rows])
