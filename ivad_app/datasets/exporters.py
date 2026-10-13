"""独立格式适配：内部真值不改写；无法完整表达的信息保留原生旁车。"""
import json, shutil, copy
from pathlib import Path
import yaml
from ivad_app.core.contracts import AppError
from ivad_app.annotations.geometry import bounding_box, polygon_area, validate_geometry
from ivad_app.storage.project_store import atomic_json, file_hash, safe_path

FORMATS={'yolo_detect','yolo_segment','coco','ivad_native'}

def export_snapshot(snapshot, source_folder, destination, format_name, check=lambda:None):
    if format_name not in FORMATS:raise AppError('EXPORT_FORMAT','不支持的导出格式。')
    labels={row['uuid']:row['class_id'] for row in snapshot['classes']}
    warnings=[]
    if format_name.startswith('yolo'):
        if not labels:raise AppError('CLASS_MAP_EMPTY','YOLO版本没有目标类别，请加入已审核目标标注；正常图片仍可独立保存或原生导出。')
        for sample in snapshot['samples']:
            if sample['annotation']['image_tag']!='NORMAL' and not sample['annotation']['objects']:
                raise AppError('UNKNOWN_NOT_NEGATIVE','未知、异常整帧标签或未标注图片不能作为正常检测负样本导出YOLO。')
            if format_name=='yolo_segment' and any(obj['kind']=='box' for obj in sample['annotation']['objects']):
                raise AppError('SEGMENT_BOX_UNSUPPORTED','版本包含检测框，不能伪装为Mask或静默丢弃。请冻结仅多边形/正常负样本的分割版本，或导出COCO/原生格式。')
            if format_name=='yolo_detect' and any(obj['kind']=='polygon' for obj in sample['annotation']['objects']):
                warnings.append('Detection使用多边形外接框；原始多边形完整保留在ivad_native.json。')
    for split in ['train','val','test']:
        (destination/'images'/split).mkdir(parents=True,exist_ok=True)
        if format_name.startswith('yolo'):(destination/'labels'/split).mkdir(parents=True,exist_ok=True)
    coco={split:{'images':[],'annotations':[],'categories':[{'id':c['class_id']+1,'name':c['name'],'label_uuid':c['uuid']} for c in snapshot['classes']]} for split in ['train','val','test']}
    for image_id,sample in enumerate(snapshot['samples'],1):
        check();relative=Path(sample['image']);src=safe_path(source_folder,sample['image'])
        if not src.is_file() or file_hash(src,check)!=sample['sha256']:raise AppError('SNAPSHOT_IMAGE_INVALID','冻结图片缺失或SHA256不符，已停止导出。')
        image_name=sample['frame_id']+relative.suffix;split=sample['split'];target=destination/'images'/split/image_name
        shutil.copyfile(src,target)
        if file_hash(target,check)!=sample['sha256']:raise AppError('EXPORT_HASH','导出图片校验失败。')
        width,height=sample['width'],sample['height'];lines=[]
        coco[split]['images'].append({'id':image_id,'file_name':f'images/{split}/{image_name}','width':width,'height':height,'frame_uuid':sample['frame_id']})
        for obj in sample['annotation']['objects']:
            validate_geometry(obj['kind'],obj['geometry'],width,height)
            if obj['label_id'] not in labels:raise AppError('CLASS_MAP_INVALID','标注类别映射无效。')
            class_id=labels[obj['label_id']];x,y,w,h=bounding_box(obj['kind'],obj['geometry'])
            if format_name=='yolo_detect':values=[(x+w/2)/width,(y+h/2)/height,w/width,h/height]
            elif format_name=='yolo_segment':values=[v/(width if i%2==0 else height) for i,v in enumerate(sum(obj['geometry'],[]))]
            else:values=[]
            if values:lines.append(str(class_id)+' '+' '.join(f'{v:.9f}' for v in values))
            coco[split]['annotations'].append({'id':len(coco[split]['annotations'])+1,'image_id':image_id,'category_id':class_id+1,'bbox':[x,y,w,h],'area':polygon_area(obj['geometry']) if obj['kind']=='polygon' else w*h,'segmentation':[sum(obj['geometry'],[])] if obj['kind']=='polygon' else [],'iscrowd':0,'annotation_uuid':obj['id']})
        if format_name.startswith('yolo'):(destination/'labels'/split/(sample['frame_id']+'.txt')).write_text('\n'.join(lines)+'\n' if lines else '',encoding='utf-8')
    if format_name.startswith('yolo'):
        # 不写硬编码path：Ultralytics以data.yaml所在目录为数据根，便于完整迁移。
        config={'train':'images/train','val':'images/val','test':'images/test','names':{c['class_id']:c['name'] for c in snapshot['classes']}}
        (destination/'data.yaml').write_text(yaml.safe_dump(config,allow_unicode=True,sort_keys=False),encoding='utf-8')
        parsed=yaml.safe_load((destination/'data.yaml').read_text(encoding='utf-8'))
        if parsed!=config:raise AppError('YAML_INVALID','导出YAML校验失败。')
    if format_name=='coco':
        for split,value in coco.items():atomic_json(destination/f'instances_{split}.json',value)
    native=copy.deepcopy(snapshot)
    for s in native['samples']:
        s['source_snapshot_image']=s['image'];s['image']=f"images/{s['split']}/{s['frame_id']}{Path(s['image']).suffix}"
    atomic_json(destination/'ivad_native.json',dict(native,export_format=format_name,export_warnings=sorted(set(warnings))))
    json.loads((destination/'ivad_native.json').read_text(encoding='utf-8'))
    manifest={p.relative_to(destination).as_posix():file_hash(p,check) for p in destination.rglob('*') if p.is_file()}
    atomic_json(destination/'export_manifest.json',{'format':format_name,'files':manifest,'state':'COMPLETE','warnings':sorted(set(warnings))})
    return sorted(set(warnings))
