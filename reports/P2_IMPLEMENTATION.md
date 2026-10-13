# P2 实施报告

状态：PASS（P2工程功能；工业场景未验收）。

执行日期：2026-10-13，Windows本机。P2最终自动化 71 passed / 0 failed / 0 errors，P1回归 37 项；证据 artifacts/p2/pytest.xml、pytest.log。源码本地 nvidia-first（报告生成时HEAD 2626af8，最终提交见Git记录）。未经用户另行批准不得进入P3–P6。

所有视频为scripts/p2/make_samples.py自行生成：320×180、36帧、运动色块和文字；无第三方/工厂素材。人工测试几何只验证工具和格式，不代表选煤厂缺陷真值。真实厂区视频/标注质量/工业精度：NOT TESTED。

复用ivad_app统一MainWindow、ApplicationServices、AsyncRunner、SQLite、JobService与日志。新增MediaService / AnnotationService / DatasetService、共享FileVideoSource及格式适配器；P2没有网络服务、第二套桌面入口、AI推理或训练。

COPY默认/REFERENCE、SHA256去重、后台导入、磁盘检查、失败状态、Missing引用重新定位；真实画面播放/暂停/速度/逐帧/跳转/捕获；实际PTS范围有限固定与变化抽帧，参数/任务/来源完整追溯。全部长操作后台执行，Qt信号回主线程。

真实鼠标矩形与多边形创建、移动、角点/顶点编辑、删除、撤销/重做、缩放/平移；视频/摄像头独立ROI、整帧/片段标签、标签库、审核、乐观修订与自动保存。源帧读取校验hash；保存失败阻止静默切换/退出。

人工已审核数据集检查、来源组划分、随机风险确认、精确重复去重/近重复警告、冻结图片与真值快照、版本查询、四种导出及hash清单。小来源组比例以实际统计为准，不伪造70/20/10。

Schema 0003新增业务表与任务payload/result，保留P1表及备份。完整模型见docs/DATABASE_SCHEMA.md。依赖仅给.venv-p1增加4个锁定包，P0未变。

截图 artifacts/p2/gui-annotation-native.png、gui-media-native.png、gui-dataset-native.png；额外100/200%截图及DPI JSON。原生DPR1.75；通过进程局部倍率得到DPR1.0/2.0，不修改Windows显示设置。截图目视发现属性拥挤后改为可滚动白色面板，已重新生成。

研发中发现并修复：list方法遮蔽类型注解；已有项目窗口表单初始化缺失；项目/视频切换旧回调污染；高DPI属性压缩；数据库提交异常导致目录未回退。最后全套通过。测试脚本初次证据生成缺少取消事件、测试末尾变量位置错误，修复后重跑，不计为未解决产品失败。

当前播放器不含音频；大规模/4K/长视频压力未测；多边形为简单单轮廓，洞/多部件/刷子Mask不支持。完整断电恢复、安装包、RTSP、AI辅助、工业报警和Intel独立验证不在P2。
