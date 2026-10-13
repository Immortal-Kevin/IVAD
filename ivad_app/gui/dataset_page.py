import json
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QWidget,QScrollArea,QLineEdit,QComboBox,QSpinBox,QCheckBox,QLabel,QFileDialog,QMessageBox,QTableWidgetItem,QPlainTextEdit
from ivad_app.gui.pages import Page,button,table

class DatasetPage(Page):
    preview_requested=Signal(list)
    freeze_requested=Signal(dict)
    export_requested=Signal(dict)
    def __init__(self):
        super().__init__('数据集管理','只从人工已审核标注冻结版本。按来源视频/摄像头分组，精确重复哈希去重；近重复仅警告。')
        outer=self.layout;body=QWidget();body.setObjectName('dataset_body');body.setStyleSheet('QWidget#dataset_body { background:#f2f5fa; }');body.setMinimumHeight(820)
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body);outer.addWidget(scroll,1);self.layout=QVBoxLayout(body);self.layout.setContentsMargins(0,0,5,0)
        self.candidate_rows=[];self.version_rows=[]
        row=QHBoxLayout();self.name=QLineEdit();self.name.setObjectName('dataset_name');self.name.setPlaceholderText('新数据集名称，或选择已有数据集创建新版本')
        self.existing=QComboBox();self.existing.addItem('新数据集',None);self.existing.currentIndexChanged.connect(self.choose_existing)
        row.addWidget(self.name,2);row.addWidget(self.existing,1);self.layout.addLayout(row)
        row=QHBoxLayout();self.strategy=QComboBox();self.strategy.addItem('按摄像头/来源视频分组（推荐）','grouped');self.strategy.addItem('随机图片划分（泄漏风险）','random')
        self.allow_random=QCheckBox('我理解随机划分泄漏风险');self.ratios=[]
        row.addWidget(self.strategy,2)
        for name,value in [('Train ',70),('Val ',20),('Test ',10)]:
            spin=QSpinBox();spin.setRange(0,100);spin.setValue(value);spin.setPrefix(name);spin.setSuffix('%');self.ratios.append(spin);row.addWidget(spin)
        self.layout.addLayout(row);row=QHBoxLayout();row.addWidget(self.allow_random);self.seed=QSpinBox();self.seed.setRange(0,2147483647);self.seed.setValue(123);self.seed.setPrefix('随机种子 ');row.addWidget(self.seed)
        row.addWidget(button('全选已审核图片',self.select_all));row.addWidget(button('检查选择',lambda:self.preview_requested.emit(self.selected_frames()),name='check_dataset'));row.addWidget(button('冻结新版本',self.freeze,True,'freeze_dataset'));self.layout.addLayout(row)
        self.candidates=table(['选择','图片UUID','来源','时间秒','目标/类型','审核/整帧标签']);self.candidates.setObjectName('dataset_candidates');self.candidates.setMinimumHeight(170);self.layout.addWidget(self.candidates,1)
        self.summary=QLabel('请先完成人工标注审核，再选择图片。');self.summary.setWordWrap(True);self.layout.addWidget(self.summary)
        self.versions=table(['数据集','版本','图片数','目标数','划分','版本UUID']);self.versions.setObjectName('dataset_versions');self.versions.setMinimumHeight(170);self.versions.itemSelectionChanged.connect(self.show_version);self.layout.addWidget(self.versions,1)
        row=QHBoxLayout();self.format=QComboBox()
        for text,value in [('YOLO Detection','yolo_detect'),('YOLO Segmentation','yolo_segment'),('COCO JSON','coco'),('IVAD Native（完整）','ivad_native')]:self.format.addItem(text,value)
        row.addWidget(self.format);row.addWidget(button('导出选中冻结版本…',self.export,True,'export_dataset'));self.layout.addLayout(row)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumHeight(110);self.layout.addWidget(self.detail)
    def selected_frames(self):return [row['id'] for i,row in enumerate(self.candidate_rows) if self.candidates.item(i,0) and self.candidates.item(i,0).checkState()==Qt.CheckState.Checked]
    def select_all(self):
        for row in range(self.candidates.rowCount()):self.candidates.item(row,0).setCheckState(Qt.CheckState.Checked)
    def choose_existing(self):
        if self.existing.currentData():self.name.setText(self.existing.currentText())
    def freeze(self):
        ids=self.selected_frames()
        if not ids:self.summary.setText('请先选择已审核图片。');return
        if QMessageBox.question(self,'确认冻结不可变版本','将复制并校验已选图片及标注快照。当前及历史版本不会被覆盖。确认冻结？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.freeze_requested.emit({'name':self.name.text(),'dataset_id':self.existing.currentData(),'frame_ids':ids,'strategy':self.strategy.currentData(),'allow_leakage':self.allow_random.isChecked(),'ratios':[s.value() for s in self.ratios],'seed':self.seed.value()})
    def show_version(self):
        row=self.versions.currentRow()
        if 0<=row<len(self.version_rows):self.detail.setPlainText(json.dumps(self.version_rows[row]['summary'],ensure_ascii=False,indent=2))
    def export(self):
        row=self.versions.currentRow()
        if not 0<=row<len(self.version_rows):self.summary.setText('请先选择冻结版本。');return
        path=QFileDialog.getExistingDirectory(self,'选择导出父目录（会新建独立目录，不覆盖）')
        if path:self.export_requested.emit({'version_id':self.version_rows[row]['id'],'format':self.format.currentData(),'parent':path})
