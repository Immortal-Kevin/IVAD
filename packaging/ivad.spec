from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, copy_metadata
root=Path(SPECPATH).parent
datas=collect_data_files('ivad_app',include_py_files=False)
datas += [(str(root/'ivad_app/storage/migrations'),'ivad_app/storage/migrations')]
datas += [(str(root/'packaging/build-info.json'),'ivad_app')]
for name in ['PySide6','av','SQLAlchemy','alembic','Pillow','numpy','PyYAML']:datas += copy_metadata(name)
a=Analysis([str(root/'packaging/entry.py')],pathex=[str(root)],binaries=[],datas=datas,
 hiddenimports=['sqlalchemy.dialects.sqlite','sqlalchemy.ext.baked','alembic.script','PySide6.QtTest'],
 excludes=['torch','torchvision','onnxruntime','ultralytics','pytest','tkinter','PySide6.QtNetwork','PySide6.QtMultimedia','PySide6.QtPdf','PySide6.QtQml','PySide6.QtQuick'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='IVAD',debug=False,bootloader_ignore_signals=False,strip=False,upx=False,console=False,icon=str(root/'packaging/ivad.ico'),version=str(root/'packaging/version-info.txt'))
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='IVAD_Platform_v1.0_P2_Beta_Portable')
