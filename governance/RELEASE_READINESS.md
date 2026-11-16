# Release Readiness — IVAD v1.1

工程检查: **PASS**；真实 GUI: **NOT TESTED**。
Annotator: **NOT VERIFIED**  
Full / NVIDIA: **BLOCKED**  
正式发行冻结：**true**。开发EXE不是安装程序。

| 检查 | 状态 | 证据方式 | 范围/限制 |
|---|---|---|---|
| A | PASS | actual service / media / child-process tests | Persistence, geometry, full/delta IDS, hashes, cancellation and rollback; no real mouse workflow claim |
| B | NOT TESTED | actual WPF startup; in-process controls / synthetic layout; real GUI NOT TESTED | 73 service/media passed / 0 failed; 37 WPF checks passed / 0 failed; computer-use rejected: Computer Use was not approved to use dev |
| C | PASS | actual compilation and PE inspection | Windows x64 development EXE; installer NOT TESTED |
| D | PASS | static source + actual assembly dependency inspection | Unexpected code tokens=[]; unexpected assembly refs=[]; Full separately BLOCKED |
| E | PASS | installed dist-info + wheel identity + source/PE inventory | Retired package/binary provenance is excluded, never automatically approved; violations=[] |
| F | PASS | not applicable, absence checked | No FFmpeg in candidate; exception is not exercised |
| G | BLOCKED | official pinned source/metadata/artifact review | RF-DETR Full closure, weights and NVIDIA run not approved; no downloaded weights or active model dependency |
| H | NOT TESTED | environment registry + static boundary | Windows OS APIs not redistributed; clean target/CUDA SDK distribution not verified |
| I | PASS | static documents and file hashes | Missing materials=[]; actual installer content NOT TESTED |
| J | PASS | explicit development candidate allowlist | Only self-built Annotator EXE; no dataset/model/font/private Full in candidate; full repository is NOT a distribution |
| K | NOT TESTED | static no-network source/assembly check; actual local execution | No network API in application; physical network-denied run NOT TESTED; no system proxy/firewall changes |
| L | NOT TESTED | actual IDS rollback tests + static lifecycle design | Installer/upgrade/uninstall/clean machine and power-loss recovery NOT TESTED; no installer authorized |

原始结果：evidence/release_gate.json、installed_scan.json、wheel_scan.json、candidate_manifest.json、assembly_references.json、runtime_environment.json和build/test-data。

任何历史环境、审计下载、候选元数据均不属于已批准发行依赖。未完成的证据不能由此脚本自动升级为READY。

## 本次一次性 Annotator 便携测试交付

- A 实际ZIP内容/材料审计：PASS（脚本随后再次核对实际ZIP）。
- B 本机独立目录可执行/内部WPF验收：PASS；真实鼠标/物理快捷键仍NOT TESTED。
- C 其他Windows电脑：NOT TESTED。
- 指定包：dist/IVAD-Annotator-v1.1-win-x64-portable.zip；普通发行/后续打包冻结保持，详见portable-authorization-20261026.json。
