"""Relink only the new build environment's PyAV to verified LGPL FFmpeg DLLs.

This is an actual dependency replacement, not a filename-based license workaround.
Original build-env DLLs are retained outside the payload. No old venv is touched.
"""
import hashlib
import base64
import csv
import json
from pathlib import Path
import shutil
import sys
import pefile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'artifacts/p37d-lite-20261019'
ENV = ROOT / '.venv-p37d-build'
SITE = ENV / 'Lib/site-packages'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def refresh_record(site):
    """Describe the actual relinked files, not the removed wheel DLL closure."""
    record=site/'av-15.1.0.dist-info/RECORD'
    before=sha(record)
    with record.open(newline='',encoding='utf8') as f:rows=list(csv.reader(f))
    rows=[r for r in rows if not r[0].startswith('av.libs/')]
    rows.extend([[p.relative_to(site).as_posix(),'',''] for p in sorted((site/'av.libs').glob('*.dll'))])
    for row in rows:
        path=site/row[0]
        if path==record:row[1:]=['',''];continue
        if path.is_file():
            digest=base64.urlsafe_b64encode(hashlib.sha256(path.read_bytes()).digest()).rstrip(b'=').decode()
            row[1:]=['sha256='+digest,str(path.stat().st_size)]
    with record.open('w',encoding='utf8',newline='') as f:csv.writer(f).writerows(rows)
    return dict(before_sha256=before,after_sha256=sha(record),reason='Actual locally relinked extension and replacement DLL hashes')

def main():
    assert Path(sys.prefix).resolve() == ENV.resolve(), 'Only the isolated Lite build environment is writable'
    old = SITE / 'av.libs'
    backup = OUT / 'original-build-env-av.libs'
    assert old.resolve().is_relative_to(ENV.resolve())
    assert backup.resolve().is_relative_to(OUT.resolve()) and not backup.exists()
    index = json.loads((ROOT / 'packaging/p37d/source-materials.json').read_text(encoding='utf8'))
    binaries = next((ROOT / 'artifacts/p37d-20261019/lgpl-prototype').glob('*/bin'))
    for row in index['ffmpeg_research_dlls']:
        assert sha(binaries / row['file']) == row['sha256']
    mapping = {}
    for path in old.glob('*.dll'):
        base = path.name.split('-')[0]
        target = next((r['file'] for r in index['ffmpeg_research_dlls'] if r['file'].startswith(base + '-')), None)
        if target:mapping[path.name.lower()] = target
    assert len(mapping) == 7
    edits = []
    for path in (SITE / 'av').rglob('*.pyd'):
        pe = pefile.PE(str(path))
        before = sha(path)
        imports = []
        for desc in getattr(pe, 'DIRECTORY_ENTRY_IMPORT', []):
            name = desc.dll.decode('ascii')
            if name.lower() in mapping:
                replacement = mapping[name.lower()].encode('ascii')
                assert len(replacement) <= len(desc.dll)
                offset = pe.get_offset_from_rva(desc.struct.Name)
                pe.set_bytes_at_offset(offset, replacement + b'\0' * (len(desc.dll) + 1 - len(replacement)))
                imports.append(dict(before=name, after=replacement.decode('ascii')))
        if imports:
            pe.OPTIONAL_HEADER.CheckSum = pe.generate_checksum()
            pe.write(str(path))
            edits.append(dict(path=str(path.relative_to(SITE)), before_sha256=before,
                              after_sha256=sha(path), imports=imports))
        pe.close()
    # All removed libraries, including x264/x265, remain available as research
    # evidence in the new round directory, never in a collected payload path.
    shutil.move(str(old), str(backup))
    old.mkdir()
    for row in index['ffmpeg_research_dlls']:
        shutil.copy2(binaries / row['file'], old / row['file'])
    record = dict(scope='Local candidate only; source/notice obligations still require closure',
                  method='PE import-table relinking to replacement FFmpeg implementation',
                  mapping=mapping, pyd_edits=edits, dlls=index['ffmpeg_research_dlls'])
    record['distribution_record_update']=refresh_record(SITE)
    (OUT / 'pyav-relink.json').write_text(json.dumps(record, indent=2), encoding='utf8')
    print('Relinked', len(edits), 'PyAV extensions to seven verified replacement DLLs')

if __name__ == '__main__':main()
