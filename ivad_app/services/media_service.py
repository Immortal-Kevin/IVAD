"""视频导入、引用、PTS抽帧与完整性检查；源文件只读。"""
from __future__ import annotations
import hashlib, json, shutil, os
from pathlib import Path
from uuid import uuid4
import numpy as np
from PIL import Image
from sqlalchemy import select
from ivad_app.core.contracts import AppError, utc_now
from ivad_app.storage.models import MediaAsset, ExtractedFrame, DatasetVersion, ExportRecord
from ivad_app.storage.project_store import file_hash, safe_path, row_dict
from ivad_app.video.reader import FileVideoSource

def dhash(image):
    array = np.asarray(image.convert('L').resize((9, 8)))
    bits = array[:, 1:] > array[:, :-1]
    return f'{int("".join("1" if bit else "0" for bit in bits.ravel()), 2):016x}'

class MediaService:
    def __init__(self, store, logs): self.store, self.logs = store, logs

    @staticmethod
    def resolve(root, media):
        path = Path(media['path']) if media['mode'] == 'REFERENCE' else safe_path(root, media['path'])
        if not path.is_file(): raise AppError('MEDIA_MISSING', '视频Missing；请重新定位引用或恢复项目副本。')
        return path

    def list(self, root=None) -> list[dict]:
        with self.store.open(root) as (folder, db, _), db.transaction() as session:
            rows = [row_dict(row) for row in session.scalars(select(MediaAsset).order_by(MediaAsset.imported_at))]
        for row in rows:
            if row['state'] == 'READY':
                try: row['accessible_path'] = str(self.resolve(folder, row))
                except AppError: row['state'] = 'MISSING'
        return rows

    def get(self, media_id: str, root=None) -> dict:
        with self.store.open(root) as (folder, db, _), db.transaction() as session:
            row = session.get(MediaAsset, media_id)
            if not row or row.state != 'READY': raise AppError('MEDIA_NOT_READY', '视频尚未完整导入或已失败。')
            data = row_dict(row)
        data['accessible_path'] = str(self.resolve(folder, data))
        return data

    def import_batch(self, context, payload):
        root = payload['root']; mode = payload.get('mode', 'COPY')
        if mode not in {'COPY', 'REFERENCE'}: raise AppError('IMPORT_MODE', '导入模式无效。')
        paths = payload['paths']
        if not paths or len(paths) > 1000: raise AppError('IMPORT_LIMIT', '请选择1至1000个文件。')
        report = {'imported': [], 'duplicates': [], 'failed': []}
        with self.store.open(root) as (folder, db, project_id):
            (folder / 'media').mkdir(exist_ok=True)
            for index, raw in enumerate(paths):
                context.check()
                source = Path(raw).resolve(); media_id = str(uuid4()); owned_temp = owned_final = None
                try:
                    if not source.is_file(): raise AppError('MEDIA_MISSING', '源文件不存在或不可读取。')
                    size = source.stat().st_size
                    checksum = file_hash(source, context.check)
                    with db.transaction() as session:
                        duplicate = session.scalar(select(MediaAsset).where(MediaAsset.sha256 == checksum, MediaAsset.state == 'READY'))
                        if duplicate:
                            report['duplicates'].append({'name': source.name, 'id': duplicate.id}); context.log('检测到相同SHA256录像，复用已有资源。'); continue
                    with db.transaction() as session:
                        session.add(MediaAsset(id=media_id, project_id=project_id, name=source.name, original_path=str(source), path='', mode=mode, sha256=checksum, size=size, video={}, camera=payload.get('camera',''), equipment=payload.get('equipment',''), site=payload.get('site',''), state='IMPORTING', error='', job_id=context.job_id, imported_at=utc_now()))
                    metadata = FileVideoSource.probe(source)
                    if mode == 'COPY':
                        if shutil.disk_usage(folder).free < size + 16 * 1024 * 1024: raise AppError('DISK_SPACE', '项目磁盘空间不足，尚未复制原始录像。')
                        suffix = source.suffix.lower()[:10] or '.video'
                        owned_final = folder / 'media' / f'{media_id}{suffix}'
                        owned_temp = owned_final.with_suffix(owned_final.suffix + '.partial')
                        with source.open('rb') as src, owned_temp.open('xb') as dst:
                            while chunk := src.read(1024 * 1024): context.check(); dst.write(chunk)
                            dst.flush(); os.fsync(dst.fileno())
                        if file_hash(owned_temp, context.check) != checksum: raise AppError('SOURCE_CHANGED', '录像在复制期间发生变化，已拒绝导入。')
                        owned_temp.rename(owned_final)
                        location = owned_final.relative_to(folder).as_posix()
                    else:
                        if file_hash(source, context.check) != checksum: raise AppError('SOURCE_CHANGED', '录像在导入期间发生变化。')
                        location = str(source)
                    context.check()
                    with db.transaction() as session:
                        row = session.get(MediaAsset, media_id); row.path = location; row.video = metadata; row.state = 'READY'
                    report['imported'].append(media_id)
                    context.log('录像导入完成：' + source.name)
                except Exception as exc:
                    if owned_temp and owned_temp.exists(): owned_temp.unlink()
                    if owned_final and owned_final.exists(): owned_final.unlink()  # 仅本次未commit的UUID复制文件。
                    error = exc.message if isinstance(exc, AppError) else '视频读取或导入失败。'
                    with db.transaction() as session:
                        row = session.get(MediaAsset, media_id)
                        if row: row.state = 'CANCELLED' if isinstance(exc, AppError) and exc.code == 'JOB_CANCELLED' else 'ERROR'; row.error = error
                    if isinstance(exc, AppError) and exc.code == 'JOB_CANCELLED': raise
                    report['failed'].append({'name': source.name, 'error': error})
                    context.log('导入失败：'+source.name+'：'+error)
                    self.logs.exception('media', '录像导入失败：' + error, context.job_id)
                finally:
                    if not context.cancel.is_set(): context.progress((index + 1) * 100 / len(paths))
        if report['failed'] and not report['imported'] and not report['duplicates']:
            raise AppError('IMPORT_ALL_FAILED', '全部录像导入失败，请查看任务日志。')
        if report['failed']: context.log(f"批量导入完成，部分失败：{len(report['failed'])}项。")
        return report

    def relocate(self, media_id, new_path, root=None):
        with self.store.open(root) as (folder, db, _):
            with db.transaction() as session:
                row = session.get(MediaAsset, media_id)
                if not row or row.mode != 'REFERENCE': raise AppError('RELOCATE_MODE', '仅外部引用可重新定位。')
                checksum = row.sha256
            path = Path(new_path).resolve()
            if not path.is_file() or file_hash(path) != checksum: raise AppError('RELOCATE_HASH', '新文件SHA256不匹配，引用未改变。')
            with db.transaction() as session: session.get(MediaAsset, media_id).path = str(path)
        return {'status': 'READY'}

    def frames(self, root=None) -> list[dict]:
        with self.store.open(root) as (folder, db, _), db.transaction() as session:
            rows = [row_dict(row) for row in session.scalars(select(ExtractedFrame).order_by(ExtractedFrame.created_at))]
        for row in rows: row['state'] = 'READY' if safe_path(folder, row['path']).is_file() else 'MISSING'
        return rows

    def frame_image(self, frame_id, root=None):
        with self.store.open(root) as (folder, db, _), db.transaction() as session:
            frame = session.get(ExtractedFrame, frame_id)
            if not frame: raise AppError('FRAME_MISSING', '候选帧记录不存在。')
            value = row_dict(frame)
        path = safe_path(folder, value['path'])
        if not path.is_file() or file_hash(path) != value['sha256']: raise AppError('FRAME_INVALID', '候选图片缺失或校验不匹配。')
        with Image.open(path) as image: return value, image.convert('RGB').copy()

    def _save_frame(self, folder, db, media_id, frame, method, parameters, job_id):
        parameters_hash = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()
        with db.transaction() as session:
            old = session.scalar(select(ExtractedFrame).where(ExtractedFrame.media_id == media_id, ExtractedFrame.pts_us == frame.pts_us, ExtractedFrame.parameters_hash == parameters_hash))
            if old: return old.id
        image = frame.image
        max_width = int(parameters.get('max_width', 0))
        if max_width and image.width > max_width:
            image = image.resize((max_width, max(1, round(image.height * max_width / image.width))))
        frame_id = str(uuid4()); extension = parameters.get('format', 'PNG').lower()
        (folder / 'frames').mkdir(exist_ok=True)
        final = folder / 'frames' / f'{frame_id}.{extension}'; temp = final.with_name(final.name + '.partial')
        try:
            image.save(temp, format=parameters.get('format','PNG'), quality=int(parameters.get('quality', 90)))
            checksum = file_hash(temp); temp.rename(final)
            with db.transaction() as session:
                session.add(ExtractedFrame(id=frame_id, media_id=media_id, pts_us=frame.pts_us, time_us=frame.time_us, frame_index=frame.index, width=image.width, height=image.height, path=final.relative_to(folder).as_posix(), sha256=checksum, perceptual_hash=dhash(image), method=method, parameters=parameters, parameters_hash=parameters_hash, job_id=job_id, created_at=utc_now()))
        except Exception:
            temp.unlink(missing_ok=True); final.unlink(missing_ok=True); raise
        return frame_id

    def extract(self, context, payload):
        root = payload['root']; media_id = payload['media_id']; opts = dict(payload['options'])
        mode = opts.get('mode','fixed'); start = int(opts.get('start_us',0)); end = int(opts.get('end_us',0))
        interval = int(opts.get('interval_us', 1000000)); maximum = int(opts.get('maximum',50))
        if mode not in {'fixed','smart'}: raise AppError('SAMPLING_UNAVAILABLE', 'AI辅助抽帧Not Available，P5实现；本阶段不执行AI。')
        if interval <= 0 or not 1 <= maximum <= 5000 or start < 0 or end <= start: raise AppError('SAMPLING_OPTIONS', '抽帧范围/间隔无效或数量超出1–5000限制。')
        if opts.get('format','PNG') not in {'PNG','JPEG'} or not 1 <= int(opts.get('quality',90)) <= 100: raise AppError('IMAGE_FORMAT', '图片格式或JPEG质量无效。')
        media = self.get(media_id, root)
        if end > media['video']['duration_us'] + 1000: raise AppError('SAMPLING_RANGE', '抽帧结束时间超出视频时长。')
        source = FileVideoSource(Path(media['accessible_path']), media['video'])
        ids = []; next_fixed = start; previous = None
        threshold = float(opts.get('sensitivity', 12)) / 100
        with self.store.open(root) as (folder, db, _):
            for frame in source.iter_frames(start, end):
                context.check()
                sample = frame.time_us >= next_fixed
                if mode == 'smart':
                    array = np.asarray(frame.image.convert('L').resize((64,64)), dtype=np.float32)
                    changed = previous is None or float(np.abs(array - previous).mean()/255) >= threshold
                    sample = changed or sample if opts.get('baseline',True) else changed
                    previous = array
                if sample:
                    opts['rotation'] = frame.rotation; opts['source_dimensions'] = [media['video']['width'], media['video']['height']]
                    ids.append(self._save_frame(folder, db, media_id, frame, mode, opts, context.job_id))
                    while next_fixed <= frame.time_us: next_fixed += interval
                    if len(ids) >= maximum: break
                context.progress(min(99, (frame.time_us-start)*100/(end-start)))
        context.progress(100)
        context.log(f'抽帧完成，{len(ids)}张候选图片；画面变化不等于工业异常。')
        return {'frames': ids, 'count': len(ids), 'maximum': maximum}

    def capture(self, media_id, time_us, root=None):
        media = self.get(media_id, root); frame = FileVideoSource(Path(media['accessible_path']), media['video']).at(time_us)
        with self.store.open(root) as (folder, db, _):
            return self._save_frame(folder, db, media_id, frame, 'manual', {'mode':'manual','format':'PNG','rotation':frame.rotation}, 'manual')

    def check(self, root=None):
        issues = []
        with self.store.open(root) as (folder, db, _):
            db.integrity_check()
            with db.transaction() as session:
                media_rows = [row_dict(r) for r in session.scalars(select(MediaAsset))]
                frames = [row_dict(r) for r in session.scalars(select(ExtractedFrame))]
                versions = [row_dict(r) for r in session.scalars(select(DatasetVersion))]
                exports = [row_dict(r) for r in session.scalars(select(ExportRecord))]
            for row in media_rows:
                if row['state'] != 'READY': issues.append({'id':row['id'],'kind':'incomplete_media','state':row['state']}); continue
                try:
                    path = self.resolve(folder,row)
                    if file_hash(path) != row['sha256']: issues.append({'id':row['id'],'kind':'media_hash_mismatch'})
                except AppError: issues.append({'id':row['id'],'kind':'media_missing'})
            for row in frames:
                path = safe_path(folder,row['path'])
                if not path.is_file() or file_hash(path) != row['sha256']: issues.append({'id':row['id'],'kind':'frame_missing_or_changed'})
            for path in folder.rglob('*.partial'): issues.append({'kind':'interrupted_staging','path':path.relative_to(folder).as_posix()})
            for row in versions:
                path=safe_path(folder,row['path'])
                if not path.is_file() or file_hash(path)!=row['sha256']:
                    issues.append({'id':row['id'],'kind':'snapshot_missing_or_changed'});continue
                snapshot=json.loads(path.read_text(encoding='utf-8'))
                for sample in snapshot['samples']:
                    image=safe_path(path.parent,sample['image'])
                    if not image.is_file() or file_hash(image)!=sample['sha256']:issues.append({'id':sample['frame_id'],'kind':'snapshot_image_missing_or_changed'})
            for row in exports:
                path=Path(row['path'])/'export_manifest.json'
                if not path.is_file() or file_hash(path)!=row['sha256']:issues.append({'id':row['id'],'kind':'export_missing_or_changed'})
        return {'status':'PASS' if not issues else 'WARNING','issues':issues,'hint':'不会自动删除资源；请重新定位引用、重试中断任务或保留项目等待恢复。'}
