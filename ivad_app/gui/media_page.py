from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QHBoxLayout,QVBoxLayout,QFormLayout,QComboBox,QLabel,QLineEdit,QDoubleSpinBox,QSpinBox,QCheckBox,
    QFileDialog,QSplitter,QWidget,QMessageBox,QTabWidget,QScrollArea,QHeaderView)
from ivad_app.gui.pages import Page,button,table
from ivad_app.gui.video_player import VideoPlayer

class MediaPage(Page):
    import_requested=Signal(dict)
    extract_requested=Signal(dict)
    capture_requested=Signal(str,int)
    load_requested=Signal(str)
    relocate_requested=Signal(str,str)
    clip_requested=Signal(dict)
    clip_file_requested=Signal(dict)
    clip_delete_requested=Signal(str,int)
    check_requested=Signal()
    cancel_requested=Signal()
    labels_requested=Signal()
    def __init__(self):
        super().__init__('视频管理与抽帧','左侧管理录像，右侧操作选中录像；变化筛选不等于工业异常判断。')
        self.media_id=None;self.media_rows=[];self.clip_rows=[];self.selected_clip=None;self.selected_media=None
        self.splitter=QSplitter(Qt.Orientation.Horizontal);self.layout.addWidget(self.splitter,1)
        left=QWidget();left.setMinimumWidth(300);ll=QVBoxLayout(left);ll.setContentsMargins(0,0,0,0)
        self.mode=QComboBox();self.mode.addItem('复制到项目（默认）','COPY');self.mode.addItem('外部引用','REFERENCE')
        ll.addWidget(self.mode);ll.addWidget(button('批量导入录像…',self.choose_import,True,'import_media'))
        self.camera=QLineEdit();self.camera.setPlaceholderText('摄像头编号（可选）');self.site=QLineEdit();self.site.setPlaceholderText('厂区（可选）');self.equipment=QLineEdit();self.equipment.setPlaceholderText('设备（可选）')
        self.import_metadata=QWidget();meta_layout=QVBoxLayout(self.import_metadata);meta_layout.setContentsMargins(0,0,0,0)
        for widget in [self.camera,self.site,self.equipment]:meta_layout.addWidget(widget)
        self.import_metadata.hide();ll.addWidget(button('导入信息（可选，展开/收起）',lambda:self.import_metadata.setVisible(not self.import_metadata.isVisible())));ll.addWidget(self.import_metadata)
        self.table=table(['录像','方式','状态','时长','编码','分辨率']);self.table.setObjectName('media_table');self.table.setMinimumHeight(220)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        for i,width in enumerate([260,80,80,90,80,110]):self.table.setColumnWidth(i,width)
        self.table.setHorizontalScrollMode(self.table.ScrollMode.ScrollPerPixel);self.table.setVerticalScrollMode(self.table.ScrollMode.ScrollPerPixel)
        self.table.itemSelectionChanged.connect(self.select_media);ll.addWidget(self.table,1)
        row=QHBoxLayout();row.addWidget(button('重新定位引用…',self.relocate));row.addWidget(button('一致性检查',self.check_requested.emit));ll.addLayout(row)
        self.splitter.addWidget(left)
        self.operations_scroll=QScrollArea();self.operations_scroll.setWidgetResizable(True)
        right=QWidget();right.setObjectName('media_operations');right.setStyleSheet('QWidget#media_operations { background:#f2f5fa; }');right.setMinimumWidth(480);rr=QVBoxLayout(right);rr.setContentsMargins(5,0,5,0);self.operations_scroll.setWidget(right);self.splitter.addWidget(self.operations_scroll)
        rr.addWidget(QLabel('统一时间范围：用于抽帧、片段标签及保存视频片段（相对录像起点）。'))
        self.start=QDoubleSpinBox();self.end=QDoubleSpinBox()
        for w in [self.start,self.end]:w.setDecimals(3);w.setRange(0,10000000);w.setSuffix(' 秒')
        self.start.setObjectName('sampling_start');self.end.setObjectName('sampling_end')
        ranges=QFormLayout()
        for text,w,handler in [('起点时间',self.start,lambda:self.start.setValue(self.player.position_us/1e6)),('终点时间',self.end,lambda:self.end.setValue(self.player.position_us/1e6))]:
            line=QWidget();row=QHBoxLayout(line);row.setContentsMargins(0,0,0,0);row.addWidget(w);row.addWidget(button('当前为'+('起点' if w is self.start else '终点'),handler));ranges.addRow(text,line)
        self.start.setToolTip('从录像哪个时间开始处理，单位为秒。');self.end.setToolTip('处理到哪个时间结束，必须晚于起点且不超出录像时长。');rr.addLayout(ranges)
        self.range_info=QLabel();self.range_info.setWordWrap(True);rr.addWidget(self.range_info)
        self.start.valueChanged.connect(self.update_range);self.end.valueChanged.connect(self.update_range)
        self.tabs=QTabWidget();self.tabs.setObjectName('media_tabs');self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setMouseTracking(True);self.tabs.tabBar().setAttribute(Qt.WidgetAttribute.WA_Hover,True)
        self.tabs.setStyleSheet('QTabBar::tab { background:#176a94; color:white; padding:8px 9px; border:1px solid #b9d4e3; } QTabBar::tab:hover, QTabBar::tab:selected { background:white; color:#111111; } QTabWidget::pane { border:1px solid #b9d4e3; background:#f2f5fa; }')
        self.player=VideoPlayer();self.player.setMinimumHeight(330);self.tabs.addTab(self.player,'播放与定位');self.player.capture_requested.connect(lambda t:self.capture_requested.emit(self.media_id,t) if self.media_id else None)
        extraction=QWidget();extraction.setObjectName('media_sampling');extraction.setStyleSheet('QWidget#media_sampling { background:#f2f5fa; }');form=QFormLayout(extraction)
        explanation=QLabel('先确定上方范围，再设置采样。变化筛选只找画面变化，不判断工业异常；候选图片仍需人工审核。');explanation.setWordWrap(True);form.addRow(explanation)
        self.sampling=QComboBox();self.sampling.addItem('固定间隔','fixed');self.sampling.addItem('变化筛选（非AI）','smart');self.sampling.addItem('AI辅助 · Not Available（P5）','ai')
        self.interval=QDoubleSpinBox();self.interval.setRange(.001,3600);self.interval.setDecimals(3);self.interval.setValue(1);self.interval.setSuffix(' 秒/帧')
        self.maximum=QSpinBox();self.maximum.setRange(1,5000);self.maximum.setValue(50);self.maximum.setSuffix(' 张')
        self.format=QComboBox();self.format.addItems(['PNG','JPEG']);self.quality=QSpinBox();self.quality.setRange(1,100);self.quality.setValue(90)
        self.max_width=QSpinBox();self.max_width.setRange(0,8192);self.max_width.setSpecialValueText('原始分辨率（0）')
        self.sensitivity=QDoubleSpinBox();self.sensitivity.setRange(.1,100);self.sensitivity.setValue(12);self.sensitivity.setSuffix(' %')
        self.baseline=QCheckBox('保留固定间隔基础样本');self.baseline.setChecked(True)
        fields=[('抽帧方式',self.sampling,'固定间隔按时间均匀采样；变化筛选按画面变化选候选。'),('固定间隔 / 频率',self.interval,'1.000秒/帧表示每1秒最多取一帧；0.200表示约每秒5帧。'),('张数上限',self.maximum,'本次任务最多生成多少张候选图片，达到上限即停止。'),('输出格式',self.format,'PNG无损，JPEG压缩后体积通常较小。'),('JPEG质量',self.quality,'仅JPEG生效，越高越清晰，文件通常越大。'),('输出最大宽度',self.max_width,'0保留视频显示分辨率；填较小宽度等比例缩小，不放大。'),('变化阈值',self.sensitivity,'越小越敏感，但变化筛选不等于工业异常判断。'),('基础均匀样本',self.baseline,'变化筛选时仍保留按固定间隔抽取的样本，避免只留下变化画面。')]
        self.parameter_help=[]
        for text,w,help_text in fields:
            w.setToolTip(help_text);label=QLabel(text);label.setToolTip(help_text);form.addRow(label,w)
            help_label=QLabel(help_text);help_label.setWordWrap(True);help_label.setStyleSheet('color:#586d82;font-size:12px;');form.addRow(help_label);self.parameter_help.append(help_label)
        self.extract_button=button('确认范围并后台抽帧',self.extract,True,'extract_frames');self.extract_button.setToolTip('确认上方范围及当前设置后启动后台任务，界面可继续使用。');form.addRow(self.extract_button)
        self.cancel_button=button('取消当前录像抽帧',self.cancel_requested.emit,name='cancel_media_job');self.cancel_button.setToolTip('只取消当前选中录像的抽帧任务，已完整保存的图片保留。');self.cancel_button.setEnabled(False);form.addRow(self.cancel_button)
        self.format.currentTextChanged.connect(lambda:self.quality.setEnabled(self.format.currentText()=='JPEG'));self.quality.setEnabled(False)
        self.tabs.addTab(extraction,'抽帧设置与时间范围')
        clips=QWidget();clips.setObjectName('media_tags');clips.setStyleSheet('QWidget#media_tags { background:#f2f5fa; }');cl=QFormLayout(clips);hint=QLabel('这里仅保存时间范围的标签；如需实际视频文件，请使用“保存视频片段”。');hint.setWordWrap(True);cl.addRow(hint)
        self.clip_tag=QComboBox()
        for text,value in [('正常','NORMAL'),('异常','ABNORMAL'),('未知/待确认','UNKNOWN')]:self.clip_tag.addItem(text,value)
        self.clip_label=QComboBox();self.clip_label.addItem('无故障类别',None);self.clip_status=QComboBox();self.clip_status.addItems(['DRAFT','REVIEWED','APPROVED','REJECTED'])
        cl.addRow('片段标签',self.clip_tag);cl.addRow('故障类别',self.clip_label);cl.addRow('审核状态',self.clip_status)
        for b in [button('保存/更新片段标签',self.save_clip,name='save_clip'),button('新片段标签',self.new_clip),button('删除选中片段标签',self.delete_clip),button('故障类型…',self.labels_requested.emit)]:cl.addRow(b)
        self.clips=table(['开始秒','结束秒','标签','故障UUID','审核','版本']);self.clips.setMinimumHeight(160);self.clips.itemSelectionChanged.connect(self.select_clip);cl.addRow(self.clips);self.tabs.addTab(clips,'视频片段标签')
        save=QWidget();save.setObjectName('media_clip_save');save.setStyleSheet('QWidget#media_clip_save { background:#f2f5fa; }');sf=QFormLayout(save);notice=QLabel('按上方起止时间保存独立MP4，原录像保留。后台重新编码，按实际帧边界截取；只保留视频画面，不含音频。最少100毫秒且至少两帧。');notice.setWordWrap(True);sf.addRow(notice)
        self.clip_name=QLineEdit();self.clip_name.setPlaceholderText('可选：默认原录像名 + 起止秒数');self.clip_note=QLineEdit();self.clip_note.setPlaceholderText('可选：故障说明或备注')
        sf.addRow('片段名称',self.clip_name);sf.addRow('备注',self.clip_note);self.save_video_button=button('保存视频片段',self.save_video_clip,True,'save_video_clip');sf.addRow(self.save_video_button)
        self.cancel_clip_button=button('取消当前片段保存',lambda:self.cancel_clip_requested.emit(),name='cancel_clip_save');self.cancel_clip_button.setEnabled(False);sf.addRow(self.cancel_clip_button)
        self.tabs.addTab(save,'保存视频片段');rr.addWidget(self.tabs,1)
        self.info=QLabel('请先打开项目并导入录像。');self.info.setWordWrap(True);rr.addWidget(self.info)
        self.splitter.setSizes([420,640]);self.splitter.setChildrenCollapsible(False);self.update_range()
    cancel_clip_requested=Signal()
    def update_range(self):self.range_info.setText(f'当前范围：{self.start.value():.3f} → {self.end.value():.3f} 秒，长度 {self.end.value()-self.start.value():.3f} 秒')
    def save_video_clip(self):
        if not self.media_id:self.info.setText('请先选择原始录像。');return
        if not self.selected_media or self.selected_media.get('kind')=='CLIP':self.info.setText('请选择原始录像，本轮不支持片段再裁片段。');return
        start=round(self.start.value()*1e6);end=round(self.end.value()*1e6)
        if not 0<=start<end<=self.selected_media['video']['duration_us']:self.info.setText('终点必须晚于起点且不超出录像时长。');return
        if end-start<100000:self.info.setText('片段至少100毫秒，请扩大范围。');return
        self.clip_file_requested.emit({'media_id':self.media_id,'start_us':start,'end_us':end,'name':self.clip_name.text(),'note':self.clip_note.text()})
    def choose_import(self):
        files,_=QFileDialog.getOpenFileNames(self,'批量选择监控录像','','录像 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)')
        if files:self.import_requested.emit({'paths':files,'mode':self.mode.currentData(),'camera':self.camera.text().strip(),'site':self.site.text().strip(),'equipment':self.equipment.text().strip()})
    def select_media(self):
        row=self.table.currentRow()
        if 0<=row<len(self.media_rows):self.media_id=self.media_rows[row]['id'];self.load_requested.emit(self.media_id)
    def load_media(self,row):
        self.media_id=row['id'];self.selected_media=row;meta=row['video']
        self.start.setMaximum(meta['duration_us']/1000000);self.end.setMaximum(meta['duration_us']/1000000)
        self.start.setValue(0);self.end.setValue(meta['duration_us']/1000000);self.player.load(row['accessible_path'],meta)
        self.info.setText(f"{row['name']} · {meta['codec']} · 标称帧率{meta['nominal_fps']} · PTS时间基{meta['time_base']} · 旋转{meta['rotation']}° · 真实拍摄时间未知")
        self.new_clip()
    def extract(self):
        if not self.media_id:self.info.setText('请选择已完整导入的录像。');return
        if self.sampling.currentData()=='ai':self.info.setText('AI辅助抽帧Not Available；P5实现，不使用CPU伪装AI推理。');return
        if QMessageBox.question(self,'确认有限抽帧',f'已预览范围后，将生成最多{self.maximum.value()}张候选图片。是否开始？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.extract_requested.emit({'media_id':self.media_id,'options':{'mode':self.sampling.currentData(),'start_us':round(self.start.value()*1000000),'end_us':round(self.end.value()*1000000),'interval_us':round(self.interval.value()*1000000),'maximum':self.maximum.value(),'format':self.format.currentText(),'quality':self.quality.value(),'max_width':self.max_width.value(),'sensitivity':self.sensitivity.value(),'baseline':self.baseline.isChecked()}})
    def relocate(self):
        if not self.media_id:self.info.setText('请先选择缺失的引用录像。');return
        path,_=QFileDialog.getOpenFileName(self,'重新定位原录像')
        if path:self.relocate_requested.emit(self.media_id,path)
    def new_clip(self):self.selected_clip=None;self.clips.clearSelection()
    def select_clip(self):
        index=self.clips.currentRow()
        if 0<=index<len(self.clip_rows):
            row=self.clip_rows[index];self.selected_clip=row;self.start.setValue(row['start_us']/1000000);self.end.setValue(row['end_us']/1000000)
            self.clip_tag.setCurrentIndex(max(0,self.clip_tag.findData(row['tag'])));self.clip_label.setCurrentIndex(max(0,self.clip_label.findData(row['label_id'])));self.clip_status.setCurrentText(row['status'])
    def save_clip(self):
        if not self.media_id:self.info.setText('请先选择录像。');return
        value={'media_id':self.media_id,'start_us':round(self.start.value()*1000000),'end_us':round(self.end.value()*1000000),'tag':self.clip_tag.currentData(),'label_id':self.clip_label.currentData(),'status':self.clip_status.currentText()}
        if self.selected_clip:value.update(id=self.selected_clip['id'],revision=self.selected_clip['revision'])
        self.clip_requested.emit(value)
    def delete_clip(self):
        if self.selected_clip:self.clip_delete_requested.emit(self.selected_clip['id'],self.selected_clip['revision'])
        else:self.info.setText('请选择片段标签。')
