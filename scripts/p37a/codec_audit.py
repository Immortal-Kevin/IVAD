"""Read actual loaded FFmpeg library metadata; never decode or replace video files."""
import sys,json,ctypes,hashlib,shutil
from pathlib import Path
import av
ROOT=Path(__file__).resolve().parents[2];label=sys.argv[1];libraries=[]
for key,version in av.library_versions.items():
    prefix=key.removeprefix('lib')
    for path in (Path(av.__file__).resolve().parent.parent/'av.libs').glob(prefix+'-*.dll'):
        library=ctypes.CDLL(str(path));config=getattr(library,prefix+'_configuration');config.restype=ctypes.c_char_p;lic=getattr(library,prefix+'_license');lic.restype=ctypes.c_char_p
        flags=config().decode();libraries.append(dict(name=key,version=version,path=str(path),sha256=hashlib.file_digest(path.open('rb'),'sha256').hexdigest(),configuration=flags,license=lic().decode(),enable_gpl='--enable-gpl' in flags,enable_nonfree='--enable-nonfree' in flags,enable_x264='--enable-libx264' in flags,enable_x265='--enable-libx265' in flags))
try:
    import cv2
    opencv=dict(version=cv2.__version__,build=cv2.getBuildInformation())
except ImportError:opencv=None
result=dict(environment=label,av=av.__version__,libraries=libraries,opencv=opencv,external_tools_on_path_not_proof_used={n:shutil.which(n) for n in ['ffmpeg','ffprobe','nvidia-smi','taskkill']})
(ROOT/f'artifacts/p37a-20261016/{label}-native-codec.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(dict(environment=label,av=av.__version__,versions=av.library_versions,ffmpeg_libraries=len(libraries))))
