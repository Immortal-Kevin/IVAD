"""Intel IDS bridge into the existing NVIDIA schema (no second business DB).

Intel's unmodified Rules/Codec/Packages remain the wire-format authority.
The source document in settings is a lossless provenance snapshot, not an
editable alternative database. Every transaction checks its projected rows.
"""
from __future__ import annotations
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
from uuid import uuid4, uuid5, NAMESPACE_URL

from sqlalchemy import select
from ivad_app.storage.database import Database
from ivad_app.storage.models import (ProjectRecord, SettingRecord, Camera,
    MediaAsset, ExtractedFrame, LabelCategory, Annotation, AnnotationRevision,
    RegionOfInterest)
from ivad_app.storage.project_store import row_dict, atomic_json, file_hash
from ivad_app.core.contracts import utc_now

KEY = 'intel_ids_source_v1'
MODELS = {m.__tablename__: m for m in (ProjectRecord, Camera, MediaAsset,
    ExtractedFrame, LabelCategory, Annotation, RegionOfInterest)}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
        separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def controlled(root):
    root = Path(root).resolve()
    boundary = os.environ.get('IVAD_IDS_CONTROLLED_ROOT')
    if not boundary or not root.is_relative_to(Path(boundary).resolve()):
        raise ValueError('IDS_WRITE_SCOPE: target must be inside explicit controlled workspace')
    if root == Path(boundary).resolve():
        raise ValueError('IDS_WRITE_SCOPE: select a project subdirectory')
    return root


def state(root):
    root = controlled(root)
    if not (root / 'project.sqlite').exists():
        return None
    db = Database(root / 'project.sqlite')
    try:
        with db.transaction() as session:
            row = session.get(SettingRecord, KEY)
            return copy.deepcopy(row.value) if row else None
    finally:
        db.close()


def commit_document(root, canonical, expected, *, provenance=None, fail_after=None):
    """Called only after Intel validation; optimistic, all-row SQLite transaction.

    JSON cache is rebuilt from this committed snapshot on every open. Incoming
    media must already be verified by Intel Packages or Store before this call.
    A failed projection never advances the source baseline or its import history.
    """
    root = controlled(root)
    root.mkdir(parents=True, exist_ok=True)
    doc = json.loads(canonical)
    if doc['schema'] != 'ids/1.0':
        raise ValueError('IDS_SCHEMA')
    incoming_hash = hashlib.sha256(canonical.encode('utf8')).hexdigest()
    entities = {e['id']: e for e in doc['entities']}
    groups = {}
    for e in doc['entities']:
        groups.setdefault(e['kind'], []).append(e)
    assets = {a['path']: a for a in doc['assets']}
    now = utc_now()
    db = Database(root / 'project.sqlite', create=not (root / 'project.sqlite').exists())
    try:
        with db.transaction(camera_write=True) as s:
            previous = s.get(SettingRecord, KEY)
            old = copy.deepcopy(previous.value) if previous else None
            if (old['sha256'] if old else None) != (expected or None):
                raise ValueError('IDS_BASELINE_CONFLICT')
            if old and old['project_id'] != doc['project_id']:
                raise ValueError('IDS_PROJECT_CONFLICT')
            rows = {table: {r.id:r for r in s.scalars(select(model))} for table,model in MODELS.items()}
            if old is None and any(rows.values()):
                raise ValueError('IDS_REQUIRES_EMPTY_CONTROLLED_DATABASE')
            # Detect edits through other NVIDIA services, even on repeated import.
            for table, records in (old or {}).get('rows', {}).items():
                for rid, checksum in records.items():
                    row = rows[table].get(rid)
                    if not row or digest(row_dict(row)) != checksum:
                        raise ValueError('IDS_LOCAL_EDIT_CONFLICT:' + table)
            if old and incoming_hash == old['sha256']:
                return {'duplicate': True, 'entities': len(entities), 'sha256': incoming_hash}
            tracked = {}
            operations = 0
            def put(model, rid, **values):
                nonlocal operations
                row = rows[model.__tablename__].get(rid)
                was_owned = rid in (old or {}).get('rows', {}).get(model.__tablename__, {})
                if row and not was_owned:
                    raise ValueError('IDS_UUID_CONFLICT:' + model.__tablename__)
                if row is None:
                    row = model(id=rid, **values)
                    s.add(row)
                    rows[model.__tablename__][rid]=row
                else:
                    for stamp in ('created_at','imported_at'):
                        if stamp in values:values[stamp]=getattr(row,stamp)
                    if 'updated_at' in values and all(getattr(row,k)==v for k,v in values.items() if k!='updated_at'):
                        values['updated_at']=row.updated_at
                    for key, value in values.items():
                        if getattr(row,key)!=value:setattr(row, key, value)
                s.flush()
                tracked.setdefault(model.__tablename__, {})[rid] = digest(row_dict(row))
                operations += 1
                if fail_after is not None and operations >= fail_after:
                    raise RuntimeError('IDS_INJECTED_ROLLBACK')
                return row
            old_entities={e['id']:e for e in json.loads(old['canonical'])['entities']} if old else {}
            entity_origins=(old or {}).get('entity_origins',{})
            def source(e):
                if old_entities.get(e['id'])!=e or e['id'] not in entity_origins:
                    entity_origins[e['id']]=incoming_hash
                return {'entity': e, 'document_sha256': entity_origins[e['id']],
                        'project_id': doc['project_id'], 'schema': doc['schema']}
            p = entities[doc['project_id']]
            put(ProjectRecord, p['id'], name=p['data']['name'], description='',
                site=entities[p['data']['site_id']]['data']['name'], created_at=now,
                updated_at=now, revision=p['revision'])
            for e in groups.get('Fault', []):
                put(LabelCategory, e['id'], name=e['data']['name'],
                    description=json.dumps(source(e), ensure_ascii=False), device_type='',
                    parent_id=None, annotation_type='box', enabled=1, revision=e['revision'])
            for e in groups.get('Camera', []):
                put(Camera, e['id'], name=e['data']['name'], legacy_key=None,
                    revision=e['revision'], history=[], details={'ids': source(e),
                    'equipment': entities[e['data']['equipment_id']]})
            for e in groups.get('Video', []):
                d = e['data']; a = assets[d['asset_path']]; cam = entities[d['camera_id']]
                put(MediaAsset, e['id'], project_id=doc['project_id'], kind='ORIGINAL',
                    parent_id=None, clip_info={}, lifecycle={'ids': source(e)},
                    name=d['original_name'], original_path=d['asset_path'], path=d['asset_path'],
                    mode='COPY', sha256=a['sha256'], size=a['bytes'],
                    video={'ids': source(e), 'decoder': 'Windows Media Foundation'},
                    camera=cam['data']['name'], camera_id=cam['id'],
                    equipment=entities[cam['data']['equipment_id']]['data']['name'],
                    site=entities[p['data']['site_id']]['data']['name'],
                    state='READY' if (root/d['asset_path']).is_file() else 'MISSING',
                    error='', job_id='', imported_at=now)
            reviews = {}
            shapes = {}; rois = {}
            for e in groups.get('Review', []):
                reviews[e['data']['frame_id']] = e
            for kind, target in [('Annotation', shapes), ('ROI', rois)]:
                for e in groups.get(kind, []):
                    if not e['data'].get('deleted', False):
                        target.setdefault(e['data']['frame_id'], []).append(e)
            def geometry(e, roi=False):
                d=e['data']; points=d['points']
                return {'id':e['id'], 'kind':('roi_' if roi else '')+d['shape'],
                    'geometry':[points[0],points[1],points[2]-points[0],points[3]-points[1]] if d['shape']=='box' else list(map(list,zip(points[::2],points[1::2]))),
                    'label_id': d.get('fault_id'), 'source':'Human Generated', 'ids':source(e)}
            for e in groups.get('Frame', []):
                d=e['data']; a=assets[d['asset_path']]; review=reviews.get(e['id'])
                status={'confirmed':'APPROVED','rejected':'REJECTED','needs_work':'DRAFT','unknown':'DRAFT'}.get((review or {}).get('data',{}).get('status'),'DRAFT')
                confirmed=status=='APPROVED'
                put(ExtractedFrame,e['id'],media_id=d['video_id'],pts_us=int(d['pts_us']),
                    time_us=int(d.get('relative_time_us',d['pts_us'])),frame_index=None,
                    width=int(d['width']),height=int(d['height']),path=d['asset_path'],
                    sha256=a['sha256'],perceptual_hash='',method='intel_ids',
                    parameters={'ids':source(e),'source_timestamp_100ns':d['source_timestamp_100ns'],
                        'time_source':d['time_source'],'timestamp_evidence':d.get('timestamp_evidence',{})},
                    parameters_hash='intel-ids-v1',job_id='',created_at=now,
                    handling={'is_excluded':bool(d.get('queue_deleted',False)),
                        'completion_state':'LABELED' if d['state'] in ('normal','abnormal') else 'UNLABELED',
                        'review_stale':not confirmed, 'ids_review': review, 'ids':source(e)})
                annotation_id=str(uuid5(NAMESPACE_URL,'intel-ids-annotation:'+e['id']))
                payload={'objects':[geometry(x) for x in shapes.get(e['id'],[])],
                    'image_tag':{'normal':'NORMAL','abnormal':'ABNORMAL'}.get(d['state'],'UNKNOWN'),
                    'image_label_id':None,'coordinate_system':'image_pixels','width':d['width'],
                    'height':d['height'],'ids_state':d['state'],'ids_review':review,'ids':source(e)}
                old_ann=rows['annotations'].get(annotation_id)
                changed=not old_ann or old_ann.payload!=payload or old_ann.status!=status
                revision=(old_ann.revision+int(changed)) if old_ann else 1
                put(Annotation,annotation_id,frame_id=e['id'],payload=payload,status=status,
                    revision=revision,source='Human Generated',updated_at=now)
                if changed:
                    s.add(AnnotationRevision(id=str(uuid4()),annotation_id=annotation_id,
                        revision=revision,payload=payload,status=status,source='Intel IDS',created_at=now))
                for roi in rois.get(e['id'],[]):
                    put(RegionOfInterest,roi['id'],scope='ids-frame:'+e['id']+':'+roi['id'],
                        media_id=d['video_id'],camera=entities[roi['data']['camera_id']]['data']['name'],
                        camera_id=roi['data']['camera_id'],payload={'objects':[geometry(roi,True)],
                        'coordinate_system':'image_pixels','frame_id':e['id'],'ids':source(roi)},
                        revision=roi['revision'],updated_at=now)
            # Active IDS projection removes queue-deleted frames. Preserve their
            # business rows, annotations and revision history as soft deletions.
            for table, records in (old or {}).get('rows', {}).items():
                for rid in records.keys()-tracked.get(table,{}).keys():
                    row=s.get(MODELS[table],rid)
                    if table=='frames':
                        row.handling=dict(row.handling,is_excluded=True,ids_removed_in=incoming_hash)
                    elif table=='rois':
                        row.payload=dict(row.payload,ids_deleted=True)
                    elif table=='media_assets':
                        row.lifecycle=dict(row.lifecycle,hidden=True,ids_removed_in=incoming_hash)
                    s.flush()
                    tracked.setdefault(table,{})[rid]=digest(row_dict(row))
            history=(old or {}).get('imports',[])
            if provenance:history=history+[provenance]
            value={'project_id':doc['project_id'],'schema':doc['schema'],'sequence':doc['sequence'],
                'sha256':incoming_hash,'canonical':canonical,'rows':tracked,'imports':history,
                'entity_origins':entity_origins}
            if previous:previous.value=value
            else:s.add(SettingRecord(key=KEY,value=value))
        result={'duplicate':False,'entities':len(entities),'sha256':incoming_hash,
            'counts':{k:len(v) for k,v in groups.items()}}
        try:
            atomic_json(root/'project.json',{'format':'ivad-project','format_version':1,
                'database':'project.sqlite','id':doc['project_id'],'name':p['data']['name']})
        except OSError:
            result['warning']='COMMITTED_PROJECT_MANIFEST_REBUILD_REQUIRED'
        return result
    finally:
        db.close()


class IdsImportService:
    def __init__(self, codec_executable):
        self.codec=Path(codec_executable).resolve()

    def import_package(self, package, root, *, fail_after=None):
        from .local_security import authorize
        root=controlled(root); authorize(root,'import');root.mkdir(parents=True,exist_ok=True)
        before=state(root)
        package=Path(package).resolve()
        # Intel importer validates bytes/paths/assets and produces its own stable
        # serialization. Stage only in the caller's controlled local workspace.
        with tempfile.TemporaryDirectory(prefix='.ids-stage-',dir=root) as temp:
            stage=Path(temp)
            if before:
                (stage/'project.ids.json').write_text(before['canonical'],encoding='utf8')
                doc=json.loads(before['canonical'])
                for a in doc['assets']:
                    src=root/a['path']; dst=stage/a['path'];dst.parent.mkdir(parents=True,exist_ok=True)
                    if src.is_file():os.link(src,dst)
            env=dict(os.environ);env.pop('IVAD_NVIDIA_BRIDGE',None)
            result=subprocess.run([str(self.codec),'--ids-import',str(package),str(stage)],
                env=env,capture_output=True,timeout=600)
            if result.returncode:
                raise ValueError('IDS_PACKAGE_REJECTED: '+(stage/'ids-error.txt').read_text(encoding='utf-8-sig') if (stage/'ids-error.txt').exists() else 'IDS_PACKAGE_REJECTED')
            canonical=(stage/'project.ids.json').read_text(encoding='utf-8-sig')
            incoming=json.loads(canonical)
            if before and hashlib.sha256(canonical.encode()).hexdigest()!=before['sha256']:
                if incoming['sequence']<=before['sequence']:
                    raise ValueError('IDS_SEQUENCE_CONFLICT')
                old_entities={e['id']:e for e in json.loads(before['canonical'])['entities']}
                for e in incoming['entities']:
                    prior=old_entities.get(e['id'])
                    if prior and (prior['kind']!=e['kind'] or (prior!=e and e['revision']<=prior['revision'])):
                        raise ValueError('IDS_ENTITY_REVISION_CONFLICT')
            newfiles=[]
            try:
                for a in json.loads(canonical)['assets']:
                    src=stage/a['path'];dst=root/a['path']
                    if dst.exists():
                        if file_hash(dst)!=a['sha256']:raise ValueError('IDS_ASSET_CONFLICT')
                    else:
                        dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,dst);newfiles.append(dst)
                summary=commit_document(root,canonical,before['sha256'] if before else None,
                    provenance={'package_sha256':file_hash(package),'target_sha256':hashlib.sha256(canonical.encode()).hexdigest()},fail_after=fail_after)
            except Exception:
                committed=state(root)
                retained={a['path'] for a in json.loads(committed['canonical'])['assets']} if committed else set()
                for p in newfiles:
                    if p.relative_to(root).as_posix() not in retained:p.unlink(missing_ok=True)
                raise
        (root/'project.ids.json').write_text(canonical,encoding='utf8')
        return summary
