"""Confirmed IDS projection to RF-DETR COCO, grouped by source camera/video."""
import json
from pathlib import Path
import shutil
from sqlalchemy import select
from ivad_app.services.ids_import_service import controlled, state, digest
from ivad_app.storage.database import Database
from ivad_app.storage.models import ExtractedFrame, Annotation, LabelCategory, MediaAsset
from ivad_app.storage.project_store import file_hash


def export_dataset(root, output, *, group_splits=None, group_by='camera', limit=None):
    root=controlled(root);output=controlled(output)
    if output.exists():raise ValueError('IDS_DATASET_OUTPUT_EXISTS')
    saved=state(root)
    if not saved:raise ValueError('IDS_SOURCE_MISSING')
    if group_by not in {'camera','video','batch'}:raise ValueError('IDS_SPLIT_GROUP')
    db=Database(root/'project.sqlite')
    try:
        with db.transaction() as s:
            frames=list(s.scalars(select(ExtractedFrame)))
            annotations={a.frame_id:a for a in s.scalars(select(Annotation))}
            media={m.id:m for m in s.scalars(select(MediaAsset))}
            labels=sorted(s.scalars(select(LabelCategory)),key=lambda x:x.id)
            # Training never ignores edits made outside the IDS bridge.
            from ivad_app.services.ids_import_service import MODELS
            from ivad_app.storage.project_store import row_dict
            for table, records in saved['rows'].items():
                current={r.id:r for r in s.scalars(select(MODELS[table]))}
                if any(rid not in current or digest(row_dict(current[rid]))!=h for rid,h in records.items()):
                    raise ValueError('IDS_LOCAL_EDIT_CONFLICT')
            class_map={row.id:i for i,row in enumerate(labels)}
            categories=[{'id':class_map[x.id],'name':x.name,'supercategory':x.name} for x in labels]
            candidates=[];excluded={}
            for f in frames:
                a=annotations.get(f.id);reason=None
                if f.handling.get('is_excluded'):reason='soft_deleted'
                elif not a or a.status!='APPROVED' or f.handling.get('review_stale'):reason='unconfirmed'
                elif a.payload['image_tag'] not in {'NORMAL','ABNORMAL'}:reason='unknown'
                elif a.payload['image_tag']=='NORMAL' and a.payload.get('objects'):raise ValueError('IDS_NORMAL_WITH_TARGETS')
                elif a.payload['image_tag']=='ABNORMAL' and not a.payload.get('objects'):reason='abnormal_without_targets'
                if reason:excluded[reason]=excluded.get(reason,0)+1;continue
                m=media[f.media_id]
                group=(m.camera_id if group_by=='camera' else m.id if group_by=='video' else m.video.get('capture_batch'))
                if not group:raise ValueError('IDS_GROUP_MISSING')
                candidates.append((f,a,group))
            groups=sorted({g for _,_,g in candidates})
            if group_splits is None:
                if len(groups)<2:raise ValueError('IDS_SPLIT_REQUIRES_INDEPENDENT_GROUPS')
                group_splits={g:('valid' if i==len(groups)-1 else 'train') for i,g in enumerate(groups)}
            if set(group_splits)!=set(groups) or not {'train','valid'}<=set(group_splits.values()) or set(group_splits.values())-{'train','valid','test'}:
                raise ValueError('IDS_SPLIT_MAP')
            outputs={split:{'info':{'description':'IDS confirmed snapshot'},'licenses':[],
                'categories':categories,'images':[],'annotations':[]} for split in set(group_splits.values())}
            # Copy only after all source hashes are checked; never modify inputs.
            chosen=candidates if limit is None else candidates[:limit]
            hashes={}
            for f,a,g in chosen:
                if file_hash(root/f.path)!=f.sha256:raise ValueError('IDS_FRAME_HASH')
                if f.sha256 in hashes and hashes[f.sha256]!=group_splits[g]:
                    raise ValueError('IDS_CROSS_SPLIT_DUPLICATE')
                hashes[f.sha256]=group_splits[g]
            output.mkdir(parents=True)
            sample_manifest=[]
            for f,a,g in chosen:
                split=group_splits[g];data=outputs[split];folder=output/split;folder.mkdir(exist_ok=True)
                name=f.id+Path(f.path).suffix;shutil.copy2(root/f.path,folder/name)
                image_id=len(data['images'])+1
                data['images'].append({'id':image_id,'file_name':name,'width':f.width,'height':f.height})
                for obj in a.payload['objects']:
                    if obj['kind']=='box':
                        x1,y1,w,h=obj['geometry'];x2,y2=x1+w,y1+h
                    elif obj['kind']=='polygon':
                        xs,ys=zip(*obj['geometry']);x1,y1,x2,y2=min(xs),min(ys),max(xs),max(ys)
                    else:raise ValueError('IDS_TARGET_SHAPE')
                    if not (0<=x1<x2<=f.width and 0<=y1<y2<=f.height):raise ValueError('IDS_TARGET_BOUNDS')
                    data['annotations'].append({'id':len(data['annotations'])+1,'image_id':image_id,
                        'category_id':class_map[obj['label_id']],'bbox':[x1,y1,x2-x1,y2-y1],
                        'area':(x2-x1)*(y2-y1),'iscrowd':0,'segmentation':[]})
                sample_manifest.append({'frame_id':f.id,'video_id':f.media_id,'camera_id':media[f.media_id].camera_id,
                    'group':g,'split':split,'sha256':f.sha256,'pts_us':f.pts_us,
                    'source_timestamp_100ns':f.parameters['source_timestamp_100ns']})
            for split,data in outputs.items():
                folder=output/split;folder.mkdir(exist_ok=True)
                (folder/'_annotations.coco.json').write_text(json.dumps(data,ensure_ascii=False),encoding='utf8')
            manifest={'source_sha256':saved['sha256'],'schema':saved['schema'],'sequence':saved['sequence'],
                'class_map':class_map,'taxonomy':{x.id:json.loads(x.description)['entity']['data']['taxonomy_version'] for x in labels},
                'group_by':group_by,'group_splits':group_splits,'excluded':excluded,'samples':sample_manifest,
                'polygon_rule':'axis-aligned min/max of source pixel vertices; bbox = x,y,width,height',
                'roi_rule':'retained separately in project rois; never a target',
                'class_names':[x.name for x in labels]}
            manifest['sha256']=digest(manifest)
            (output/'ids-dataset.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
            return manifest
    finally:db.close()
