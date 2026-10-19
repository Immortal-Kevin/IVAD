from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
root = Path(SPECPATH).parents[1]
datas = collect_data_files('ivad_app', include_py_files=False)
datas += [(str(root/'ivad_app/storage/migrations'),'ivad_app/storage/migrations'),
          (str(root/'packaging/p37d-lite/p37d-lite-profile.json'),'.')]
for name in ['PySide6','shiboken6','av','SQLAlchemy','alembic','Pillow','numpy','PyYAML']:
    datas += copy_metadata(name)
excludes = ['setuptools','pkg_resources','wheel','pip','pefile','PyInstaller',
            'numpy.f2py','numpy.distutils',
            'torch','torchvision','onnxruntime','ultralytics','ultralytics_platform',
            'ultralytics_thop','thop','rfdetr','cv2','pytest','tkinter',
            'ivad_app.distribution_check','ivad_app.services.training_service',
            'ivad_app.services.training_router','ivad_app.services.rfdetr_training_service',
            'ivad_app.services.model_service','ivad_app.services.offline_demo_service',
            'ivad_app.services.offline_cache','ivad_app.gui.training_page',
            'ivad_app.gui.offline_demo_page','ivad_app.compute.train_worker',
            'ivad_app.compute.offline_worker','ivad_app.compute.rfdetr_train_worker',
            'PySide6.QtTest','PySide6.QtNetwork','PySide6.QtMultimedia','PySide6.QtPdf',
            'PySide6.QtQml','PySide6.QtQuick','PySide6.QtCharts','PySide6.QtDataVisualization',
            'PySide6.QtQuick3D','PySide6.QtVirtualKeyboard']
a = Analysis([str(root/'packaging/p37d-lite/entry.py')], pathex=[str(root)], binaries=[],
             datas=datas, hiddenimports=['sqlalchemy.dialects.sqlite','sqlalchemy.ext.baked','alembic.script'],
             excludes=excludes, noarchive=False)
# Qt hooks also collect optional native plugins even when Python modules are
# excluded. Apply an explicit DLL/plugin allowlist to the actual collected TOC.
qt_dlls = {'Qt6Core.dll','Qt6Gui.dll','Qt6Widgets.dll','Qt6Svg.dll'}
plugins = {'qwindows.dll','qmodernwindowsstyle.dll','qgif.dll','qico.dll',
           'qjpeg.dll','qsvg.dll','qsvgicon.dll'}
def needed(row):
    dest = row[0].replace('\\','/')
    name = dest.rsplit('/',1)[-1]
    if '__pycache__' in dest.split('/') or name.endswith('.pyc'):return False
    if name.lower().startswith(('api-ms-win-','ext-ms-win-')):return False
    if name.startswith('Qt6') and name.endswith('.dll'):return name in qt_dlls
    if '/plugins/' in dest:return name in plugins
    # Modern supported Windows supplies its own UCRT. Do not collect an
    # unrelated UCRT from the host toolchain's libheif search path.
    if name.lower() in {'opengl32sw.dll','d3dcompiler_47.dll','ucrtbase.dll'}:return False
    if dest.startswith('PySide6/') and any(p in dest.split('/') for p in ['qml','translations']):return False
    return True
a.binaries = [row for row in a.binaries if needed(row)]
a.datas = [row for row in a.datas if needed(row)]
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='IVAD_Internal_Demo',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False,
          console=False, icon=str(root/'packaging/ivad.ico'))
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='IVAD_P37D_Lite_Candidate')
