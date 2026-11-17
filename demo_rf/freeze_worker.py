"""Reuse only build tooling from the Lite builder; RF environment stays read-only."""
import os,sys
from pathlib import Path
root=Path(__file__).resolve().parents[1]
sys.dont_write_bytecode=True
sys.path.append(str(root/'.venv-p37d-build/Lib/site-packages'))
os.environ['PYTHONDONTWRITEBYTECODE']='1'
out=Path(os.environ.get('IVAD_RF_BUILD_ROOT',str(root/'artifacts/rf-demo-20261019')))
os.environ['PYINSTALLER_CONFIG_DIR']=str(out/'pyinstaller-cache')
import PyInstaller.__main__
PyInstaller.__main__.run(['--noconfirm','--workpath',str(out/'build-worker'),
                        '--distpath',str(out/'dist-worker'),str(root/'demo_rf/worker.spec')])
