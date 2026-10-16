"""Layout only: three tabs sharing configuration, task and cache state."""
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QDoubleSpinBox,QLabel,QScrollArea,QTabWidget,QSplitter,QGroupBox,QCheckBox,QMenu,QSizePolicy,QLayout
from ivad_app.gui.pages import button,table
from ivad_app.gui.video_player import VideoPlayer
from ivad_app.gui.time_range_slider import TimeRangeSlider

class OfflineDemoLayout:
    def build_layout(self):
        outer=QVBoxLayout(self);outer.setContentsMargins(5,5,5,5)
        title=QLabel('P3.5 · 离线 AI 识别演示');title.setObjectName('title');self.title_label=title;outer.addWidget(title)
        self.warning=QLabel('工程实验，未完成独立工业验证。先GPU预处理、再回放；预测不是工业报警。');self.warning.setWordWrap(True);outer.addWidget(self.warning)
        self.tabs=QTabWidget();self.tabs.setStyleSheet('QTabBar::tab {background:#176a94;color:white;padding:7px 12px;} QTabBar::tab:selected,QTabBar::tab:hover {background:white;color:#203047;} QTabWidget::pane {background:#f2f5fa;border:1px solid #cbd6e4;}');outer.addWidget(self.tabs,1)
        config=QWidget();demo=QWidget();details=QWidget()
        for body in [config,demo,details]:body.setObjectName('p35OfflineBody');body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.tabs.addTab(config,'识别配置与视频选择');self.tabs.addTab(demo,'AI 识别演示');self.tabs.addTab(details,'检测详情与导出');v=QVBoxLayout(config);v.setContentsMargins(5,5,5,5)
        self.top=QSplitter(Qt.Orientation.Horizontal);v.addWidget(self.top,1);self.config_info=QLabel("请选择视频和模型。");self.config_info.setWordWrap(True);v.addWidget(self.config_info)
        left=QGroupBox('识别配置');left.setStyleSheet('QGroupBox {background:#f2f5fa;color:#203047;}');ll=QVBoxLayout(left);ll.setContentsMargins(6,6,6,6);form=QFormLayout();form.setSpacing(4);ll.addLayout(form)
        self.project_label=QLabel('请先打开项目');self.project_label.setWordWrap(True);self.camera=QComboBox();self.model=QComboBox();self.gpu=QComboBox();self.confidence=QDoubleSpinBox();self.confidence.setRange(.01,1);self.confidence.setValue(.25);self.confidence.setSingleStep(.05)
        for name,widget in [('厂区 / 项目',self.project_label),('所属摄像头',self.camera),('模型版本',self.model),('置信度阈值',self.confidence),('NVIDIA GPU',self.gpu)]:form.addRow(name,widget)
        for c in [self.camera,self.model,self.gpu]:c.setMinimumContentsLength(10);c.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.other_models=QCheckBox('查看其他兼容实验模型');ll.addWidget(self.other_models)
        self.model_info=QLabel();self.model_info.setWordWrap(True);ll.addWidget(self.model_info)
        row=QHBoxLayout();v.addLayout(row);self.start_button=button('开始 AI 识别',self.start,True,'offline_start');self.cancel_button=button('取消处理',self.cancel,name='offline_cancel');self.reuse_button=button('使用已有缓存',self.use_cache,name='offline_reuse')
        for b in [self.start_button,self.cancel_button,self.reuse_button]:row.addWidget(b)
        self.refresh_button=button('刷新模型与视频',self.refresh,name='offline_refresh');row.addWidget(self.refresh_button);ll.addStretch()
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(left);scroll.setMinimumHeight(150);self.top.addWidget(scroll)
        right=QGroupBox('视频选择与原片预览（不运行AI）');right.setStyleSheet('QGroupBox {background:#f2f5fa;color:#203047;}');rr=QVBoxLayout(right);rr.setContentsMargins(6,6,6,6);rr.setSpacing(3)
        self.select_button=button('选择演示视频…',lambda:None,True,'offline_select');menu=QMenu(self.select_button);menu.addAction('从当前项目已有视频选择…',self.choose_project_video);menu.addAction('从本机选择新视频…',self.import_video);self.select_button.setMenu(menu);rr.addWidget(self.select_button)
        # Preserve the existing selection model without a second visible selection control.
        self.media=QComboBox(self);self.media.hide();self.media_info=QLabel('请选择录像；不通过文件名猜测摄像头。');self.media_info.setWordWrap(True);rr.addWidget(self.media_info)
        self.preview=VideoPlayer();self.preview.picture.setMinimumHeight(170);self.preview.picture.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored);self.preview.setMinimumHeight(225);self.preview.capture_button.hide();self.preview.previous.hide();self.preview.next.hide();self.preview.speed.hide();self.preview.goto.hide();self.preview.goto_button.hide();self.preview.layout().itemAt(2).layout().addWidget(self.preview.slider,1);self.preview.play_button.setMaximumWidth(70);self.preview.play_button.setStyleSheet('padding:3px 6px;');self.preview.info.setStyleSheet('font-size:11px;');rr.addWidget(self.preview,1)
        self.range_slider=TimeRangeSlider();rr.addWidget(self.range_slider);self.range_label=QLabel();self.range_label.setWordWrap(True);range_line=QHBoxLayout();range_line.addWidget(self.range_label,1);rr.addLayout(range_line)
        self.precise_toggle=QCheckBox('精确输入');range_line.addWidget(self.precise_toggle);self.precise=QWidget();line=QHBoxLayout(self.precise);line.setContentsMargins(0,0,0,0);self.start_time=QDoubleSpinBox();self.end_time=QDoubleSpinBox()
        for name,c in [('起点',self.start_time),('终点',self.end_time)]:c.setDecimals(3);c.setRange(0,1000000);c.setSuffix(' 秒');line.addWidget(QLabel(name));line.addWidget(c)
        rr.addWidget(self.precise);rr.removeWidget(self.preview);rr.addWidget(self.preview,1);self.precise.hide();self.precise_toggle.toggled.connect(self.precise.setVisible)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(right);scroll.setMinimumHeight(150);self.top.addWidget(scroll);self.top.setSizes([430,700])
        dv_demo=QVBoxLayout(demo);self.status_bar=QLabel('尚未开始识别');self.status_bar.setWordWrap(True);self.status_bar.setObjectName('notice');dv_demo.addWidget(self.status_bar);self.experiment_status=QLabel('工程实验模型，尚未完成独立工业验证。');self.experiment_status.setWordWrap(True);dv_demo.addWidget(self.experiment_status);lower=QWidget();lower.setStyleSheet("background:#f2f5fa;color:#203047;");lv=QVBoxLayout(lower);lv.setContentsMargins(0,0,0,0);lv.setSpacing(3);self.info=QLabel('选择视频 → 拖动片段 → 开始AI识别。');self.info.setWordWrap(True);lv.addWidget(self.info)
        self.cache_state=QLabel('未加载推理缓存。');self.cache_state.setWordWrap(True);v.insertWidget(1,self.cache_state)
        self.player=VideoPlayer();self.player.picture.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Ignored);self.player.picture.setMinimumHeight(170);self.player.capture_button.hide();self.player.layout().setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize);self.player.info.setWordWrap(True);lv.addWidget(self.player,1);self.timing=QLabel('播放器显示缓存相对时间，原录像位置见偏移提示。');self.timing.setWordWrap(True);lv.addWidget(self.timing);lv.setSizeConstraint(QLayout.SizeConstraint.SetMinimumSize);play_scroll=QScrollArea();play_scroll.setWidgetResizable(True);play_scroll.setWidget(lower);dv_demo.addWidget(play_scroll,1);self.focus_button=button('专注播放',lambda:self.set_focus_playback(not self.focused),name='offline_focus');focus_row=QHBoxLayout();focus_row.addWidget(self.focus_button);focus_row.addStretch();dv_demo.addLayout(focus_row);self.back_button=button('返回修改配置',lambda:self.tabs.setCurrentIndex(0),name='offline_back');focus_row.addWidget(self.back_button)
        dv=QVBoxLayout(details);self.task_details=QLabel("暂无任务");self.task_details.setWordWrap(True);dv.addWidget(self.task_details);self.history=QComboBox();self.history.addItem('选择本项目已完成演示缓存',None);dv.addWidget(self.history);self.detail_context=QLabel('尚未选择推理结果。');self.detail_context.setWordWrap(True);dv.addWidget(self.detail_context)
        self.show_all=QCheckBox('显示全部已处理帧（包括无检测目标）');dv.addWidget(self.show_all);self.results=table(['视频相对时间（秒）','检测类别','Confidence','模型版本','框数','来源视频']);dv.addWidget(self.results,1)
        self.diagnostics=QLabel('任务日志：任务中心 / 诊断日志。');self.diagnostics.setWordWrap(True);dv.addWidget(self.diagnostics);row=QHBoxLayout();dv.addLayout(row);self.export_button=button('导出带框视频 + CSV/JSON',self.export,name='offline_export');self.shot_button=button('导出当前检测截图',self.screenshot,name='offline_screenshot');row.addWidget(self.export_button);row.addWidget(self.shot_button)
        self.history.currentIndexChanged.connect(self.load_history);self.results.itemSelectionChanged.connect(self.seek_result);self.show_all.toggled.connect(self.render_results);self.media.currentIndexChanged.connect(self.select_media);self.model.currentIndexChanged.connect(self.show_model);self.camera.currentIndexChanged.connect(self.filter_models);self.other_models.toggled.connect(self.filter_models)
        self.range_slider.rangeChanged.connect(self.slider_changed);self.range_slider.seekRequested.connect(self.preview_seek);self.start_time.valueChanged.connect(lambda:self.precise_changed(0));self.end_time.valueChanged.connect(lambda:self.precise_changed(1));self.confidence.valueChanged.connect(self.configuration_changed)
        self.refresh_button.setToolTip('读取模型、视频及已检查GPU；首次请在设备与后端执行GPU检查。');self.confidence.setToolTip('预测阈值，不是工业报警阈值。修改只影响新任务，旧回放仍按其原参数显示。')
