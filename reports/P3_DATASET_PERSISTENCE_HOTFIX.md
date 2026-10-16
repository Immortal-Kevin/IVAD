# P3 Dataset草稿持久化修复

日期：2026-10-16。功能PASS；新源码Schema0009，PACKAGING_FREEZE = TRUE。

## 消失根因与调查范围

对真实项目`E:\IVAD Project\测试1号\IVAD-fc4276bc-6919-42c6-8e56-234a9b9bd3e2`使用SQLite mode=ro检查，project.json与projects表UUID均为fc4276bc-6919-42c6-8e56-234a9b9bd3e2。当前库Schema0008、完整性ok，datasets/dataset_versions均0；同目录5份项目迁移备份（0003–0007）中也没有Dataset记录。当前库仍有251帧、217条Annotation，没有删除原图片或标注。详细SQL调查结果见draft-investigation.json。

代码检查与数据库结果一致：旧GUI的self.drafts字典仅驻留内存，点击“添加所选图片”没有SQLite事务；DatasetService只有freeze成功时才创建Dataset。下拉框原从冻结版本反推Dataset，不能呈现无版本草稿。因此不是未提交事务或筛选隐藏了已保存草稿，而是旧版没有持久保存功能。

未在查验范围找到“8525压滤板破裂测试1”，不能虚构恢复其上次选择或创建同名记录掩盖问题。此前未保存的内存草稿无法从这些空记录恢复；200张现存人工样本保留，可重新选择后正式保存。本轮没有在原项目补建同名数据集。

## 修复与数据关系

复用Dataset聚合，0009仅在原datasets表增加details JSON、revision，不另造同义Draft表。details保存所属Project UUID、Detection任务、Camera UUID集合、Fault UUID集合、更新时间，以及嵌入的draft成员/Annotation UUID和revision、划分设置、内容revision、保存时间和检查状态/签名。Dataset名称非主键，UUID稳定。

“保存数据集草稿”使用BEGIN IMMEDIATE事务与revision CAS；成功提交才在GUI显示时间和UUID。失败保留内存内容；重试沿用稳定UUID，不重复创建。相同机位可建多个不同故障数据集，正常图可独立引用而不写故障标签。多类别图片必须声明全部目标类别；检测类别映射以明确的Fault集合为准。跨摄像头须显式授权，新建另一个数据集/项目会重置旧授权。

当前采用手动保存，不提供自动保存。未保存修改有明确状态，切换Dataset/项目或退出可保存、放弃、取消；保存失败不继续切换/关闭。名单从所有Dataset记录重新加载，包括无冻结版本草稿和旧数据集，不再依赖版本列表。临时勾选与草稿成员分离，重复添加去重，删除成员不物理删除图片或标注。

## 200张真实副本验证

在独立副本选择8525的200张有效候选，输入“8525压滤板破裂测试1”，保存后关闭应用；第二个ApplicationServices/新Qt窗口重新打开同一副本项目并选择原Dataset，200个Frame/Annotation引用完全一致，Dataset UUID为920cdd1e-b164-4bfc-9e4b-261083bb7f83。修改后再保存仍使用此UUID，Dataset总数仍1。

这是新功能在副本中建立并恢复的草稿，不是声称找回原项目已经丢失的内存草稿。副本原类别实际名称“压滤版破裂”保持原样，未擅自重命名。

![已保存200张](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-lifecycle-20261016/real-gui-final/01-saved-200.png)

![应用关闭后重新打开200张](E:/IVAD Project/IVAD_Platform_v1.0_NVIDIA_Primary/artifacts/dataset-lifecycle-20261016/real-gui-final/02-reopened-200.png)

## 保护与使用

原项目本轮始终只读，保持Schema0008、Dataset数0；副本升级0009并通过原表/版本/UUID不变测试。下一次用户重启新源码并打开旧项目时，程序先自动备份SQLite，再追加两列。不要用旧Beta包打开已升级项目；不重新搭建环境或打包。

166项选取原库、录像、模型工件、历史证据和备份SHA256核验0变化；原库与本轮备份逻辑dump一致，详见protection-final.json。该结论只覆盖清单，不是全盘扫描。操作见docs/P3_DATASET_USER_GUIDE.md，其余测试见P3_DATASET_WORKFLOW_TEST_RESULTS.md。
