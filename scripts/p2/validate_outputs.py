"""Independent read-back of real exported files, numerical geometry and hashes."""
import json,sys,hashlib
from pathlib import Path
import yaml
import av
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from ivad_app.video.reader import FileVideoSource
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
out=ROOT/'artifacts/p2';results=[]
for manifest in sorted(out.glob('gui-evidence-*/IVAD-*/export_manifest.json')):
    folder=manifest.parent;index=json.loads(manifest.read_text(encoding='utf-8'));native=json.loads((folder/'ivad_native.json').read_text(encoding='utf-8'))
    for name,checksum in index['files'].items():assert digest(folder/name)==checksum
    mapping={r['uuid']:r['class_id'] for r in native['classes']};seen={};groups={};objects=0
    for s in native['samples']:
        assert digest(folder/s['image'])==s['sha256']
        assert s['sha256'] not in seen;seen[s['sha256']]=s['split']
        groups.setdefault(s['camera'] or s['media_id'],set()).add(s['split'])
        objects+=len(s['annotation']['objects'])
        if index['format'].startswith('yolo'):
            lines=(folder/'labels'/s['split']/(s['frame_id']+'.txt')).read_text(encoding='utf-8').splitlines()
            assert len(lines)==len(s['annotation']['objects'])
            for line,obj in zip(lines,s['annotation']['objects']):
                values=line.split();assert int(values[0])==mapping[obj['label_id']];v=list(map(float,values[1:]));assert all(0<=x<=1 for x in v)
                pts=obj['geometry']
                if index['format']=='yolo_segment':
                    assert obj['kind']=='polygon' and len(v)==2*len(pts)
                    for i,(x,y) in enumerate(pts):assert abs(v[2*i]*s['width']-x)<1e-5 and abs(v[2*i+1]*s['height']-y)<1e-5
                else:
                    if obj['kind']=='polygon':x=min(p[0] for p in pts);y=min(p[1] for p in pts);w=max(p[0] for p in pts)-x;h=max(p[1] for p in pts)-y
                    else:x,y,w,h=pts
                    assert len(v)==4
                    expected=[x+w/2,y+h/2,w,h];actual=[v[0]*s['width'],v[1]*s['height'],v[2]*s['width'],v[3]*s['height']]
                    assert all(abs(a-b)<1e-5 for a,b in zip(expected,actual))
        elif index['format']=='coco':
            coco=json.loads((folder/f"instances_{s['split']}.json").read_text(encoding='utf-8'));image=next(i for i in coco['images'] if i['frame_uuid']==s['frame_id'])
            anns=[a for a in coco['annotations'] if a['image_id']==image['id']];assert len(anns)==len(s['annotation']['objects'])
            for ann,obj in zip(anns,s['annotation']['objects']):
                assert ann['category_id']==mapping[obj['label_id']]+1
                if obj['kind']=='polygon':assert ann['segmentation']==[sum(obj['geometry'],[])]
                assert len(ann['bbox'])==4 and ann['area']>0
    assert all(len(v)==1 for v in groups.values())
    results.append({'path':str(folder.relative_to(ROOT)),'format':index['format'],'images':len(native['samples']),'objects':objects,'splits':{sp:sum(s['split']==sp for s in native['samples']) for sp in ['train','val','test']},'status':'PASS','hashes':len(index['files']),'native_rois':len(native['rois'])})
assert len(results)>=4
media=[]
for p in sorted((out/'samples').glob('*')):
    try:
        source=FileVideoSource(p);frames=list(source.iter_frames())
        with av.open(str(p)) as container:bframes=sum(int(f.pict_type)==3 for f in container.decode(video=0))
        media.append({'file':p.name,'sha256':digest(p),'metadata':source.metadata,'decoded_frames':len(frames),'decoded_b_frames':bframes,'delta_pts_us':sorted({b.pts_us-a.pts_us for a,b in zip(frames,frames[1:])}),'status':'PASS'})
    except Exception as exc:media.append({'file':p.name,'sha256':digest(p),'status':'REJECTED','reason':str(exc)})
(out/'export-validation.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'media-validation.json').write_text(json.dumps(media,ensure_ascii=False,indent=2),encoding='utf-8')
print(len(results),'exports validated;',len(media),'actual video samples')
