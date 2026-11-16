# 第三方许可证与来源登记

## Annotator / IDS

自研代码Apache-2.0，LICENSE原文来源https://www.apache.org/licenses/LICENSE-2.0.txt；本地SHA256：`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`。
当前产品无NuGet/pip/npm第三方依赖、无随附字体/图标/FFmpeg/模型。系统WPF字体不复制入项目。

| 环境组件 | 角色 | 许可/证据 | 随附 |
|---|---|---|---|
| Windows .NET Framework/WPF | 托管运行与界面 | Microsoft系统条款；https://learn.microsoft.com/en-us/dotnet/framework/get-started/system-requirements | 否 |
| Windows Media Foundation | 软件视频解码、真实样本时间 | Microsoft系统组件；https://learn.microsoft.com/en-us/windows/win32/medfound/source-reader | 否 |
| C# compiler / PowerShell | 开发编译与自动化 | 现有系统开发工具，单独登记，非Apache假定 | 否 |
| CPython 3.14.7 / pip 26.2.1 | 元数据和文件审计 | PSF / MIT及pip内嵌工具各自许可；不属于产品运行时 | 否 |

## Full / NVIDIA候选递归依赖

固定根：rfdetr 1.11.2 [train]；Windows x64 / CPython3.12目标。仅元数据解析，不安装、不下载权重。候选并非成功安装锁。所有工件的内嵌许可证未完成前保持BLOCKED。
解析候选数：88；未解决解析错误：0。原始请求/依赖/URL/hash/标签见evidence/rfdetr/resolution.json。解析器为有界约束累积，不冒充完整回溯安装求解器。

| 包 | 固定候选版本 | 声明许可（截短） | 决定 |
|---|---|---|---|
| accelerate | 1.15.0 | Apache | BLOCKED：待具体工件/内嵌许可与功能验证 |
| aiohappyeyeballs | 2.7.1 | PSF-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| aiohttp | 3.14.5 | Apache-2.0 AND MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| aiosignal | 1.4.0 | Apache 2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| annotated-doc | 0.0.5 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| annotated-types | 0.8.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| anyio | 4.15.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| attrs | 26.1.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| av | 19.0.2 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| certifi | 2026.10.23 | MPL-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| charset-normalizer | 3.5.2 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| click | 8.5.0 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| colorama | 0.4.6 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| contourpy | 1.4.0 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| cycler | 0.12.1 | Copyright (c) 2015, matplotlib project All rights reserved. Redistribution and use in source and binary forms, with or without modification, are permitted provided that the followi | BLOCKED：待具体工件/内嵌许可与功能验证 |
| defusedxml | 0.7.1 | PSFL | BLOCKED：待具体工件/内嵌许可与功能验证 |
| faster-coco-eval | 1.8.0 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| filelock | 4.2.4 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| filetype | 1.2.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| fonttools | 4.67.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| frozenlist | 1.8.0 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| fsspec | 2026.9.0 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| h11 | 0.16.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| hf-xet | 1.7.0 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| hotcoco | 1.0.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| httpcore2 | 2.16.0 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| httpx2 | 2.16.0 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| huggingface-hub | 2.3.0 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| idna | 3.20 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| jinja2 | 3.1.6 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| kiwisolver | 1.5.1 | ========================= The Kiwi licensing terms ========================= Kiwi is licensed under the terms of the Modified BSD License (also known as New or Revised BSD), as fol | BLOCKED：待具体工件/内嵌许可与功能验证 |
| lightning-utilities | 0.15.3 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| markdown-it-py | 4.2.0 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| markupsafe | 3.0.4 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| matplotlib | 3.11.2 | License agreement for matplotlib versions 1.3.0 and later ========================================================= 1. This LICENSE AGREEMENT is between the Matplotlib Development  | BLOCKED：待具体工件/内嵌许可与功能验证 |
| mdurl | 0.1.2 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| mpmath | 1.3.0 | BSD | BLOCKED：待具体工件/内嵌许可与功能验证 |
| multidict | 7.2.1 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| networkx | 3.7 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| numpy | 2.5.4 | BSD-3-Clause AND 0BSD AND MIT AND Zlib AND CC0-1.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| opencv-python-headless | 5.0.0.93 | Apache 2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| peft | 0.21.2 | Apache | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pillow | 13.0.0 | MIT-CMU | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pillow-avif-plugin | 1.6.0 | MIT License | BLOCKED：待具体工件/内嵌许可与功能验证 |
| propcache | 0.5.4 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| psutil | 7.2.2 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pyarrow | 26.0.0 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pycocotools | 2.0.11 | FreeBSD | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pydantic | 2.14.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pydantic-core | 2.50.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pydeprecate | 0.9.0 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pygments | 2.21.0 | BSD-2-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pyparsing | 3.3.3 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| python-dateutil | 3.0.0 | Dual License | BLOCKED：待具体工件/内嵌许可与功能验证 |
| python-dotenv | 1.2.4 | BSD-3-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pytorch-lightning | 2.6.6 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| pyyaml | 6.0.3 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| regex | 2026.9.29 | Apache-2.0 AND CNRI-Python | BLOCKED：待具体工件/内嵌许可与功能验证 |
| requests | 2.34.2 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| requests-toolbelt | 1.0.0 | Apache 2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| rfdetr | 1.11.2 | Apache License 2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| rich | 15.0.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| roboflow | 1.7.2 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| safetensors | 0.8.0 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| scipy | 1.18.1 | Copyright (c) 2001-2002 Enthought, Inc. 2003, SciPy Developers. All rights reserved. Redistribution and use in source and binary forms, with or without modification, are permitted  | BLOCKED：待具体工件/内嵌许可与功能验证 |
| setuptools | 84.2.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| shellingham | 1.5.4 | ISC License | BLOCKED：待具体工件/内嵌许可与功能验证 |
| simplejpeg | 1.9.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| six | 1.17.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| supervision | 0.31.2 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| sympy | 1.14.0 | BSD | BLOCKED：待具体工件/内嵌许可与功能验证 |
| tokenizers | 0.23.3 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| torch | 2.14.1 | Apache-2.0 AND Apache-2.0 WITH LLVM-exception AND BSD-2-Clause AND BSD-3-Clause AND BSL-1.0 AND MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| torch-hungarian | 0.1.0rc0 | UNKNOWN | BLOCKED：待具体工件/内嵌许可与功能验证 |
| torchmetrics | 1.8.2 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| torchvision | 0.29.1 | BSD | BLOCKED：待具体工件/内嵌许可与功能验证 |
| tqdm | 4.70.1 | MPL-2.0 AND MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| transformers | 5.20.2 | Apache 2.0 License | BLOCKED：待具体工件/内嵌许可与功能验证 |
| truststore | 0.10.5 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| typer | 0.25.1 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| typing-extensions | 4.16.0 | PSF-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| typing-inspection | 0.4.4 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| tzdata | 2026.5 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| ultrafast-pycocotools | 0.1.14 | BSD-2-Clause | BLOCKED：待具体工件/内嵌许可与功能验证 |
| urllib3 | 2.8.0 | MIT | BLOCKED：待具体工件/内嵌许可与功能验证 |
| vernier | 0.5.4 | MIT OR Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |
| yarl | 1.25.1 | Apache-2.0 | BLOCKED：待具体工件/内嵌许可与功能验证 |

审计过小wheel的LICENSE/METADATA及hash见evidence/rfdetr/artifact_review.json；只保留声明与证据，不安装候选wheel。PyTorch/CUDA大工件未批准。旧环境和下载缓存完全排除于候选分发。
