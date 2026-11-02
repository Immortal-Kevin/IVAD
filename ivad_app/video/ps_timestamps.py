"""Read MPEG-2 PES video PTS, without decoding or modifying media.

This deliberately does not pretend to be a general MPEG-PS demuxer. Only
timestamp-bearing video PES packets are returned. Frame association requires
an independently verified one-to-one decoder result with matching intervals.
"""
import mmap
from pathlib import Path


def video_pes_pts(path):
    result = []
    with Path(path).open('rb') as file:
        if not file.seek(0, 2):
            return result
        file.seek(0)
        with mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ) as data:
            offset = 0
            while True:
                offset = data.find(b'\x00\x00\x01', offset)
                if offset < 0 or offset + 9 > len(data):
                    break
                stream = data[offset + 3]
                if 0xE0 <= stream <= 0xEF and data[offset + 6] & 0xC0 == 0x80:
                    length = int.from_bytes(data[offset + 4:offset + 6], 'big')
                    flags = data[offset + 7]
                    header = data[offset + 8]
                    if flags & 0x80 and header >= 5 and offset + 14 <= len(data):
                        p = data[offset + 9:offset + 14]
                        if p[0] & 1 and p[2] & 1 and p[4] & 1 and p[0] >> 4 in (2, 3):
                            pts = ((p[0] >> 1 & 7) << 30) | (p[1] << 22) | ((p[2] >> 1) << 15) | (p[3] << 7) | (p[4] >> 1)
                            result.append({'offset': offset, 'stream': stream, 'raw_pts': pts, 'time_base': '1/90000'})
                    offset += max(4, length + 6) if length else 4
                else:
                    offset += 4
    return result


def verify_frame_association(packets, presentation_ticks):
    """Reject ambiguous layouts, discontinuities and clock interpolation."""
    if not packets or len(packets) != len(presentation_ticks):
        raise ValueError('PES/frame correspondence not one-to-one')
    if len({p['stream'] for p in packets}) != 1:
        raise ValueError('Multiple video PES streams need explicit selection')
    first, origin = packets[0]['raw_pts'], presentation_ticks[0]
    previous = None
    for packet, ticks in zip(packets, presentation_ticks):
        pts = packet['raw_pts']
        if previous is not None and pts <= previous:
            raise ValueError('PES PTS discontinuity or wrap requires explicit handling')
        # Integer rational comparison; at most one 100ns output-clock tick.
        if abs((pts - first) * 10_000_000 - (ticks - origin) * 90_000) > 90_000:
            raise ValueError('PES/MF timestamp sequences differ')
        previous = pts
    return {'frames': len(packets), 'raw_origin_pts': first, 'raw_time_base': '1/90000', 'presentation_origin_ticks': origin, 'mapping': 'verified-all-frame-relative-intervals'}
