from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QFormLayout,QComboBox,QSpinBox,QDoubleSpinBox,QCheckBox,QLabel,QScrollArea,QGroupBox,QMessageBox,QFileDialog,QPlainTextEdit,QInputDialog
from ivad_app.gui.pages import button,table
from ivad_app.gui.training_controls import TrainingControls
from ivad_app.services.training_service import DEFAULTS,validate_parameters

class TrainingPage(TrainingControls,QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName('p3Training');self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True);self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);self.w=window;self.s=window.s;self.runner=window.runner;self.root=None;self.busy=False;self.job_id=None;self.rows=[];self.selected_run=None
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setObjectName('p3TrainingScroll');scroll.setWidgetResizable(True);outer.addWidget(scroll);body=QWidget();body.setObjectName('p3TrainingBody');body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);scroll.setWidget(body);v=QVBoxLayout(body)
        title=QLabel('P3 · GPU模型训练与验证');title.setObjectName('title');v.addWidget(title)
        note=QLabel('仅使用有效冻结的目标检测版本（历史审核或显式实验准入）。正常无框是负样本；异常无框/未知/剔除不可训练。测试指标不代表工业堵煤准确率。');note.setWordWrap(True);v.addWidget(note)
        self.config_layout=QHBoxLayout();v.addLayout(self.config_layout);self.basic=QGroupBox("训练基础配置");form=QFormLayout(self.basic);self.config_layout.addWidget(self.basic,4)
        self.mode=QComboBox();self.mode.addItems(['简易训练','高级训练']);form.addRow('训练模式',self.mode)
        self.dataset_group=QComboBox();self.dataset_group.setObjectName('training_dataset_group');form.addRow('所属数据集',self.dataset_group);self.frozen_versions=[];self.dataset_group.currentIndexChanged.connect(self.filter_dataset_versions)
        self.dataset=QComboBox();self.dataset.setObjectName('training_dataset');form.addRow('冻结数据集版本',self.dataset)
        self.model=QComboBox();self.model.addItems(['yolo26n','yolo11n']);form.addRow('基础模型',self.model)
        self.gpu=QComboBox();self.gpu.setObjectName('training_gpu');form.addRow('NVIDIA GPU',self.gpu)
        self.initial=QComboBox();form.addRow('初始权重',self.initial)
        self.resume=QComboBox();self.resume.setToolTip('同数据版本与架构，使用原训练参数和已完成epoch的优化器状态；写入新的训练目录，不覆盖原实验。');form.addRow('条件恢复（沿用原参数）',self.resume)
        self.advanced=QGroupBox('高级参数（简易模式采用下列推荐默认值）');params=QFormLayout(self.advanced);self.config_layout.addWidget(self.advanced,6);self.inputs={}
        for key,label,lo,hi in [('epochs','轮数 Epochs',1,10000),('imgsz','图像尺寸（32倍数）',64,2048),('batch','每批图片数（显存不足时减小）',1,64),('patience','早停等待轮数，0关闭',0,10000),('seed','随机种子',0,2147483647)]:
            widget=QSpinBox();widget.setRange(lo,hi);widget.setValue(DEFAULTS[key]);widget.setObjectName('train_'+key);params.addRow(label,widget);self.inputs[key]=widget
        for key,label,lo,hi in [('lr0','初始学习率',.000001,1),('weight_decay','权重衰减',0,1)]:
            widget=QDoubleSpinBox();widget.setDecimals(6);widget.setRange(lo,hi);widget.setValue(DEFAULTS[key]);params.addRow(label,widget);self.inputs[key]=widget
        widget=QComboBox();widget.addItems(['SGD','Adam','AdamW','auto']);params.addRow('优化器',widget);self.inputs['optimizer']=widget
        for key,label in [('augment','启用数据增强'),('amp','AMP混合精度（关闭为FP32）')]:
            widget=QCheckBox(label);widget.setChecked(DEFAULTS[key]);params.addRow(widget);self.inputs[key]=widget
        self.advanced.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
        bar=QGridLayout();self.actions=bar;self.action_buttons=[];v.addLayout(bar)
        for i,(title,fn,name) in enumerate([('刷新数据与GPU',self.refresh,'training_refresh'),('训练前检查',self.preflight,'training_preflight'),('启动GPU训练',self.start,'training_start'),('验证所选初始模型',lambda:self.start('validate'),'training_validate'),('取消所选训练',self.cancel,'training_cancel')]):
            b=button(title,fn,name=name);self.action_buttons.append(b);bar.addWidget(b,0,i)
        self.info=QLabel('请打开项目，并在设备与后端完成GPU检查。');self.info.setWordWrap(True);v.addWidget(self.info)
        self.runs=table(['训练ID','模型','状态','轮次','指标 / 错误']);self.runs.setMinimumHeight(140);v.addWidget(self.runs);self.runs.itemSelectionChanged.connect(self.show_run)
        self.metrics=QPlainTextEdit();self.metrics.setReadOnly(True);self.metrics.setMaximumHeight(160);v.addWidget(self.metrics)
        self.plot_choice=QComboBox();self.plot_choice.addItem('训练与验证曲线','results.png');self.plot_choice.addItem('混淆矩阵（适用时）','confusion_matrix.png');self.plot_choice.currentIndexChanged.connect(self.show_run);v.addWidget(self.plot_choice)
        self.curve=QLabel('训练结束后显示真实结果曲线（如生成）。');self.curve.setAlignment(Qt.AlignmentFlag.AlignCenter);v.addWidget(self.curve)
        self.init_controls()
        self.timer=QTimer(self);self.timer.setInterval(1000);self.timer.timeout.connect(self.refresh);self.timer.start()
    def set_root(self,root):
        if root!=self.root:self.checked_configuration=None;self.root=root;self.job_id=None;self.selected_run=None;self.rows=[];self.runs.setRowCount(0);self.curve.clear();self.refresh();self.configuration_changed()
        self.setEnabled(bool(root) and not self.s.lite)
    def refresh(self):
        if not self.root or self.busy or self.s.lite:return
        self.busy=True;root=self.root
        def collect():return self.s.datasets.training_versions(root),self.s.training.runs(root),self.s.models.versions(root),self.s.devices.snapshot()
        def done(data,error):
            self.busy=False
            if root!=self.root:return
            if error:self.info.setText(error);return
            versions,runs,models,gpus=data
            def fill(combo,rows):
                old=combo.currentData();combo.blockSignals(True);combo.clear()
                for title,value in rows:combo.addItem(title,value)
                idx=combo.findData(old)
                if idx>=0:combo.setCurrentIndex(idx)
                combo.blockSignals(False)
            self.frozen_versions=versions;seen={r['dataset_id']:r['name'] for r in versions};fill(self.dataset_group,[(name+' · '+did[:8],did) for did,name in seen.items()]);self.filter_dataset_versions();fill(self.gpu,[(d.name+' · '+d.status,d.id) for d in gpus if d.id.startswith('nvidia:') and d.backend_available])
            fill(self.initial,[('本地P0官方基础权重',None)]+[(r.get('model','?')+' · '+r['id'][:8],r['id']) for r in models if r['path'].endswith('.pt')]);fill(self.resume,[('新训练（不恢复）',None)]+[(r['model']+' · '+r['id'][:8],r['id']) for r in runs if r['state'] in {'FAILED','CANCELLED'}])
            self.rows=runs;self.runs.blockSignals(True);self.runs.setRowCount(len(runs))
            from PySide6.QtWidgets import QTableWidgetItem
            for i,r in enumerate(runs):
                for j,value in enumerate([r['id'][:8],r['model'],r['state'],str(r.get('progress',{}).get('epoch',0)),str(r.get('error') or r.get('result',{}).get('metrics',{}))]):self.runs.setItem(i,j,QTableWidgetItem(value))
                if r['id']==self.selected_run:self.runs.selectRow(i)
            self.runs.blockSignals(False)
            if self.selected_run:self.show_run()
            try:valid=self.checked_configuration==self.fingerprint()
            except Exception:valid=False
            if not valid:self.checked_configuration=None
            self.action_buttons[2].setEnabled(valid and not self.submitting);self.update_mode()
        self.runner.run(collect,done)
    def filter_dataset_versions(self,*_):
        if not hasattr(self,'dataset'):return
        old=self.dataset.currentData();self.dataset.blockSignals(True);self.dataset.clear()
        for r in self.frozen_versions:
            if r['dataset_id']==self.dataset_group.currentData():self.dataset.addItem(r['name']+' v'+str(r['number'])+' · '+r['id'][:8],r['id'])
        idx=self.dataset.findData(old)
        if idx>=0:self.dataset.setCurrentIndex(idx)
        self.dataset.blockSignals(False)
    def show_run(self):
        i=self.runs.currentRow()
        if not 0<=i<len(self.rows):return
        r=self.rows[i];self.selected_run=r['id'];progress=r.get('progress',{});result=r.get('result',{})
        import json
        self.metrics.setPlainText(json.dumps(dict(state=r['state'],actual_parameters=r.get('parameters'),progress=progress,metrics=result.get('metrics'),seconds=result.get('seconds'),gpu=result.get('environment'),error=r.get('error'),log=r['path']+'/worker-console.log'),ensure_ascii=False,indent=2))
        image=Path(self.root)/r['path']/('validation' if r.get('operation')=='validate' else 'run')/self.plot_choice.currentData()
        if image.exists():self.curve.setPixmap(QPixmap(str(image)).scaledToWidth(700,Qt.TransformationMode.SmoothTransformation))
        else:self.curve.setText('该图尚未生成；请查看训练日志。')

class ModelsPage(QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName('p3Models');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);self.w=window;self.root=None;self.rows=[];self.busy=False;v=QVBoxLayout(self);v.addWidget(QLabel('模型仓库 · EXPERIMENTAL → CANDIDATE → PRODUCTION'))
        note=QLabel('PRODUCTION仅为注册状态，不部署厂区，不自动替换权重。候选门槛为技术验证，不代表工业准确率达标。');note.setWordWrap(True);v.addWidget(note)
        self.thresholds={};limits=QFormLayout();v.addLayout(limits)
        for key,title,value in [('precision','候选最低Precision',.5),('recall','候选最低Recall',.5),('map50','候选最低mAP50',.5),('map50_95','候选最低mAP50-95',.25)]:
            spin=QDoubleSpinBox();spin.setRange(0,1);spin.setSingleStep(.05);spin.setValue(value);limits.addRow(title,spin);self.thresholds[key]=spin
        self.table=table(['版本ID','模型','状态','SHA256','指标']);v.addWidget(self.table)
        bar=QGridLayout();v.addLayout(bar)
        for i,(title,fn,name) in enumerate([('刷新',self.refresh,'models_refresh'),('导入可信模型',self.import_model,'model_import'),('完整性检查',self.verify,'model_verify'),('申请候选',lambda:self.transition('CANDIDATE'),'model_candidate'),('批准生产注册',lambda:self.transition('PRODUCTION'),'model_production'),('回滚到所选历史版本',lambda:self.transition('PRODUCTION',True),'model_rollback'),('导出模型权重/ONNX',self.export_model,'model_export')]):bar.addWidget(button(title,fn,name=name),i//3,i%3)
        self.info=QLabel('新训练模型默认实验版本。导入本身不代表模型已验证。');self.info.setWordWrap(True);v.addWidget(self.info)
    def set_root(self,root):self.root=root;self.setEnabled(bool(root) and not self.w.s.lite);self.refresh()
    def refresh(self):
        if not self.root or self.busy:return
        self.busy=True;self.setEnabled(False);root=self.root
        def done(rows,error):
            self.busy=False;self.setEnabled(bool(self.root) and not self.w.s.lite)
            if root!=self.root:self.refresh();return
            if error:self.info.setText(error);return
            self.rows=rows;self.table.setRowCount(len(rows));from PySide6.QtWidgets import QTableWidgetItem
            for i,r in enumerate(rows):
                for j,value in enumerate([r['id'][:8],r.get('model','未验证'),r['state'],r['sha256'],str(r.get('metrics',{}))]):self.table.setItem(i,j,QTableWidgetItem(value))
        self.w.runner.run(lambda:self.w.s.models.versions(root),done)
    def selected(self):
        i=self.table.currentRow();return self.rows[i] if 0<=i<len(self.rows) else None
    def verify(self):
        r=self.selected()
        if r:self.w.runner.run(lambda:self.w.s.models.verify(r['id'],self.root),lambda _,e:self.info.setText(e or 'SHA256完整性通过；不代表GPU兼容或工业准确率。'))
    def transition(self,state,rollback=False):
        if self.busy:return
        r=self.selected()
        if not r:return
        approved=False
        if state=='PRODUCTION':
            approved=QMessageBox.question(self,'人工发布批准','明确批准所选模型成为生产注册版本？这会切换本项目注册指针，不部署设备，也不代表工业安全合格。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes
            if not approved:return
        root=self.root
        thresholds={k:w.value() for k,w in self.thresholds.items()}
        self.busy=True;self.setEnabled(False)
        def done(_,error):
            self.busy=False;self.info.setText(error or '注册状态已记录。');self.refresh()
        self.w.runner.run(lambda:self.w.s.models.transition(r['id'],state,r['revision'],root,approved=approved,rollback=rollback,thresholds=thresholds),done)
    def import_model(self):
        path,_=QFileDialog.getOpenFileName(self,'选择可信模型','','模型 (*.pt *.onnx)')
        if not path:return
        if QMessageBox.question(self,'确认模型来源','确认此模型来源可信？PT加载可能执行代码。仅登记不等于已验证，不可信模型请取消。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        architecture,ok=QInputDialog.getItem(self,'声明模型架构','选择可信权重的实际架构（能力仍待GPU验证）',['yolo26n','yolo11n','unverified'],0,False)
        if not ok:return
        root=self.root
        self.w.runner.run(lambda:self.w.s.models.register(path,{'model':architecture,'task':'detect' if architecture!='unverified' else 'unverified','source':'user confirmed trusted; architecture declared, not verified'},root,trusted=True),lambda _,e:(self.info.setText(e or '已登记EXPERIMENTAL，训练/验证能力尚未确认。'),self.refresh()))
    def export_model(self):
        row=self.selected()
        if not row:return
        parent=QFileDialog.getExistingDirectory(self,'导出模型工件（不含应用程序）')
        if not parent:return
        root=self.root;mid=row['id']
        self.w.runner.run(lambda:self.w.s.models.export(mid,parent,root),lambda path,error:self.info.setText(error or '模型工件已导出：'+path))
