# 分发检查与冻结

- [x] 标注端不引用AI环境；Full源码保持独立。
- [x] 自研Apache LICENSE/NOTICE和环境依赖登记。
- [x] 开发x64 EXE编译；不包含运行库重分发文件。
- [ ] 干净Windows 10/11 x64首次安装运行。
- [ ] 正式安装、升级、卸载；卸载默认保留业务项目。
- [ ] 跨版本迁移与备份恢复用户级演练。
- [ ] 用户批准正式打包、签名、公开或分发。
- [ ] 实际候选包LICENSE/NOTICE/hash/源码材料与依赖终审。
- [ ] Windows运行库/媒体组件先决条件与必要再分发条款。
- [ ] 编码专利、素材/商标权利及合同风险独立处理。

发行冻结=true。用户2026-10-26一次性授权的Annotator便携测试ZIP已固化；授权已消耗。没有安装程序，后续新版打包仍冻结。

未来打包必须采用文件白名单，包含LICENSE/NOTICE、THIRD_PARTY_LICENSES、SBOM及适用源码/构建材料，逐文件校验哈希。不得递归打包项目；禁止src/Full、.venvs、artifacts、用户数据、模型权重、测试素材、网络配置快照和审计缓存。

恢复设计：project.ids.json原子替换并保留.backup；IDS包hash和staging验证后提交；增量只接受精确基线，否则不改目标。未知schema拒绝，不做有损迁移。断电可能留下未引用资产或staging目录，尚无自动垃圾回收/跨进程重启恢复验收，不宣称零丢失。

## 本次限定交付终审

- [x] 用户本次便携测试ZIP授权，已消耗CONSUMED_FROZEN；未授权公开/签名/后续自动打包。
- [x] 实际ZIP12文件白名单、许可证/NOTICE/SBOM/构建记录/hash/隐私审计。
- [x] 外部.NET Framework/WPF/MF运行条件、官方说明和只读检测；无Microsoft运行时再分发。
- [x] 独立TEMP目录、普通用户、中文空格/长文件名、实际子进程和IDS完整性。
- [x] 受控清单提交前硬终止后恢复最后提交数据；不是所有断电场景通过。
- [ ] 真实GUI/物理Ctrl+S（工具审批拒绝）。
- [ ] 其他Windows电脑、AMD/NVIDIA/无独显、纯4.8/缺运行时。

证据：evidence/portable-delivery.json及reports/V1_1_PORTABLE_DELIVERY_20261026.md。原先勾选项中的全面公开分发/安装器要求仍未授权或未验证。
