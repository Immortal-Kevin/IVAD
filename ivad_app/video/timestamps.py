"""Derived media/source times. Never rewrite persisted PTS or infer camera wall time."""


def relative_time_us(pts_us,metadata):
    """PTS is already converted to microseconds; origin uses the same clock."""
    return int(pts_us)-int(metadata['origin_us'])


def frame_times(frame,media,media_map=None):
    metadata=media.get('video',{});issues=[];raw_us=int(frame['pts_us']);stored=frame.get('time_us')
    if metadata.get('origin_us') is not None:
        relative=relative_time_us(raw_us,metadata);basis='pts_minus_stream_origin'
        if stored is not None and abs(relative-int(stored))>1:issues.append('原PTS与历史相对时间不一致，派生显示未改写历史记录')
    elif stored is not None:relative=int(stored);basis='stored_relative_fallback';issues.append('缺少媒体起始PTS，使用历史相对时间，待核验')
    else:relative=None;basis='unknown';issues.append('缺少可信媒体时间')
    duration=metadata.get('duration_us')
    if relative is not None and (relative<0 or (duration is not None and relative>int(duration)+1)):issues.append('相对时间超出媒体时长，需只读核查')
    current=media;source_relative=relative;seen=set();media_map=media_map or {media['id']:media}
    while current.get('parent_id'):
        if current['id'] in seen or current['parent_id'] not in media_map:issues.append('原视频来源链缺失或循环');source_relative=None;break
        seen.add(current['id']);offset=current.get('clip_info',{}).get('first_source_time_us')
        if offset is None:issues.append('片段缺少实际首帧来源时间，不按申请起点猜测');source_relative=None
        elif source_relative is not None:source_relative+=int(offset)
        current=media_map[current['parent_id']]
    return {'raw_pts_us':raw_us,'raw_pts':frame.get('raw_pts'),'time_base':metadata.get('time_base'),'media_origin_us':metadata.get('origin_us'),'media_relative_us':relative,'media_relative_seconds':relative/1e6 if relative is not None else None,'source_relative_us':source_relative,'source_relative_seconds':source_relative/1e6 if source_relative is not None else None,'root_source_id':current['id'] if not current.get('parent_id') else None,'capture_datetime':None,'time_basis':basis,'timestamp_issues':issues}
