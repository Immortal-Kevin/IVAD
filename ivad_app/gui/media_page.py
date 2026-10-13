from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QHBoxLayout,QVBoxLayout,QComboBox,QLabel,QLineEdit,QDoubleSpinBox,QSpinBox,QCheckBox,
    QFileDialog,QSplitter,QWidget,QMessageBox,QTabWidget)
from ivad_app.gui.pages import Page,button,table
from ivad_app.gui.video_player import VideoPlayer

class MediaPage(Page):
    import_requested=Signal(dict)
    extract_requested=Signal(dict)
    capture_requested=Signal(str,int)
    load_requested=Signal(str)
    relocate_requested=Signal(str,str)
    clip_requested=Signal(dict)
    clip_delete_requested=Signal(str,int)
    check_requested=Signal()
    cancel_requested=Signal()
    labels_requested=Signal()
    def __init__(self):
        super().__init__('视频管理与抽帧','本地录像 · Copy默认 · 实际PTS定位；变化筛选不等于工业异常。')
        self.media_id=None;self.media_rows=[];self.clip_rows=[];self.selected_clip=None
        top=QHBoxLayout();self.mode=QComboBox();self.mode.addItem('复制到项目（默认）','COPY');self.mode.addItem('外部引用','REFERENCE')
        top.addWidget(self.mode);top.addWidget(button('批量导入录像…',self.choose_import,True,'import_media'))
        top.addWidget(button('重新定位引用…',self.relocate));top.addWidget(button('一致性检查',self.check_requested.emit));top.addWidget(button('故障类型…',self.labels_requested.emit));self.layout.addLayout(top)
        meta=QHBoxLayout();self.camera=QLineEdit();self.camera.setPlaceholderText('摄像头编号（可选）');self.site=QLineEdit();self.site.setPlaceholderText('厂区（可选）');self.equipment=QLineEdit();self.equipment.setPlaceholderText('设备（可选）')
        for widget in [self.camera,self.site,self.equipment]:meta.addWidget(widget)
        self.layout.addLayout(meta)
        self.table=table(['录像','方式','状态','时长','编码','分辨率']);self.table.setObjectName('media_table');self.table.setMaximumHeight(160);self.table.itemSelectionChanged.connect(self.select_media);self.layout.addWidget(self.table)
        self.tabs=QTabWidget();self.player=VideoPlayer();self.tabs.addTab(self.player,'播放与定位');self.player.capture_requested.connect(lambda t:self.capture_requested.emit(self.media_id,t) if self.media_id else None);self.layout.addWidget(self.tabs,1)
        extraction=QWidget();form=QVBoxLayout(extraction)
        row=QHBoxLayout();self.start=QDoubleSpinBox();self.end=QDoubleSpinBox()
        for widget in [self.start,self.end]:widget.setDecimals(3);widget.setRange(0,10000000);widget.setSuffix(' 秒')
        self.start.setObjectName('sampling_start');self.end.setObjectName('sampling_end');row.addWidget(QLabel('范围'));row.addWidget(self.start);row.addWidget(button('当前为起点',lambda:self.start.setValue(self.player.position_us/1000000)));row.addWidget(self.end);row.addWidget(button('当前为终点',lambda:self.end.setValue(self.player.position_us/1000000)));form.addLayout(row)
        row=QHBoxLayout();self.sampling=QComboBox();self.sampling.addItem('固定间隔','fixed');self.sampling.addItem('变化筛选（非AI）','smart');self.sampling.addItem('AI辅助 · Not Available（P5）','ai')
        self.interval=QDoubleSpinBox();self.interval.setRange(.001,3600);self.interval.setDecimals(3);self.interval.setValue(1);self.interval.setSuffix(' 秒/帧')
        self.maximum=QSpinBox();self.maximum.setRange(1,5000);self.maximum.setValue(50);self.maximum.setSuffix(' 张上限')
        for widget in [self.sampling,self.interval,self.maximum]:row.addWidget(widget)
        form.addLayout(row);row=QHBoxLayout();self.format=QComboBox();self.format.addItems(['PNG','JPEG']);self.quality=QSpinBox();self.quality.setRange(1,100);self.quality.setValue(90);self.quality.setPrefix('JPEG质量 ')
        self.max_width=QSpinBox();self.max_width.setRange(0,8192);self.max_width.setSpecialValueText('原始分辨率');self.max_width.setPrefix('最大宽度 ')
        for widget in [self.format,self.quality,self.max_width]:row.addWidget(widget)
        form.addLayout(row);row=QHBoxLayout();self.sensitivity=QDoubleSpinBox();self.sensitivity.setRange(.1,100);self.sensitivity.setValue(12);self.sensitivity.setSuffix('%变化阈值（越小越敏感）');self.baseline=QCheckBox('保留固定间隔基础样本');self.baseline.setChecked(True)
        row.addWidget(self.sensitivity);row.addWidget(self.baseline);form.addLayout(row);row=QHBoxLayout();self.extract_button=button('确认范围并后台抽帧',self.extract,True,'extract_frames');row.addWidget(self.extract_button);self.cancel_button=button('取消本项目任务',self.cancel_requested.emit,name='cancel_media_job');self.cancel_button.setEnabled(False);row.addWidget(self.cancel_button);form.addLayout(row)
        form.addWidget(QLabel('抽帧使用实际PTS；预览范围后确认，生成图片仍需人工审核。'))
        self.tabs.addTab(extraction,'抽帧设置与时间范围')
        clips=QWidget();clip_layout=QVBoxLayout(clips);clip_layout.addWidget(QLabel('使用抽帧设置页的起止范围保存独立片段标签，不转换为目标框。'))
        row=QHBoxLayout();self.clip_tag=QComboBox()
        for text,value in [('正常','NORMAL'),('异常','ABNORMAL'),('未知/待确认','UNKNOWN')]:self.clip_tag.addItem(text,value)
        self.clip_label=QComboBox();self.clip_label.addItem('无故障类别',None);self.clip_status=QComboBox();self.clip_status.addItems(['DRAFT','REVIEWED','APPROVED','REJECTED'])
        for widget in [self.clip_tag,self.clip_label,self.clip_status,button('保存/更新片段',self.save_clip,name='save_clip'),button('新片段',self.new_clip),button('删除选中片段',self.delete_clip)]:row.addWidget(widget)
        clip_layout.addLayout(row);self.clips=table(['开始秒','结束秒','标签','故障UUID','审核','版本']);self.clips.itemSelectionChanged.connect(self.select_clip);clip_layout.addWidget(self.clips);self.tabs.addTab(clips,'视频片段标签')
        self.info=QLabel('请先打开项目并导入录像。');self.info.setWordWrap(True);self.layout.addWidget(self.info)
    def choose_import(self):
        files,_=QFileDialog.getOpenFileNames(self,'批量选择监控录像','','录像 (*.mp4 *.avi *.mov *.mkv);;所有文件 (*)')
        if files:self.import_requested.emit({'paths':files,'mode':self.mode.currentData(),'camera':self.camera.text().strip(),'site':self.site.text().strip(),'equipment':self.equipment.text().strip()})
    def select_media(self):
        row=self.table.currentRow()
        if 0<=row<len(self.media_rows):self.media_id=self.media_rows[row]['id'];self.load_requested.emit(self.media_id)
    def load_media(self,row):
        self.media_id=row['id'];meta=row['video'];self.start.setValue(0);self.end.setValue(meta['duration_us']/1000000)
        self.start.setMaximum(meta['duration_us']/1000000);self.end.setMaximum(meta['duration_us']/1000000);self.player.load(row['accessible_path'],meta)
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
