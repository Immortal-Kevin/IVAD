from pathlib import Path
from PyInstaller.utils.hooks import copy_metadata
root=Path(SPECPATH).parent
a=Analysis([str(root/'demo_rf/gui_entry.py')],pathex=[str(root)],binaries=[],datas=copy_metadata('av'),
           hiddenimports=['PIL.Image'],excludes=['torch','torchvision','rfdetr','cv2','pytest','tkinter','ultralytics','PyInstaller',
           'PySide6.QtNetwork','PySide6.QtMultimedia','PySide6.QtQml','PySide6.QtQuick','PySide6.QtPdf'])
qt={'Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Svg.dll'}
plugins={'qwindows.dll','qmodernwindowsstyle.dll','qgif.dll','qico.dll','qjpeg.dll','qsvg.dll','qsvgicon.dll'}
def keep(row):
    n=row[0].replace('\\','/');base=n.rsplit('/',1)[-1]
    if base.startswith('Qt6') and base.endswith('.dll'):return base in qt
    if '/plugins/' in n:return base in plugins
    if base.lower().startswith(('api-ms-win-','ext-ms-win-')):return False
    if base.lower() in {'ucrtbase.dll','opengl32sw.dll','d3dcompiler_47.dll'}:return False
    return '__pycache__' not in n
a.binaries=[x for x in a.binaries if keep(x)];a.datas=[x for x in a.datas if keep(x)]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='IVAD_RF_Demo',console=False,debug=False,upx=False,icon=str(root/'packaging/ivad.ico'))
# A console bootloader preserves redirected stdin/stdout for the decoder protocol.
decoder=EXE(pyz,a.scripts,[],exclude_binaries=True,name='IVAD_RF_Decode',console=True,debug=False,upx=False)
coll=COLLECT(exe,decoder,a.binaries,a.datas,name='IVAD_RF_Demo_Candidate',upx=False)
