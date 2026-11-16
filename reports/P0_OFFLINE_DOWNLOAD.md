# P0 人工离线下载清单

生成日期：2026-10-12。只暂停未完整取得的训练依赖与模型安装；不得进入 P1。

最小人工步骤：

1. 在网络稳定的电脑下载本表文件。可将 scripts/p0/download_offline.ps1 与 reports/raw/offline_missing_manifest.json 放到同一目录，运行下方命令；脚本仅 HTTPS 下载与官方 SHA256 校验，不安装任何包。
2. 将生成的 offline_download 文件夹复制到本项目 artifacts/p0/offline_drop；保留原始文件名，然后告知 Codex。Codex 再校验 hash、ABI 和依赖闭包，先完成 XPU 基础门禁，再处理 YOLO 扩展依赖与测试。

```powershell
powershell -NoProfile -File ./download_offline.ps1 -Manifest ./offline_missing_manifest.json -Destination ./offline_download
```

两个已有 venv 不需要重建，Python 仍为 CPython 3.14.7 / Windows x64。cp314-cp314-win_amd64 为普通 CPython 3.14 ABI（不是 cp314t）；abi3 表示可兼容较新 CPython 的稳定 ABI；py2.py3-none-win_amd64 为厂商原生 runtime 的无 Python ABI wheel。权重 .pt 没有 wheel ABI，但只能以可信官方来源加载。

XPU 基础依赖闭包 33 项，完整大小 1,502,655,954 bytes；其中已经取得的 NumPy 自动排除，不需重复下载。本轮也已核对含 YOLO 的完整 P0 候选闭包 62 项；这仍是待安装候选清单，不是已验证的软件环境锁。

SHA256 校验示例（将值与表中/JSON中的官方期望值逐字比较）：

```powershell
(Get-FileHash -Algorithm SHA256 -LiteralPath './torch-2.14.1+xpu-cp314-cp314-win_amd64.whl').Hash.ToLowerInvariant()
```

| 包/版本 | 文件名及 ABI/平台 | 官方下载 URL | 官方 SHA256 |
|---|---|---|---|
| h11 0.16.0 | `h11-0.16.0-py3-none-any.whl` | [下载](https://files.pythonhosted.org/packages/04/4b/29cac41a4d98d144bf5f6d33995617b185d14b22401f75ca86f384e87ff1/h11-0.16.0-py3-none-any.whl) | `63cf8bbe7522de3bf65932fda1d9c2772064ffb3dae62d55932da54b31cb6c86` |
| torch 2.14.1+xpu | `torch-2.14.1+xpu-cp314-cp314-win_amd64.whl` | [下载](https://download.pytorch.org/whl/xpu/torch-2.14.1%2Bxpu-cp314-cp314-win_amd64.whl) | `740a95ff335b8cdffb16b542096a2f8e2f21ce058f4fe23179a02557c5132ed4` |
| triton-xpu 3.8.0 | `triton_xpu-3.8.0-cp314-cp314-win_amd64.whl` | [下载](https://download.pytorch.org/whl/triton_xpu-3.8.0-cp314-cp314-win_amd64.whl) | `75a1d076576610661f5eb5701f5e7ab82d74c5ddb75975efa78d7cf6db81d6d1` |
| intel-openmp 2026.1.0 | `intel_openmp-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/6e/cc/b4cb4ed4a1cca9dcc63cec93f7813ef3840f37d8bd30c06b8013948edc00/intel_openmp-2026.1.0-py2.py3-none-win_amd64.whl) | `8f9f86d93da9d549eec7bae26d65d6188ed748792ce655b5cdbc2e1a15cb7206` |
| mkl 2026.1.0 | `mkl-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/d6/bd/e35bd5477278c91b0f5d4733b13009d183c284d636d68c649204858c207a/mkl-2026.1.0-py2.py3-none-win_amd64.whl) | `8194a8270d70622eff00eec84c793efc382b14848b98c3ace6bacdda42170a80` |
| intel-opencl-rt 2026.1.0 | `intel_opencl_rt-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/b4/8f/574738fd8f384c635f50a3f78e5f47763020486960ac83564a954b82bec7/intel_opencl_rt-2026.1.0-py2.py3-none-win_amd64.whl) | `0967dc144f9cdf3aaa0fc722b92a54119cff9867f0b07e8dee8b8c0a88f05e44` |
| intel-sycl-rt 2026.1.0 | `intel_sycl_rt-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/c8/0a/e39270bde66bedc4aa68fb0f9cd23f7e251d007cf1a6552441475b4cc890/intel_sycl_rt-2026.1.0-py2.py3-none-win_amd64.whl) | `307d7022583d929e3091eadcea15fd3440fb68c35cd20094f2bf8597f936bfd9` |
| onemkl-sycl-sparse 2026.1.0 | `onemkl_sycl_sparse-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/10/f3/71110f3ab8566fd1e7e7fdf85ca01d0c75fcd18e0b1d705fcc7f470df752/onemkl_sycl_sparse-2026.1.0-py2.py3-none-win_amd64.whl) | `b8ded2ac3a693089fa42e600b22ccd8a84c67017d2e32faf5a17272b564a1eed` |
| onemkl-sycl-blas 2026.1.0 | `onemkl_sycl_blas-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/6b/f9/c39f81e686db4be90cb79e14ca5298772c8584de8afb5518aa2dd75abb6d/onemkl_sycl_blas-2026.1.0-py2.py3-none-win_amd64.whl) | `c4478971431ac022a1b8268655bdb8cc49c877c93e8700e68e18c8271be42993` |
| onemkl-sycl-rng 2026.1.0 | `onemkl_sycl_rng-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/26/b5/bbbb459df6cfba8d4f9f034ec21478eef820c7377e3de46e4ac954ca21f8/onemkl_sycl_rng-2026.1.0-py2.py3-none-win_amd64.whl) | `fb5f168c5032777fa65022272d77e2c67ada06c4d89459a2d08cd0b2ad56c041` |
| onemkl-sycl-lapack 2026.1.0 | `onemkl_sycl_lapack-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/1f/d1/46baabeb2e855d840dfb10e92a86f8a47299ee64f9325f7635bc8265d7a9/onemkl_sycl_lapack-2026.1.0-py2.py3-none-win_amd64.whl) | `e25599ff5a23439d52021ed2f29bf0450a5bfd77495084694032d0bd8c4188ba` |
| onemkl-sycl-dft 2026.1.0 | `onemkl_sycl_dft-2026.1.0-py2.py3-none-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/01/af/ea8b355642e61c0176d033f873917c707ff8fb7d8a66c51ef0c4ecd94cf9/onemkl_sycl_dft-2026.1.0-py2.py3-none-win_amd64.whl) | `f57ec87c2af23dbae00f94fd3941c2443beb5330c82eec8475d8c219b13e35bc` |
| networkx 3.6.1 | `networkx-3.6.1-py3-none-any.whl` | [下载](https://files.pythonhosted.org/packages/9e/c9/b2622292ea83fbb4ec318f5b9ab867d0a28ab43c5717bb85b0a5f6b3b0a4/networkx-3.6.1-py3-none-any.whl) | `d47fbf302e7d9cbbb9e2555a0d267983d2aa476bac30e90dfbe5669bd57f3762` |
| sympy 1.14.0 | `sympy-1.14.0-py3-none-any.whl` | [下载](https://files.pythonhosted.org/packages/a2/09/77d55d46fd61b4a135c444fc97158ef34a095e5681d0a6c10b75bf356191/sympy-1.14.0-py3-none-any.whl) | `e091cc3e99d2141a0ba2847328f5479b05d94a6635cb96148ccb3f34671bd8f5` |
| mpmath 1.3.0 | `mpmath-1.3.0-py3-none-any.whl` | [下载](https://files.pythonhosted.org/packages/43/e3/7d92a15f894aa0c9c4b49b8ee9ac9850d6e63b03c9c32c0367a13ae62209/mpmath-1.3.0-py3-none-any.whl) | `a0b2b9fe80bbcd81a6647ff13108738cfb482d481d826cc0e02f5b35e5c88d2c` |
| setuptools 78.1.0 | `setuptools-78.1.0-py3-none-any.whl` | [下载](https://files.pythonhosted.org/packages/54/21/f43f0a1fa8b06b32812e0975981f4677d28e0f3271601dc88ac5a5b83220/setuptools-78.1.0-py3-none-any.whl) | `3e386e96793c8702ae83d17b853fb93d3e09ef82ec62722e61da5cd22376dcd8` |
| polars-runtime-32 2.0.0 | `polars_runtime_32-2.0.0-cp310-abi3-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/61/59/8c9fd7199f7c4eb1b64e640306a946a2e4a46337b3bbb33b840972c7d84b/polars_runtime_32-2.0.0-cp310-abi3-win_amd64.whl) | `7da1caf3c7b4f397fb213c984013a0c755557619a2d511899a1ff74392484078` |
| opencv-python 5.0.0.93 | `opencv_python-5.0.0.93-cp37-abi3-win_amd64.whl` | [下载](https://files.pythonhosted.org/packages/21/f0/9fa6e85cb10c8eb36a0222d27e50fe381b86ce49a55446bf39f491727564/opencv_python-5.0.0.93-cp37-abi3-win_amd64.whl) | `f90ba04b8f73bc5c3814037699739f0156f597338a98f05956c684e7c3ca10d2` |
| yolo26n official assets v8.4.0 | `yolo26n.pt` | [下载](https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt) | `9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef` |

实际来源：普通依赖来自官方 PyPI JSON；torch/torchvision/triton-xpu 来自官方 XPU 索引及经实测可用的官方 CDN 等价路径；模型 digest 来自官方 GitHub release API。TLS 保持验证，未知或 hash 不符文件不安装。

网络正常后可先验证 core 清单中的全部 wheel，再在 intel_train 使用 --no-index --find-links 离线安装；不得让 pip 用 CPU torch 替换 +xpu。安装动作当前暂停，等待完整离线文件。
