from pathlib import Path
import json
from PyInstaller.utils.hooks import copy_metadata, collect_submodules, collect_data_files
root = Path(SPECPATH).parent
data = []
for name in ['rfdetr','supervision','torch','torchvision','transformers','numpy','Pillow','pydantic','timm','opencv-python']:
    try:data += copy_metadata(name)
    except Exception:pass
for name in json.loads((root/'demo_rf/runtime_metadata.json').read_text()):
    try:data += copy_metadata(name)
    except Exception:pass
data += collect_data_files('rfdetr', include_py_files=False)
data += collect_data_files('timm', include_py_files=False)
hidden = collect_submodules('rfdetr', filter=lambda n: not any(s in n for s in ['training','export','cli','benchmark','visualization']))
hidden += ['torchvision._C','torchvision.image','scipy.special._special_ufuncs']
hidden += json.loads((root/'demo_rf/inference_imports.json').read_text())
a = Analysis([str(root/'demo_rf/worker_entry.py')], pathex=[str(root)], hookspath=[str(root/'demo_rf/hooks')],
    module_collection_mode={'rfdetr':'pyz+py'},
    datas=data, binaries=[], hiddenimports=hidden,
    excludes=['PySide6','tkinter','ultralytics','ultralytics_thop','rfdetr_plus','thop','av','pytest',
              'pytorch_lightning','lightning','torchmetrics','tensorboard','tensorboardX','wandb','mlflow',
              'rfdetr.training','rfdetr.export','rfdetr.cli','onnx','onnxruntime','tensorflow','jax','triton',
              'IPython','notebook','setuptools','pip','PyInstaller','pkg_resources','matplotlib','pyarrow','pandas','polars',
              'roboflow','hotcoco','torch_hungarian'])
def keep(row):
    n = row[0].replace('\\','/'); base = n.rsplit('/',1)[-1].lower()
    return not (base.startswith(('opencv_videoio_ffmpeg','api-ms-win-','ext-ms-win-')) or base in {'ucrtbase.dll','nvcuda.dll','nvperf_host.dll'} or base.endswith(('.lib','.pdb','.h','.hpp')))
a.binaries = [x for x in a.binaries if keep(x)]
a.datas = [x for x in a.datas if keep(x) and '__pycache__' not in x[0]]
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='IVAD_RF_Worker',console=True,debug=False,upx=False)
coll=COLLECT(exe,a.binaries,a.datas,name='RF_Worker_Candidate',upx=False)
