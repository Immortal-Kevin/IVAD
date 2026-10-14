# P2测试结果（补充修改后的当前版本）

日期：2026-10-14（Asia/Shanghai），P2补充修改；未进入P3–P6。基于原P2提交3b4b9ca增量实施，无第二套页面/业务系统，未新增环境或依赖。

主套84 passed / 0 failed / 0 errors / 0 skipped，原有71项全部保留（其中P1为37项），新增13项。另100%/200%DPI各1项同GUI流程复测通过，不重复计入主套。XML/log、截图、布局尺寸和保护校验都保存在artifacts/p2-adjustment/。

所有测试录像为自制色块/文字素材；长录像20秒500帧，截取[5,7)实际50帧；没有工厂隐私视频或第三方素材，真实工业数据NOT TESTED。

|模块|通过|失败|
|---|---:|---:|
|tests.test_crash_restart|1|0|
|tests.test_devices|4|0|
|tests.test_gui|8|0|
|tests.test_jobs_logs|6|0|
|tests.test_p2_adjustment|13|0|
|tests.test_p2_canvas|3|0|
|tests.test_p2_gui|1|0|
|tests.test_p2_media|11|0|
|tests.test_p2_safety|14|0|
|tests.test_p2_services|5|0|
|tests.test_projects_database|18|0|

命令：.venv-p1/Scripts/python.exe -m pytest tests -q --junitxml=artifacts/p2-adjustment/pytest.xml。本次耗时45.118秒。测试证据通过IVAD_TEST_EVIDENCE_DIR和IVAD_P2_GUI_EVIDENCE_DIR指向新目录；原artifacts/p2不覆盖。原2026-10-13的71项报告/证据保持在artifacts/p2及artifacts/p2-adjustment/history/。

新增13项：长REFERENCE片段/标注/数据集；4种无效时间范围；服务取消；模拟编码失败；0003→0004保留原媒体列和备份；真实GUI左右布局/标签色/帮助文字/保存及播放，切回长录像终点恢复完整时长；真实队列取消历史；VFR、非整数帧率、旋转分别裁剪校验。100/200%DPI各额外1项同GUI流程通过，原生175%在主套中通过。

额外迁移集成验证：从上一版真实P2持久化项目只读backup出副本，迁移0004后16张旧表的全部原列和数据逐行相同，生成迁移备份；原项目不写入。结果migration-check.json，未重复计入主套用例数。

保护结果：preservation.json=PASS，253份上一版P2原始证据hash不变，6份旧P2报告完整历史副本hash不变，P0/P1历史文件及原GPU/GUI全部包版本一致。没有下载新包、改驱动、全局Python或系统代理。本轮P1设备回归调用既有CUDA worker，未新增训练。

开发过程中修正测试注入路径、Qt自动化悬停事件投递及原生tooltip弹出测试。最终改为直接可见辅助说明并保留标准tooltip，验证可见文本；标签悬停色通过真实Qt事件渲染验证。最终没有未解决失败，不将故障注入称为现场断电/坏码流实验。

只保存第一个视频轨的画面，未保存音频；重新编码H.264 CRF18并非无损拷贝。片段时间按实际显示帧边界，范围采用[start,end)，首帧时间会重置为0，末帧显示时长可能与输入秒数存在帧级差异。最短100毫秒且至少两帧；片段再次裁片段明确拒绝。4K/小时级录像/大规模数据/真实选煤厂标注质量/断电强杀恢复未测，不作工业精度承诺。重复保存使用新UUID，不覆盖或幂等复用旧片段。
