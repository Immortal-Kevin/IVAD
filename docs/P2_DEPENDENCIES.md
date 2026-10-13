# P2依赖与安装来源

仅追加到项目GUI .venv-p1，Python3.12.14；不新建第二套业务环境，不改变P0 GPU环境。requirements-p1.txt保持历史原状；P2入口requirements-p2.txt，全包锁定requirements-p2-lock.txt。pip check通过，所有P1原版本保持。来源官方PyPI files.pythonhosted.org；本次下载成功，无欠缺安装包。完整pip机器报告/安装日志保存在artifacts/p2/install.json及install.log。

|包|锁定版本|官方实际下载URL|SHA256|
|---|---|---|---|
|av|15.1.0|https://files.pythonhosted.org/packages/15/74/6f8e38a3b0aea5f28e72813672ff45b64615f2c69e6a4a558718c95edb9f/av-15.1.0-cp312-cp312-win_amd64.whl|d5921aa45f4c1f8c1a8d8185eb347e02aa4c3071278a2e2dd56368d54433d643|
|pillow|11.2.1|https://files.pythonhosted.org/packages/7c/18/24bff2ad716257fc03da964c5e8f05d9790a779a8895d6566e493ccf0189/pillow-11.2.1-cp312-cp312-win_amd64.whl|14e33b28bf17c7a38eede290f77db7c664e4eb01f7869e37fa98a5aa95978941|
|numpy|2.2.5|https://files.pythonhosted.org/packages/8b/09/4ffb4d6cfe7ca6707336187951992bd8a8b9142cf345d87ab858d2d7636a/numpy-2.2.5-cp312-cp312-win_amd64.whl|ced69262a8278547e63409b2653b372bf4baff0870c57efa76c5703fd6543282|
|PyYAML|6.0.2|https://files.pythonhosted.org/packages/0c/e8/4f648c598b17c3d06e8753d7d13d57542b30d56e6c2dedf9c331ae56312e/PyYAML-6.0.2-cp312-cp312-win_amd64.whl|7e7401d0de89a9a855c839bc697c079a4af81cf878373abd7dc625847d25cbd8|

PyAV wheel内置FFmpeg库，未安装系统ffmpeg/修改PATH；视频普通CPU解码属于P2非AI处理，GPU-only AI要求不变。PyAV/Pillow/NumPy/PyYAML和FFmpeg随包版权条款需要在未来正式安装/分发阶段保留与核对；此处不作商用法律结论。
