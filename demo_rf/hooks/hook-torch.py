"""Inference demo: collect native Torch runtime, not every optional Python backend."""
from PyInstaller.utils.hooks import collect_dynamic_libs, copy_metadata
module_collection_mode = 'pyz+py'
binaries = collect_dynamic_libs('torch')
datas = copy_metadata('torch')
hiddenimports = ['torch._C', 'torch.cuda', 'torch.nn', 'torch.nn.functional', 'torch.jit']
