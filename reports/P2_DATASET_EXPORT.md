# P2 数据集与导出报告

执行日期：2026-10-13，Windows本机。P2最终自动化 71 passed / 0 failed / 0 errors，P1回归 37 项；证据 artifacts/p2/pytest.xml、pytest.log。源码本地 nvidia-first（报告生成时HEAD 52d36f1，最终提交见Git记录）。未经用户另行批准不得进入P3–P6。

所有视频为scripts/p2/make_samples.py自行生成：320×180、36帧、运动色块和文字；无第三方/工厂素材。人工测试几何只验证工具和格式，不代表选煤厂缺陷真值。真实厂区视频/标注质量/工业精度：NOT TESTED。

一键启动实际验证PASS：独立smoke实例正常退出，默认实例实际窗口标题IVAD Platform 1.0.0-P2，保留运行供用户使用；证据launcher-validation.json。

人工REVIEWED/APPROVED入选；DRAFT/REJECTED不入选。COPY冻结图片，标注修订/类别/媒体/ROI/片段快照写不可覆盖vNNNN；清单hash保存在SQLite。每次导出校验清单和图片，不修改原版本。

独立验证脚本scripts/p2/validate_outputs.py读回12个实际输出目录（3个DPI证据项目×4格式），全部PASS。每项目3张图片/3目标/3独立录像，真实train=1,val=1,test=1；精确hash无交叉，来源组不跨划分。以下为首个项目：

|格式|图片|目标|实际划分|结果|
|---|---:|---:|---|---|
|coco|3|3|{'train': 1, 'val': 1, 'test': 1}|PASS|
|ivad_native|3|3|{'train': 1, 'val': 1, 'test': 1}|PASS|
|yolo_detect|3|3|{'train': 1, 'val': 1, 'test': 1}|PASS|
|yolo_segment|3|3|{'train': 1, 'val': 1, 'test': 1}|PASS|

YOLO Detection归一化中心宽高与原像素回算误差<1e-5；多边形转外接框明确警告，真多边形留native旁车。YOLO Segmentation为class+真实轮廓归一化坐标，含任何检测框时拒绝整个导出，不生成伪Mask或丢弃对象。data.yaml names类别与稳定UUID映射来自冻结版本，不随标签重命名变化。

COCO images/categories/annotations关系、真实polygon segmentation、bbox/area独立读回；Native保留所有原生语义、图片引用有效。四格式均附ivad_native.json和export_manifest.json，全部生成文件hash读回一致。无覆盖导出，目标带版本与UUID。

相同SHA256图片实际去重；dHash汉明距离≤4仅警告近重复。按camera或video分组，小组数导致比例近似，GUI显示真实统计。随机需明确风险选择；即使人工确认也保留泄漏警告。正常无目标导出空标签；异常/未知无目标不能当正常YOLO负样本。

新版本不会改变旧manifest字节；图片篡改拒绝导出；可捕获数据库提交失败实际回退.partial并回滚登记。强制断电的文件/数据库跨步骤窗口仍需人工一致性核对，未做电源故障实验。外部导出文件路径丢失会报告，程序不删除用户资源。

具备P3的合法工程输入：YES，已有真实可解析分割/检测文件和三份非空划分。具备选煤厂生产训练真值：NO，只有3张自制工程图片，不能评估模型泛化/工业准确率。未启动Ultralytics训练、未进行P3。
