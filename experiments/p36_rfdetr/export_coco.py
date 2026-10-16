"""Independent frozen IVAD -> COCO experiment copy. No application/YOLO imports."""
import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path


def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def export(manifest_path, destination):
    manifest_path, destination = Path(manifest_path), Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    m = json.loads(manifest_path.read_text(encoding='utf8'))
    classes = m['classes']
    ids = {c['uuid']: c['class_id'] for c in classes}
    categories = [dict(id=c['class_id'], name=c['name'], supercategory='fault', uuid=c['uuid']) for c in classes]
    groups = {s: dict(images=[], annotations=[], categories=categories, info=dict(status='LIMITED', source_version=m['version_id'])) for s in ('train', 'valid', 'test')}
    counts = {s: dict(images=0, objects=0, normal=0) for s in groups}
    provenance = []
    # Validate everything before creating the copy; never consult mutable labels.
    for i, sample in enumerate(m['samples'], 1):
        split = {'train': 'train', 'val': 'valid', 'test': 'test'}[sample['split']]
        annotation = sample['annotation']
        if sample.get('annotation_source') != 'Human Generated':
            raise ValueError('Non-human annotation source')
        w, h = sample['width'], sample['height']
        source = (manifest_path.parent / sample['image']).resolve()
        if not source.is_relative_to(manifest_path.parent.resolve()) or sha(source) != sample['sha256']:
            raise ValueError('Image path/hash mismatch')
        objects = annotation['objects']
        if annotation['image_tag'] == 'NORMAL' and objects:
            raise ValueError('Normal/target conflict')
        if annotation['image_tag'] not in ('NORMAL', 'ABNORMAL'):
            raise ValueError('Unconfirmed/excluded sample')
        from PIL import Image
        with Image.open(source) as image:
            if image.size != (w,h):raise ValueError('Actual image dimensions differ')
            image.verify()
        coco = groups[split]
        coco['images'].append(dict(id=i, file_name=source.name, width=w, height=h, ivad_frame_id=sample['frame_id']))
        for obj in objects:
            if obj['kind'] != 'box' or obj.get('source') != 'Human Generated':
                raise ValueError('Polygon or non-human object requires explicit review')
            x, y, bw, bh = obj['geometry']
            if not all(math.isfinite(v) for v in (x,y,bw,bh)) or min(x,y)<0 or min(bw,bh)<=0 or x+bw>w+1e-6 or y+bh>h+1e-6:
                raise ValueError('Invalid box geometry')
            coco['annotations'].append(dict(id=len(coco['annotations'])+1, image_id=i, category_id=ids[obj['label_id']], bbox=[x,y,bw,bh], area=bw*bh, iscrowd=0, ivad_object_id=obj['id']))
        counts[split]['images'] += 1
        counts[split]['objects'] += len(objects)
        counts[split]['normal'] += annotation['image_tag'] == 'NORMAL'
        provenance.append(dict(sample=sample, source=str(source), split=split))
    for split, coco in groups.items():
        folder=destination/split
        folder.mkdir(parents=True)
        (folder/'_annotations.coco.json').write_text(json.dumps(coco,ensure_ascii=False,indent=2),encoding='utf8')
    for p in provenance:
        target=destination/p['split']/Path(p['source']).name
        shutil.copyfile(p['source'],target)
        assert sha(target)==p['sample']['sha256']
    train=[p['sample'] for p in provenance if p['split']=='train']
    val=[p['sample'] for p in provenance if p['split']=='valid']
    nearest=min(abs(t['time_us']-v['time_us'])/1e6 for t in train for v in val if t['source_group_id']==v['source_group_id'])
    result=dict(status='LIMITED', manifest_sha256=sha(manifest_path), version_id=m['version_id'], counts=counts, categories=categories, minimum_cross_split_same_source_seconds=nearest, source_groups=sorted({p['sample']['source_group_id'] for p in provenance}), samples=provenance)
    (destination/'provenance.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
    return {k:v for k,v in result.items() if k!='samples'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('manifest');parser.add_argument('destination')
    args=parser.parse_args()
    print(json.dumps(export(args.manifest,args.destination),ensure_ascii=False,indent=2))
