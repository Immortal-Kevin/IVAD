# v1.1 旧路线清理报告

依据：2026-10-26用户明确授权退休Ultralytics，移除其代码、依赖、权重和专用实验资产。项目根仍为IVAD_Platform_v1.0以保持路径稳定，产品基线已变为v1.1。

## 删除前证据

- evidence/legacy_deletion_manifest.json：745个文件，48142514 bytes，逐文件原路径/SHA256/用途。
- evidence/incompatible_legacy_deletion_manifest.json：追加4549个文件的原路径/大小/hash。
- evidence/legacy_installed_before.json：原安装包身份；uninstall_*.log/remove_*.log：实际卸载结果。
- evidence/legacy_manifest_changes.json：移除旧依赖条目的清单原hash。

## 已执行

卸载ultralytics 8.4.175、ultralytics-platform 0.1.83、ultralytics-thop 2.2.2；移除官方/实验YOLO权重、IR、模型特有脚本、训练输出、合成数据、bus样例、专用原始日志、配置/字体缓存及对应wheel。保留一份旧进度摘要解释历史，旧链接中已删除文件不再可复现，不伪造原日志。

追加移除两环境NumPy 2.5.4及wheel：实际Windows wheel的numpy.libs/libscipy_openblas*.dll许可证声明包含GPL-3.0-or-later WITH GCC-exception-3.1，B.1未批准此例外。移除退休训练环境OpenCV、matplotlib及setuptools相关实验安装/缓存；setuptools78.1.0内嵌autocommand2.2.2为LGPLv3，不能作为未审查例外沿用。没有删声明来保留二进制。

## 保留与限制

通用GPU探针、网络诊断、hash/续传工具、非Ultralytics的旧GPU工件及基础测试摘要保留；通用脚本已去除旧模型目标。旧环境现为退休资产，依赖可能不完整，不再是可执行训练环境或发行锁。保留不等于B.1审查通过；全部排除出Annotator/Full候选分发，禁止自动恢复安装。

OpenVINO包含名为region_yolo/reorg_yolo的通用算子头文件，这是OpenVINO自己的操作定义，不能因为字符串相同就当作Ultralytics安装；当前产品也不引用OpenVINO。

项目外父级同名目录未触碰。没有修改全局环境、其他AI项目、驱动、VPN/代理，未删除真实厂区/人工标注业务资产。所有删除均校验解析后的路径在项目内。

## 清理后验证

scripts/release_gate.ps1重新读取实际安装dist-info、嵌套dist-info、缓存wheel身份、产品源码与开发EXE引用。结果见evidence/installed_scan.json、wheel_scan.json、candidate_manifest.json与RELEASE_READINESS.md。字符串扫描不作为唯一证明；保留历史文档/删除清单中的名称不代表运行依赖。
