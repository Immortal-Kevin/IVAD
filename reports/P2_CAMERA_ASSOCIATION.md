# P2 摄像头UUID管理与关联

日期：2026-10-14。工程1.0.0-P2-UX.2，便携候选1.0.0-P2-Beta.2，Schema0005。仅P2，未进入P3–P6。

## 数据关系

每个项目数据库新增cameras表，id为稳定UUID；name为可重名显示名称，legacy_key仅为旧编号迁移/导入别名。MediaAsset.camera_id、ROI.camera_id为项目内受服务验证的关系；SQLite不重建旧表增加外键。Frame→MediaAsset→Camera、Annotation→Frame关系自然继承，不复制摄像头名称作为主键。

0005把既有非空media/ROI文本编号映射到同一UUID，并将camera级ROI scope改为camera:UUID。原ROI id、payload、revision与历史保持；旧文本字段保留兼容信息。新导入旧编号也建立/复用UUID。无编号仍可正常标注。

关联事务同时更新原录像及来源CLIP，已抽取图片/标注通过媒体继承；以后生成片段提交时读父媒体最新camera_id。旧数据集快照不改。新快照按UUID分组，名称变化不造成来源泄漏。

## GUI

右侧滚动至“所属摄像头（录像及其片段共用）”→选择已有项或“新建摄像头…”→“保存摄像头关联”。编辑名称保持UUID；同名由短ID区分。未保存选择在同录像内保留，过期异步结果不重置选择。切换来源录像后显示其实际关联。

ROI视频级/摄像头级/目标标注独立，camera scope在未关联时禁用，不阻断保存。机位变化可重新绘制ROI并保存其版本历史。

## 实测

真实测试摄像头“1204-1202给煤机摄像头”，UUID `29bac15c-d02e-4134-a12e-7a3e82d13554`，在独立副本创建。重命名并恢复原名UUID不变；原录像、实际新MP4片段、片段抽取图片继承相同UUID；摄像头ROI可读取，普通目标数据保持。clip id `adae042c-21cf-4a63-8e0b-f2b8f797b48b`，新帧 id `4ef7faf0-3c71-404c-a7bc-460f29334bc6`。没有接入实时摄像头、RTSP或报警。

旧0004→0005前SQLite backup API生成备份；复制真实项目的全部Annotation行及AnnotationRevision行升级前后逐列相同。原“测试1号”项目没有升级或写入，用户历史仍原址。
