# 当前任务

2026-10-16 P3 Dataset Lifecycle & Split Workflow Hotfix PASS。原草稿只在GUI内存，真实当前库及5份备份Dataset/Version均空，未虚构恢复或在原项目新建同名记录。

新增显式草稿事务保存、UUID/CAS、项目/摄像头/故障关联、关闭切换保护和重启恢复。三预设及按组/正常异常/类别近似分配完成；版本跟随Dataset，冻结读取已保存VALIDATED修订、不可变快照和签名；训练按Dataset/Version选择，继续强制全量预检。

真实独立副本200成员重启恢复、同UUID再次保存、v1/v2不可变已验证。来源组1，标准200/0/0为LIMITED；明确工程小样本160/40/0（Train13正常147异常331目标；Val3正常37异常71目标），没有独立Test结论或实际训练。

主回归50+77=127不同用例通过，后续11项复验及200% GUI3项通过。Schema目标0009（Dataset两列），原项目保持0008只读，副本迁移验证。166项选取保护哈希0变化，原库/备份逻辑一致。下次重启新源码打开旧项目时先自动备份后迁移。

交付reports/P3_DATASET_PERSISTENCE_HOTFIX.md、P3_DATASET_SPLIT_PRESETS.md、P3_DATASET_VERSION_LIFECYCLE.md、P3_DATASET_WORKFLOW_TEST_RESULTS.md。指南已更新。原P3已完成成果不重复训练，当前Hotfix停止待审；PACKAGING_FREEZE=TRUE，不进入P4–P10，不生成分发包。
