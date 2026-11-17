from PyInstaller.utils.hooks import copy_metadata
module_collection_mode = 'pyz+py'
datas = []
for package in ['transformers', 'tokenizers', 'huggingface-hub', 'safetensors', 'torch', 'torchvision', 'numpy', 'packaging', 'PyYAML', 'regex', 'tqdm', 'requests', 'filelock']:
    try: datas += copy_metadata(package)
    except Exception: pass
hiddenimports = ['transformers.models.dinov2.configuration_dinov2', 'transformers.models.dinov2.modeling_dinov2',
                 'transformers.models.auto.configuration_auto', 'transformers.models.auto.modeling_auto']
