"""P37D Lite capability boundary, enforced below the UI."""
import os
import sys
from pathlib import Path
from ivad_app.core.contracts import AppError

NOTICE = '内部Lite演示版未提供AI训练、推理、旧缓存播放及视频重编码；视频读取、抽帧和人工标注可用。'
RUNTIME_AUDIT = {'denied_imports': [], 'denied_network': []}

def enabled():
    if getattr(sys, 'frozen', False):
        return (Path(sys._MEIPASS) / 'p37d-lite-profile.json').is_file()
    return os.environ.get('IVAD_P37D_LITE') == '1'

def require(feature):
    if enabled() and feature in {'ai', 'reencode', 'legacy_cache'}:
        raise AppError('DEMO_FEATURE_DISABLED', NOTICE)

class DisabledAI:
    """No worker or cache implementation is imported in the Lite composition."""
    def __getattr__(self, name):
        def denied(*args, **kwargs):
            raise AppError('DEMO_FEATURE_DISABLED', NOTICE)
        return denied

def install_runtime_guard():
    """Defense in depth for the Lite executable, including failure paths."""
    if not enabled():return
    class NoAIImports:
        def find_spec(self, fullname, path=None, target=None):
            if fullname.split('.')[0] in {'torch','torchvision','ultralytics','ultralytics_platform','ultralytics_thop','thop','rfdetr','onnxruntime','cv2'}:
                RUNTIME_AUDIT['denied_imports'].append(fullname)
                raise ImportError('Lite演示版不加载AI模块：'+fullname)
    sys.meta_path.insert(0,NoAIImports())
    def audit(event,args):
        if event in {'socket.connect','socket.getaddrinfo','socket.bind'}:
            RUNTIME_AUDIT['denied_network'].append(event)
            raise PermissionError('Lite演示版不自动联网；本地视频/标注无需网络。')
    sys.addaudithook(audit)
