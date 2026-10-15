import json
from PySide6.QtCore import Qt,Signal
from PySide6.QtWidgets import (QHBoxLayout,QVBoxLayout,QWidget,QLineEdit,QComboBox,QSpinBox,QCheckBox,QLabel,QFileDialog,QMessageBox,QTableWidgetItem,QPlainTextEdit,QTabWidget,QGridLayout,QHeaderView,QScrollArea)
from ivad_app.gui.pages import Page,button,table

class DatasetPage(Page):
    preview_requested=Signal(list)
    version_check_requested=Signal(str)
    split_requested=Signal(dict)
    batch_requested=Signal(str,list)
    freeze_requested=Signal(dict)
    export_requested=Signal(dict)
    def __init__(self):
        super().__init__('数据集管理','已保存人工真值通过自动校验后可创建实验数据集；自动检查不等于独立人工审核或生产批准。')
        self.all_rows=[];self.candidate_rows=[];self.version_rows=[];self.omitted={};self.root=None;self.updating=False
        filters=QGridLayout();self.layout.addLayout(filters)
        self.camera=QComboBox();self.fault=QComboBox();self.tag=QComboBox();self.source=QComboBox();self.completion=QComboBox();self.exclusion=QComboBox()
        for text,value in [('正常/异常/未知：全部',None),('正常','NORMAL'),('异常','ABNORMAL'),('未知','UNKNOWN')]:self.tag.addItem(text,value)
        for text,value in [('标注完成：全部',None),('已标注','LABELED'),('未标注','UNLABELED')]:self.completion.addItem(text,value)
        for text,value in [('仅有效图片','active'),('仅已剔除图片','excluded'),('全部图片','all')]:self.exclusion.addItem(text,value)
        for i,(text,widget) in enumerate([('所属摄像头',self.camera),('故障类型',self.fault),('处理结果',self.tag),('来源视频/片段',self.source),('标注完成',self.completion),('剔除状态',self.exclusion)]):
            filters.addWidget(QLabel(text),i//3*2,i%3);filters.addWidget(widget,i//3*2+1,i%3);widget.currentIndexChanged.connect(self.filter_rows)
        self.tabs=QTabWidget();self.tabs.setObjectName('dataset_tabs');self.tabs.setStyleSheet('QTabBar::tab { background:#176a94; color:white; padding:8px 9px; border:1px solid #b9d4e3; } QTabBar::tab:hover, QTabBar::tab:selected { background:white; color:#111111; } QTabWidget::pane { border:1px solid #b9d4e3; background:#f2f5fa; }');self.layout.addWidget(self.tabs,1)
        layouts=[]
        for text in ['图片列表与筛查','新建数据集','训练集划分设置','数据集版本']:
            body=QWidget();body.setObjectName('dataset_tab_body');body.setStyleSheet('QWidget#dataset_tab_body { background:#f2f5fa; }');layout=QVBoxLayout(body);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(body);self.tabs.addTab(scroll,text);layouts.append(layout)
        screening,creation,splitting,versions=layouts
        self.candidates=table(['选择','摄像头','抽帧时间（秒）','来源视频','处理结果','故障类型','标注数量']);self.candidates.setObjectName('dataset_candidates');self.candidates.setMinimumHeight(220);self.candidates.setSortingEnabled(True);self.candidates.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive);self.candidates.horizontalHeader().setStretchLastSection(True)
        for i,width in enumerate([55,150,130,240,100,220,90]):self.candidates.setColumnWidth(i,width)
        self.candidates.itemChanged.connect(self.update_counts);screening.addWidget(self.candidates,1)
        row=QHBoxLayout();screening.addLayout(row)
        for text,fn,name in [('全选当前筛选结果',self.select_all,'dataset_select_all'),('取消选择',self.clear_selection,'dataset_clear_selection'),('从候选列表排除',self.omit_selected,'dataset_omit'),('恢复候选排除',self.restore_omitted,'dataset_restore_omitted')]:row.addWidget(button(text,fn,name=name))
        row=QHBoxLayout();screening.addLayout(row)
        row.addWidget(button('标记所选为无效帧',lambda:self.batch_requested.emit('exclude',self.selected_frames()),name='dataset_exclude'))
        row.addWidget(button('恢复已剔除图片',lambda:self.batch_requested.emit('restore',self.selected_frames()),name='dataset_restore'))
        self.batch_info=QLabel('候选排除仅改变当前数据集会话草稿；标记无效帧会改变全局剔除状态。均不删除文件。');self.batch_info.setWordWrap(True);screening.addWidget(self.batch_info)
        row=QHBoxLayout();self.name=QLineEdit();self.name.setObjectName('dataset_name');self.name.setPlaceholderText('例如 8525_压滤板破裂_Detection_v1，由操作员确认')
        self.existing=QComboBox();self.existing.addItem('创建新数据集',None);self.existing.currentIndexChanged.connect(self.choose_existing)
        row.addWidget(self.name,2);row.addWidget(self.existing,1);creation.addLayout(row)
        self.counts=QLabel();self.counts.setWordWrap(True);creation.addWidget(self.counts)
        self.allow_multi=QCheckBox('明确允许多个摄像头/未关联来源建立共享实验数据集');creation.addWidget(self.allow_multi)
        self.draft_info=QLabel('先在图片列表勾选，然后添加到当前数据集草稿。切换筛选会清空勾选，已添加成员独立保留。');self.draft_info.setWordWrap(True);creation.addWidget(self.draft_info)
        row=QHBoxLayout();creation.addLayout(row);row.addWidget(button('添加所选图片',self.add_selected,True,'dataset_add_selected'));row.addWidget(button('移除草稿中所选图片',self.remove_selected));row.addWidget(button('清空当前草稿',self.clear_draft))
        creation.addWidget(button('检查候选数据',lambda:self.preview_requested.emit(self.draft_frames()),name='check_dataset'))
        self.draft_detail=QPlainTextEdit();self.draft_detail.setReadOnly(True);self.draft_detail.setMinimumHeight(140);creation.addWidget(self.draft_detail,1);self.drafts={}
        self.strategy=QComboBox()
        for text,value in [('按来源视频分组（推荐，片段追溯原视频）','source'),('按摄像头分组','camera'),('随机图片划分（泄漏风险）','random')]:self.strategy.addItem(text,value)
        self.strategy.setToolTip('原视频及派生片段保持同组；摄像头分组适合未见摄像头评估。未来日期/工况/时段分组尚未实现。');splitting.addWidget(self.strategy)
        grid=QGridLayout();splitting.addLayout(grid);self.ratios=[]
        for i,(name,value,help_text) in enumerate([('Train（训练集）',70,'用于模型参数学习。'),('Val（验证集）',20,'用于训练过程中的模型验证、调参与选择。'),('Test（测试集）',10,'用于训练结束后的独立性能评估，不应反复用于调参。')]):
            spin=QSpinBox();spin.setRange(0,100);spin.setValue(value);spin.setSuffix('%');spin.setToolTip(help_text);spin.setMinimumHeight(spin.sizeHint().height());self.ratios.append(spin);grid.addWidget(QLabel(name),i,0);grid.addWidget(spin,i,1)
        self.seed=QSpinBox();self.seed.setRange(0,2147483647);self.seed.setValue(123);self.seed.setToolTip('控制随机划分的重复性。相同数据、划分方法及种子通常得到相同结果。不是训练次数，也不是图片数量。');grid.addWidget(QLabel('随机种子（Seed）'),3,0);grid.addWidget(self.seed,3,1)
        self.allow_random=QCheckBox('我理解随机图片划分的相邻帧泄漏风险');splitting.addWidget(self.allow_random)
        self.allow_limited=QCheckBox('允许LIMITED隔离实验：仅工程管线测试，不可用于工业泛化结论');splitting.addWidget(self.allow_limited)
        risk=QLabel('比例合计须为100%。原视频组/摄像头不足或跨集合高相似样本将提示LIMITED；未知、冲突、缺失、剔除样本为BLOCKED。随机图片划分不代表独立工业验证。');risk.setWordWrap(True);splitting.addWidget(risk)
        splitting.addWidget(button('预览划分与数据泄漏检查',lambda:self.split_requested.emit(self.payload()),True,'dataset_split_preview'))
        self.split_detail=QPlainTextEdit();self.split_detail.setReadOnly(True);self.split_detail.setMinimumHeight(160);splitting.addWidget(self.split_detail,1)
        row=QHBoxLayout();versions.addLayout(row);row.addWidget(button('检查候选数据',lambda:self.preview_requested.emit(self.draft_frames())));row.addWidget(button('冻结新版本',self.freeze,True,'freeze_dataset'));row.addWidget(button('检查选中版本完整性 / 来源',self.check_version,name='dataset_check_version'))
        self.versions=table(['数据集','版本','图片数','目标数','划分','版本UUID']);self.versions.setObjectName('dataset_versions');self.versions.setMinimumHeight(200);self.versions.itemSelectionChanged.connect(self.show_version);versions.addWidget(self.versions,1)
        row=QHBoxLayout();self.format=QComboBox()
        for text,value in [('YOLO Detection','yolo_detect'),('YOLO Segmentation','yolo_segment'),('COCO JSON','coco'),('IVAD Native（完整）','ivad_native')]:self.format.addItem(text,value)
        row.addWidget(self.format);row.addWidget(button('导出选中冻结版本…',self.export,True,'export_dataset'));versions.addLayout(row)
        self.detail=QPlainTextEdit();self.detail.setReadOnly(True);self.detail.setMaximumHeight(160);versions.addWidget(self.detail)
        self.summary=QLabel('请打开项目，选择摄像头并检查已保存人工标注。');self.summary.setWordWrap(True);self.layout.addWidget(self.summary)
    def key(self):return self.existing.currentData() or '__new__'
    def draft_frames(self):return list(self.drafts.get(self.key(),[]))
    def set_project(self,root):
        if root!=self.root:self.root=root;self.all_rows=[];self.candidate_rows=[];self.drafts={};self.omitted={};self.camera.clear();self.filter_rows()
    def set_data(self,rows,cameras,labels,versions,preferred_camera=None):
        self.updating=True;self.all_rows=rows
        for combo,items,default in [(self.camera,[('全部摄像头','__all__')]+[(c['name'],c['id']) for c in cameras]+[('未关联摄像头','__unlinked__')],preferred_camera or next((c['id'] for c in cameras if any(r['camera_id']==c['id'] and r['eligible'] for r in rows)),cameras[0]['id'] if cameras else '__unlinked__')),(self.fault,[('全部故障类型',None)]+[(l['name'],l['id']) for l in labels],None),(self.source,[('全部来源',None)]+list(dict.fromkeys((r['media_name'],r['media_id']) for r in rows)),None)]:
            old=combo.currentData() if combo.count() else default;combo.clear()
            for text,value in items:combo.addItem(text,value)
            combo.setCurrentIndex(max(0,combo.findData(old)))
        old=self.existing.currentData();self.existing.clear();self.existing.addItem('创建新数据集',None);seen=set()
        for v in versions:
            if v['dataset_id'] not in seen:self.existing.addItem(v['name'],v['dataset_id']);seen.add(v['dataset_id'])
        self.existing.setCurrentIndex(max(0,self.existing.findData(old)));self.version_rows=versions;self.versions.setRowCount(len(versions))
        for i,v in enumerate(versions):
            for j,value in enumerate([v['name'],v['number'],v['summary']['images'],v['summary']['objects'],str(v['summary']['splits']),v['id']]):self.versions.setItem(i,j,QTableWidgetItem(str(value)))
        self.updating=False;self.filter_rows()
    def filter_rows(self):
        if self.updating:return
        cam=self.camera.currentData();fault=self.fault.currentData();tag=self.tag.currentData();source=self.source.currentData();completion=self.completion.currentData();mode=self.exclusion.currentData();hidden=self.omitted.get(self.key(),set())
        rows=[r for r in self.all_rows if (cam=='__all__' or r['camera_id']==cam or (cam=='__unlinked__' and not r['camera_id'])) and (not fault or fault in r['fault_ids']) and (not tag or r['image_tag']==tag) and (not source or r['media_id']==source) and (not completion or r['completion_state']==completion) and (mode=='all' or (r['excluded'] if mode=='excluded' else not r['excluded'])) and r['id'] not in hidden]
        self.candidates.setSortingEnabled(False);self.candidates.blockSignals(True);self.candidates.setRowCount(len(rows));self.candidate_rows=rows
        for i,r in enumerate(rows):
            values=['',r['camera_name'],r['pts_us']/1000000,r['media_name'],{'NORMAL':'正常','ABNORMAL':'异常','UNKNOWN':'未知'}.get(r['image_tag'],'冲突'),r['fault_text'],r['objects']]
            for j,value in enumerate(values):
                item=QTableWidgetItem();item.setData(Qt.ItemDataRole.DisplayRole,value);item.setData(Qt.ItemDataRole.UserRole,r['id']);item.setToolTip(f"UUID：{r['id']}\nSHA256：{r['sha256']}\n项目内路径：{r['path']}\n来源：{r['media_name']} / {r['media_id']}\n源路径：{r['source_path']}\n摄像头UUID：{r['camera_id']}\n原视频UUID：{r['source_group_id']}\n审核：{r['review_status']}；完成：{r['completion_state']}\n自动检查：{r['issue'] or '通过（非独立审核）'}")
                if j==0:item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Unchecked)
                self.candidates.setItem(i,j,item)
        self.candidates.blockSignals(False);self.candidates.setSortingEnabled(True);self.update_counts()
    def selected_frames(self):return [self.candidates.item(i,0).data(Qt.ItemDataRole.UserRole) for i in range(self.candidates.rowCount()) if self.candidates.item(i,0).checkState()==Qt.CheckState.Checked]
    def select_all(self):
        for i in range(self.candidates.rowCount()):self.candidates.item(i,0).setCheckState(Qt.CheckState.Checked)
    def clear_selection(self):
        for i in range(self.candidates.rowCount()):self.candidates.item(i,0).setCheckState(Qt.CheckState.Unchecked)
    def update_counts(self,*_):
        rows=self.candidate_rows;selected=set(self.selected_frames());draft=set(self.draft_frames());all_by={r['id']:r for r in self.all_rows}
        self.counts.setText(f"当前筛选{len(rows)}张；可训练候选{sum(r['eligible'] for r in rows)}；已勾选{len(selected)}；正常{sum(r['image_tag']=='NORMAL' for r in rows)}；异常{sum(r['image_tag']=='ABNORMAL' for r in rows)}；无效/冲突{sum(not r['eligible'] for r in rows)}；草稿{len(draft)}张")
        self.draft_detail.setPlainText('\n'.join(f"{all_by[f]['camera_name']} · {all_by[f]['media_name']} · {all_by[f]['pts_us']/1e6:.3f}s · {all_by[f]['fault_text']}" if f in all_by else f+'（来源不可用）' for f in self.draft_frames()))
    def add_selected(self):
        ids=self.selected_frames();by={r['id']:r for r in self.all_rows};valid=[f for f in ids if by[f]['eligible']];cams={by[f]['camera_id'] for f in self.draft_frames()+valid if f in by}
        if len(cams)>1 and not self.allow_multi.isChecked():self.summary.setText('BLOCKED：多个摄像头/未关联来源，请明确勾选共享实验数据集。');return
        new=[f for f in valid if f not in self.draft_frames()];self.drafts[self.key()]=self.draft_frames()+new;self.summary.setText(f'添加：成功{len(new)}，跳过{len(ids)-len(new)}，失败0。无效/重复样本不能重复加入。');self.update_counts()
    def remove_selected(self):
        ids=set(self.selected_frames());before=self.draft_frames();self.drafts[self.key()]=[f for f in before if f not in ids];self.summary.setText(f'草稿移除：成功{len(ids & set(before))}，跳过{len(ids-set(before))}，失败0。');self.update_counts()
    def clear_draft(self):self.drafts[self.key()]=[];self.update_counts()
    def omit_selected(self):
        ids=set(self.selected_frames());self.omitted.setdefault(self.key(),set()).update(ids);self.drafts[self.key()]=[f for f in self.draft_frames() if f not in ids];self.batch_info.setText(f'仅本草稿候选排除：成功{len(ids)}，跳过0，失败0；全局状态/原文件不变。');self.filter_rows()
    def restore_omitted(self):
        count=len(self.omitted.get(self.key(),set()));self.omitted[self.key()]=set();self.batch_info.setText(f'恢复候选：成功{count}，跳过0，失败0。');self.filter_rows()
    def choose_existing(self):
        if self.updating:return
        if self.existing.currentData():self.name.setText(self.existing.currentText())
        self.filter_rows()
    def payload(self):return {'name':self.name.text(),'dataset_id':self.existing.currentData(),'frame_ids':self.draft_frames(),'strategy':self.strategy.currentData(),'allow_leakage':self.allow_random.isChecked(),'allow_limited':self.allow_limited.isChecked(),'allow_multi_camera':self.allow_multi.isChecked(),'ratios':[s.value() for s in self.ratios],'seed':self.seed.value(),'admission':'experimental'}
    def freeze(self):
        if not self.draft_frames():self.summary.setText('请在图片列表勾选并添加到数据集草稿。');return
        if QMessageBox.question(self,'确认冻结不可变实验版本','将严格检查并复制当前草稿。保留历史审核原值，不冒充独立审核。历史版本不会覆盖。确认冻结？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.freeze_requested.emit(self.payload())
    def check_version(self):
        row=self.versions.currentRow()
        if not 0<=row<len(self.version_rows):self.summary.setText('请先选择冻结版本。');return
        self.version_check_requested.emit(self.version_rows[row]['id'])
    def show_version(self):
        row=self.versions.currentRow()
        if 0<=row<len(self.version_rows):self.detail.setPlainText(json.dumps(self.version_rows[row]['summary'],ensure_ascii=False,indent=2))
    def export(self):
        row=self.versions.currentRow()
        if not 0<=row<len(self.version_rows):self.summary.setText('请先选择冻结版本。');return
        path=QFileDialog.getExistingDirectory(self,'选择导出父目录（新建独立目录，不覆盖）')
        if path:self.export_requested.emit({'version_id':self.version_rows[row]['id'],'format':self.format.currentData(),'parent':path})
