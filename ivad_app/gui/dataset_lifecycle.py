"""Incremental persisted-draft controls for the existing four dataset tabs."""
import copy,json
from uuid import uuid4
from PySide6.QtCore import Qt,Signal,QSize
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QWidget,QLabel,QComboBox,QListWidget,QListWidgetItem,QMessageBox,QTableWidgetItem,QGroupBox,QFormLayout,QStyle
from ivad_app.gui.pages import button,table

class DatasetLifecyclePage:
    def init_lifecycle(self,creation,splitting,versions):
        self.dataset_records={};self.active_dataset=None;self.draft_revision=0;self.draft_dirty=False;self.draft_saving=False;self.lifecycle_loading=False;self.active_validated=False;self.new_uuid=str(uuid4());self.project_identity=None
        self.project_scope=QLabel('所属项目：未打开');creation.insertWidget(1,self.project_scope)
        row=QHBoxLayout();self.target_camera=QComboBox();row.addWidget(QLabel('目标摄像头'));row.addWidget(self.target_camera,1);self.task=QComboBox();self.task.addItem('目标检测 Detection','detect');row.addWidget(self.task);creation.insertLayout(2,row)
        self.target_faults=QListWidget();self.target_faults.setMaximumHeight(90);self.target_faults.setToolTip('勾选目标故障类型。多类别目标必须全部明确勾选；正常帧不因此被标为故障。');creation.insertWidget(3,QLabel('目标故障类型（可多选）'));creation.insertWidget(4,self.target_faults)
        row=QHBoxLayout();self.save_draft_button=button('保存数据集草稿',lambda:self.save_requested.emit(None),True,'dataset_save_draft');row.addWidget(self.save_draft_button);self.saved_state=QLabel('尚未保存');self.saved_state.setWordWrap(True);row.addWidget(self.saved_state,1);creation.insertLayout(5,row)
        self.identity=QLabel();self.identity.setWordWrap(True);splitting.insertWidget(0,self.identity)
        self.preset=QComboBox()
        for text,value in [('标准训练（推荐）70 / 20 / 10','standard'),('小样本实验 80 / 20 / 0','small'),('自定义（高级）','custom')]:self.preset.addItem(text,value)
        self.preset.setToolTip('标准优先独立原视频组；小样本无最终Test评估；高级才修改分组/比例。');splitting.insertWidget(1,self.preset)
        self.strategy.hide()
        self.advanced_split=QWidget();self.advanced_split.setObjectName('dataset_advanced_split');self.advanced_split.setStyleSheet('QWidget#dataset_advanced_split {background:#f2f5fa;}');advanced=QFormLayout(self.advanced_split);advanced.setContentsMargins(0,0,0,0)
        # Move existing settings widgets into an optional advanced group; no duplicate inputs.
        old_grid=splitting.itemAt(3).layout()
        if old_grid:
            while old_grid.count():
                item=old_grid.takeAt(0)
                if item.widget() and item.widget() not in self.ratios+[self.seed]:item.widget().deleteLater()
            splitting.removeItem(old_grid)
        advanced.addRow('分组方法',self.strategy)
        for title,control in zip(['Train（训练集）','Val（验证集）','Test（测试集）','随机种子（Seed）'],self.ratios+[self.seed]):advanced.addRow(title,control)
        splitting.insertWidget(2,self.advanced_split);self.strategy.show()
        self.allow_random.setText('明确允许隔离工程图片划分（来源不足时使用，连续帧存在泄漏风险）')
        self.allow_random.hide();self.allow_limited.hide()
        self.validation_mode=QComboBox();self.validation_mode.addItem('工程实验（默认）','engineering');self.validation_mode.addItem('严格验证','strict');splitting.insertWidget(3,self.validation_mode)
        self.mode_help=QLabel('工程实验适合少量录像的训练测试；LIMITED 结果不代表工业识别准确率。严格验证要求独立来源及完整集合。');self.mode_help.setWordWrap(True);splitting.insertWidget(4,self.mode_help)
        self.split_save_state=QLabel('检查时先原子化保存全部待处理修改（包括图片成员），无需返回新建数据集。');self.split_save_state.setWordWrap(True);splitting.insertWidget(5,self.split_save_state)
        self.validation_mode.currentIndexChanged.connect(self.mark_draft_dirty)
        self.split_table=table(['集合','目标比例','实际图片','实际比例','正常','异常','目标数','原视频组','重复/泄漏']);self.split_table.setMinimumHeight(155);splitting.insertWidget(splitting.count()-1,self.split_table)
        self.split_button=self.findChild(type(self.save_draft_button),'dataset_split_preview');self.split_button.setText('自动划分并检查已保存草稿')
        self.version_identity=QLabel();self.version_identity.setWordWrap(True);versions.insertWidget(0,self.version_identity)
        self.empty_versions=QLabel('尚未创建数据集版本，请先完成草稿保存、数据检查和划分。');self.empty_versions.setWordWrap(True);versions.insertWidget(1,self.empty_versions)
        self.versions.setColumnCount(8);self.versions.setHorizontalHeaderLabels(['数据集','版本','冻结日期','图片数','目标数','Train/Val/Test','校验状态','版本UUID'])
        self.freeze_button=self.findChild(type(self.save_draft_button),'freeze_dataset');self.freeze_button.setText('检查并冻结新版本')
        self.preset.currentIndexChanged.connect(self.apply_preset)
        for control in [self.name,self.target_camera,self.allow_multi,self.allow_random,self.allow_limited,self.strategy,self.seed,*self.ratios]:
            signal=control.textChanged if control is self.name else control.toggled if hasattr(control,'toggled') else control.valueChanged if hasattr(control,'valueChanged') else control.currentIndexChanged
            signal.connect(self.mark_draft_dirty)
        self.target_faults.itemChanged.connect(self.mark_draft_dirty);self.camera.currentIndexChanged.connect(self.inherit_camera);self.fault.currentIndexChanged.connect(self.inherit_fault)
        self.apply_preset();self.draft_dirty=False

    def selected_fault_ids(self):return [self.target_faults.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.target_faults.count()) if self.target_faults.item(i).checkState()==Qt.CheckState.Checked]
    def configure_targets(self,cameras,labels):
        self.lifecycle_loading=True;old=self.target_camera.currentData() or self.camera.currentData();faults=self.selected_fault_ids()
        self.target_camera.clear()
        for c in cameras:self.target_camera.addItem(c['name'],c['id'])
        self.target_camera.addItem('未关联摄像头','__unlinked__');self.target_camera.setCurrentIndex(max(0,self.target_camera.findData(old)))
        self.target_faults.clear()
        for label in labels:
            item=QListWidgetItem(label['name']);item.setSizeHint(QSize(0,max(self.target_faults.fontMetrics().height()+8,self.target_faults.style().pixelMetric(QStyle.PixelMetric.PM_IndicatorHeight,None,self.target_faults)+8)));item.setData(Qt.ItemDataRole.UserRole,label['id']);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if label['id'] in faults else Qt.CheckState.Unchecked);self.target_faults.addItem(item)
        self.lifecycle_loading=False
    def inherit_camera(self,*_):
        if not self.active_dataset and not self.updating:
            cid=self.camera.currentData();idx=self.target_camera.findData(cid)
            if idx>=0:self.target_camera.setCurrentIndex(idx)
    def inherit_fault(self,*_):
        if not self.active_dataset and not self.updating and self.fault.currentData():
            for i in range(self.target_faults.count()):self.target_faults.item(i).setCheckState(Qt.CheckState.Checked if self.target_faults.item(i).data(Qt.ItemDataRole.UserRole)==self.fault.currentData() else Qt.CheckState.Unchecked)
    def infer_member_faults(self):
        if self.selected_fault_ids():return
        by={r['id']:r for r in self.all_rows};faults={f for fid in self.draft_frames() if fid in by for f in by[fid]['fault_ids']}
        for i in range(self.target_faults.count()):
            item=self.target_faults.item(i)
            if item.data(Qt.ItemDataRole.UserRole) in faults:item.setCheckState(Qt.CheckState.Checked)
    def mark_draft_dirty(self,*_):
        if self.lifecycle_loading or self.updating:return
        self.draft_dirty=True;self.active_validated=False;self.split_table.setRowCount(0);self.split_detail.setPlainText('草稿有未保存修改，先前划分检查已失效；请保存后重新检查。');self.saved_state.setText('未保存修改 · DRAFT；先前检查已失效');self.update_identity()
    def apply_preset(self,*_):
        loading=self.lifecycle_loading;self.lifecycle_loading=True;value=self.preset.currentData()
        if value in {'standard','small'}:
            for spin,ratio in zip(self.ratios,[70,20,10] if value=='standard' else [80,20,0]):spin.setValue(ratio)
            self.strategy.setCurrentIndex(self.strategy.findData('source'))
        self.advanced_split.setVisible(value=='custom');self.lifecycle_loading=loading
        if not loading:self.mark_draft_dirty()
    def settings_payload(self):return {k:self.payload()[k] for k in ['strategy','ratios','seed']}|{'preset':self.preset.currentData(),'validation_mode':self.validation_mode.currentData()}
    def draft_save_payload(self):
        self.infer_member_faults();by={r['id']:r for r in self.all_rows};cameras={self.target_camera.currentData() or '__unlinked__'}
        if self.allow_multi.isChecked():cameras.update(by[f]['camera_id'] or '__unlinked__' for f in self.draft_frames() if f in by)
        return {'dataset_id':self.active_dataset or self.new_uuid,'expected_revision':self.draft_revision,'project_id':self.project_identity['id'],'name':self.name.text(),'task':'detect','camera_ids':sorted(cameras),'fault_ids':self.selected_fault_ids(),'allow_multi_camera':self.allow_multi.isChecked(),'frame_ids':self.draft_frames(),'settings':self.settings_payload()}
    def set_lifecycle_data(self,records,project):
        self.project_identity={'id':project.id,'name':project.name} if project else None;self.project_scope.setText('所属项目：'+project.name+' / '+project.id if project else '请先打开项目')
        self.dataset_records={r['id']:r for r in records};selected=self.active_dataset;self.existing.blockSignals(True);self.existing.clear();self.existing.addItem('创建新数据集',None)
        for record in records:self.existing.addItem(record['name']+' · '+record['id'][:8],record['id'])
        self.existing.setCurrentIndex(max(0,self.existing.findData(selected)));self.existing.blockSignals(False)
        if selected and selected in self.dataset_records and not self.draft_dirty and not self.draft_saving:self.load_record(self.dataset_records[selected])
        self.render_versions();self.update_identity()
    def load_record(self,record):
        self.lifecycle_loading=True;self.active_dataset=record['id'];self.draft_revision=record['revision'];details=record['details'];draft=details.get('draft',{});self.drafts[record['id']]=[m['frame_id'] for m in draft.get('members',[])];self.name.setText(record['name']);settings=draft.get('settings',{})
        idx=self.target_camera.findData(next(iter(details.get('camera_ids',[])),self.camera.currentData()));self.target_camera.setCurrentIndex(max(0,idx))
        for i in range(self.target_faults.count()):
            item=self.target_faults.item(i);item.setCheckState(Qt.CheckState.Checked if item.data(Qt.ItemDataRole.UserRole) in details.get('fault_ids',[]) else Qt.CheckState.Unchecked)
        self.allow_multi.setChecked(details.get('allow_multi_camera',False));self.preset.setCurrentIndex(max(0,self.preset.findData(settings.get('preset','standard'))));self.apply_preset()
        self.strategy.setCurrentIndex(max(0,self.strategy.findData(settings.get('strategy','source'))))
        self.validation_mode.setCurrentIndex(max(0,self.validation_mode.findData(settings.get('validation_mode','engineering'))))
        for spin,value in zip(self.ratios,settings.get('ratios',[70,20,10])):spin.setValue(value)
        self.seed.setValue(settings.get('seed',123));self.allow_random.setChecked(settings.get('allow_leakage',False));self.allow_limited.setChecked(settings.get('allow_limited',False));self.draft_dirty=False;self.active_validated=draft.get('state')=='VALIDATED';self.saved_state.setText((draft.get('state','DRAFT')+' · 已保存 '+draft.get('saved_at','历史版本，需配置并保存草稿'))+' · '+record['id']);self.lifecycle_loading=False
        if draft.get('validation'):self.show_plan(draft['validation']['report'])
        self.update_counts();self.update_identity();self.render_versions()
    def reset_new_draft(self):
        self.lifecycle_loading=True;self.active_dataset=None;self.draft_revision=0;self.new_uuid=str(uuid4());self.drafts['__new__']=[];self.name.clear();self.allow_multi.setChecked(False);self.allow_random.setChecked(False);self.allow_limited.setChecked(False);self.preset.setCurrentIndex(0);self.apply_preset();self.seed.setValue(123)
        self.validation_mode.setCurrentIndex(0)
        for i in range(self.target_faults.count()):self.target_faults.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.inherit_camera();self.inherit_fault();self.draft_dirty=False;self.active_validated=False;self.saved_state.setText('尚未保存');self.lifecycle_loading=False;self.split_table.setRowCount(0);self.split_detail.clear()
    def choose_dataset(self):
        if self.updating:return
        target=self.existing.currentData();previous=self.active_dataset
        self.existing.blockSignals(True);self.existing.setCurrentIndex(max(0,self.existing.findData(previous)));self.existing.blockSignals(False)
        def switch():
            self.existing.blockSignals(True);self.existing.setCurrentIndex(max(0,self.existing.findData(target)));self.existing.blockSignals(False)
            if target:self.load_record(self.dataset_records[target])
            else:
                self.reset_new_draft();self.filter_rows();self.render_versions();self.update_identity()
        if self.guard_departure(switch):switch()
    def guard_departure(self,continuation):
        if self.draft_saving:return False
        if not self.draft_dirty:return True
        answer=QMessageBox.question(self,'数据集草稿未保存','当前草稿有未保存修改。保存后继续、放弃修改或取消？',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Save:self.save_requested.emit(continuation);return False
        if answer==QMessageBox.StandardButton.Discard:
            if self.active_dataset and self.active_dataset in self.dataset_records:self.load_record(self.dataset_records[self.active_dataset])
            else:
                self.lifecycle_loading=True;self.drafts['__new__']=[];self.name.clear();self.draft_dirty=False;self.active_validated=False;self.saved_state.setText('尚未保存');self.lifecycle_loading=False;self.update_counts()
            return True
        return False
    def update_identity(self):
        if not hasattr(self,'identity'):return
        by={r['id']:r for r in self.all_rows};rows=[by[f] for f in self.draft_frames() if f in by]
        state='未保存修改' if self.draft_dirty else 'VALIDATED' if self.active_validated else '已保存 DRAFT' if self.active_dataset else '尚未保存'
        camera_ids={self.target_camera.currentData()}
        if self.allow_multi.isChecked():camera_ids.update(r['camera_id'] or '__unlinked__' for r in rows)
        camera_text='、'.join(self.target_camera.itemText(self.target_camera.findData(cid)) for cid in sorted(c for c in camera_ids if c))
        text=f"数据集：{self.name.text() or '未选择'} · UUID：{self.active_dataset or '请先保存'}\n项目：{(self.project_identity or {}).get('name','未打开')} · 摄像头：{camera_text} · 故障："+'、'.join(self.target_faults.item(i).text() for i in range(self.target_faults.count()) if self.target_faults.item(i).checkState()==Qt.CheckState.Checked)+f"\n草稿{len(self.draft_frames())}张 / 正常{sum(r['image_tag']=='NORMAL' for r in rows)} / 异常{sum(r['image_tag']=='ABNORMAL' for r in rows)} · {state}"
        self.identity.setText(text);self.version_identity.setText(text)
        ready=bool(self.project_identity and self.name.text().strip() and self.draft_frames() and self.selected_fault_ids()) and sum(w.value() for w in self.ratios)==100
        self.split_button.setEnabled(ready and not self.draft_saving)
        self.split_save_state.setText('保存中，请稍候。' if self.draft_saving else '请填写名称、故障类型、图片成员，比例合计须为100%。' if not ready else '检查时将先原子化保存全部待处理修改（包括图片成员）。' if self.draft_dirty else '当前数据集已保存，可直接检查划分。')
        self.freeze_button.setEnabled(bool(self.active_dataset) and self.active_validated and not self.draft_dirty and not self.draft_saving)
    def render_versions(self):
        if not hasattr(self,'all_version_rows'):self.all_version_rows=[]
        self.version_rows=[v for v in self.all_version_rows if v['dataset_id']==self.active_dataset];self.versions.setRowCount(len(self.version_rows));self.empty_versions.setVisible(not self.version_rows)
        for i,v in enumerate(self.version_rows):
            values=[v['name'],v['number'],v['created_at'],v['summary']['images'],v['summary']['objects'],str(v['summary']['splits']),'FROZEN · '+v['summary'].get('admission',{}).get('split_status','历史审核'),v['id']]
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(value));self.versions.setItem(i,j,item)
    def show_plan(self,plan):
        self.split_detail.setPlainText(json.dumps({k:v for k,v in plan.items() if k!='samples'},ensure_ascii=False,indent=2));self.split_table.setRowCount(3)
        for i,(name,stats) in enumerate(plan.get('statistics',{}).items()):
            for j,value in enumerate([name,stats['target_percent'],stats['images'],round(stats['actual_percent'],2),stats['normal'],stats['abnormal'],stats['objects'],stats['source_groups'],stats.get('leakage_status','待检查')]):self.split_table.setItem(i,j,QTableWidgetItem(str(value)))
    def freeze_saved(self):
        if not self.active_dataset or self.draft_dirty or not self.active_validated:self.action_info.setText('请先保存当前草稿并自动划分检查。');return
        if QMessageBox.question(self,'检查并冻结新版本','仅冻结当前Dataset UUID已保存且检查通过的修订。历史版本保持不变。确认？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.freeze_requested.emit({'dataset_id':self.active_dataset,'draft_revision':self.draft_revision})
