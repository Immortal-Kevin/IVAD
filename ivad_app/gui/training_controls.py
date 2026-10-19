"""Responsive training configuration and guarded, asynchronous preflight."""
import json
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QBoxLayout,QCheckBox,QComboBox,QMessageBox
from ivad_app.compute.legacy_training_parameters import DEFAULTS,validate_parameters
from ivad_app.compute.rfdetr_contract import MODEL as RF_MODEL,DEFAULTS as RF_DEFAULTS,parameters as rf_parameters

HELP={
 'epochs':'完整遍历训练集的次数。',
 'imgsz':'训练输入图像尺寸，须为32倍数；较大尺寸可能识别更小目标，但增加显存和计算量。',
 'batch':'每次参数更新处理的图片数量，过大可能显存不足。',
 'patience':'验证指标连续多少轮没有改善时提前停止；0表示关闭早停。',
 'seed':'随机种子，用于提高实验可重复性。',
 'lr0':'学习率，控制模型权重更新幅度。',
 'weight_decay':'权重衰减，用于正则化，降低部分过拟合风险。',
 'optimizer':'优化器决定如何根据梯度更新权重。当前Worker传递SGD、Adam、AdamW及auto给Ultralytics后端。',
 'augment':'训练时随机变化图片以增加场景多样性；工业设备场景不应过度变换。',
 'amp':'AMP（Automatic Mixed Precision）允许GPU在部分训练计算中使用低精度数值，可降低显存使用并可能提高训练速度。开启后仍需验证模型精度和数值稳定性。关闭时使用FP32模式。Worker启动时执行本地CUDA AMP探测，失败保留错误日志。'}

class TrainingControls:
    def init_controls(self):
        self.checked_configuration=None;self.submitting=False;self.checking=False;self.check_report=None
        for key,w in self.inputs.items():
            w.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
            w.setToolTip(HELP[key]+' 简易模式只读，切换高级训练以修改参数。')
            signal=w.toggled if isinstance(w,QCheckBox) else w.currentIndexChanged if isinstance(w,QComboBox) else w.valueChanged
            signal.connect(self.configuration_changed)
        for w in [self.mode,self.dataset_group,self.dataset,self.model,self.gpu,self.initial,self.resume]:w.currentIndexChanged.connect(self.configuration_changed)
        self.mode.currentIndexChanged.connect(self.update_mode)
        self.model.currentIndexChanged.connect(self.update_mode)
        self.gpu.currentIndexChanged.connect(self.update_mode)
        self.resume.currentIndexChanged.connect(self.update_mode)
        self.initial.setToolTip('选已有模型作为微调起点：创建新训练和独立模型版本，不覆盖旧实验；与恢复中断训练不同。')
        self.resume.setToolTip('恢复同数据版本、同架构的失败/取消训练检查点，沿用原参数和优化器进度；保留原任务，写入独立续训记录及目录。已完成模型应选择初始权重微调。')
        self.dataset.setToolTip('只能选择冻结版本；新草稿或新增样本不会改变此版本。')
        self.model.setToolTip('RF-DETR Nano：已验证目标检测，采用独立环境与专属参数。')
        self.gpu.setToolTip('仅显示已通过设备后端检查的NVIDIA GPU。资源使用现有GPU队列。')
        tips=['刷新可用数据集、模型及GPU设备，不会启动训练。','验证当前数据集版本、模型权重、训练参数、GPU后端和文件完整性。','使用当前冻结数据集版本和训练配置创建GPU训练任务；必须先通过训练前检查。','检查所选初始权重的模型加载及验证能力，不等于验证新训练模型的最终效果。','请求取消当前选定的训练任务。已完成任务不会被删除，历史记录予以保留。']
        for b,tip in zip(self.action_buttons,tips):b.setToolTip(tip);b.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips,True)
        self.update_mode();self.reflow_controls()

    def update_mode(self,*_):
        rf=self.model.currentText()==RF_MODEL
        self.advanced.setVisible(not rf);self.rf_advanced.setVisible(rf);self.resume.setEnabled(not rf)
        if rf:
            self.initial.setEnabled(True)
            advanced=self.mode.currentIndex()==1
            for key,w in self.rf_inputs.items():
                w.setEnabled(advanced)
                if not advanced:
                    w.blockSignals(True);value=RF_DEFAULTS[key]
                    if isinstance(w,QCheckBox):w.setChecked(value)
                    elif isinstance(w,QComboBox):w.setCurrentText(value)
                    else:w.setValue(value)
                    w.blockSignals(False)
            self.resume.setToolTip('RF本轮保留恢复CKPT但未验收优化器恢复；不能将CKPT冒充PTH推理权重。')
            device=getattr(self,'rf_device_info',{}).get(self.gpu.currentData())
            amp=self.rf_inputs['amp_dtype'];amp.setEnabled(advanced and bool(device and device.backend_available))
            amp.model().item(amp.findText('bf16')).setEnabled(bool(device and device.details.get('bf16_supported')))
            return
        advanced=self.mode.currentIndex()==1;resuming=bool(self.resume.currentData())
        previous=next((r for r in self.rows if r['id']==self.resume.currentData()),None)
        self.initial.setEnabled(not resuming)
        self.advanced.setEnabled(True)
        for key,w in self.inputs.items():
            supported=key!='amp' or bool(self.gpu.currentData() and self.gpu.currentData().startswith('nvidia:'))
            w.setEnabled(advanced and supported and not resuming)
            w.setToolTip(HELP[key]+(' 恢复中断训练沿用原任务参数；如需修改，请选择新训练。' if resuming else ' 简易模式采用推荐参数，切换高级训练以修改。' if not advanced else ' 当前无可用NVIDIA CUDA后端，不能启用。' if not supported else ''))
        if not advanced or previous:
            values=previous['parameters'] if previous else DEFAULTS
            for key,w in self.inputs.items():
                w.blockSignals(True)
                if isinstance(w,QCheckBox):w.setChecked(values[key])
                elif isinstance(w,QComboBox):w.setCurrentText(values[key])
                else:w.setValue(values[key])
                w.blockSignals(False)
        if not self.inputs['amp'].isEnabled() and not resuming:self.inputs['amp'].setChecked(False)

    def configuration(self,operation='train'):
        if not self.root or not self.dataset.currentData() or not self.gpu.currentData():raise ValueError('请选择冻结数据集版本及可用NVIDIA GPU。')
        if self.model.currentText()==RF_MODEL:
            values={k:w.isChecked() if isinstance(w,QCheckBox) else w.currentText() if isinstance(w,QComboBox) else w.value() for k,w in self.rf_inputs.items()}
            return dict(root=self.root,version_id=self.dataset.currentData(),device_id=self.gpu.currentData(),model=RF_MODEL,parameters=rf_parameters(values),initial_model_id=self.initial.currentData(),resume_run_id=None,operation=operation)
        values={k:w.isChecked() if isinstance(w,QCheckBox) else w.currentText() if isinstance(w,QComboBox) else w.value() for k,w in self.inputs.items()} if self.mode.currentIndex()==1 else {}
        if operation=='train' and self.resume.currentData():
            previous=next((r for r in self.rows if r['id']==self.resume.currentData()),None)
            if previous:values=dict(previous['parameters'])
        return dict(root=self.root,version_id=self.dataset.currentData(),device_id=self.gpu.currentData(),model=self.model.currentText(),parameters=validate_parameters(values),initial_model_id=self.initial.currentData(),resume_run_id=self.resume.currentData() if operation=='train' else None,operation=operation)

    def fingerprint(self):return json.dumps(self.configuration(),sort_keys=True,default=str)
    def configuration_changed(self,*_):
        self.checked_configuration=None;self.check_report=None
        if not hasattr(self,'info'):return
        try:self.fingerprint();text='配置已变化，请重新执行训练前检查。'
        except Exception as e:text=str(e)
        self.info.setText(text);self.action_buttons[2].setEnabled(False)

    def preflight(self):
        if self.checking or self.submitting:return
        try:payload=self.configuration();token=self.fingerprint()
        except Exception as e:self.info.setText(str(e));return
        self.checking=True;self.action_buttons[1].setEnabled(False);self.info.setText('正在后台检查数据、权重、参数及GPU…')
        def done(report,error):
            self.checking=False;self.action_buttons[1].setEnabled(True)
            try:unchanged=token==self.fingerprint()
            except Exception:unchanged=False
            if not unchanged:self.info.setText('检查期间配置变化，请重新检查。');return
            self.checked_configuration=None if error else token;self.check_report=None if error else report
            self.action_buttons[2].setEnabled(not error);self.info.setText(error or '预检通过：'+str(report['counts'])+'。启动前仍复核文件与GPU。')
        self.runner.run(lambda:self.s.training.configuration_preflight(payload),done)

    def start(self,operation='train'):
        if self.submitting or self.checking:return
        try:
            payload=self.configuration(operation)
            if operation=='train' and self.checked_configuration!=self.fingerprint():raise ValueError('请先通过当前配置的训练前检查。')
        except Exception as e:self.info.setText(str(e));return
        root=self.root;project_id=self.s.projects.current.id;checked_report=self.check_report;self.submitting=True
        for i in [1,2,3]:self.action_buttons[i].setEnabled(False)
        def submit():
            result=self.s.training.configuration_preflight(payload)
            if operation=='train' and result!=checked_report:raise ValueError('预检后文件或实际配置已变化，请重新检查。')
            return self.s.jobs.submit('p3_validate' if operation=='validate' else 'p3_train',project_id,payload)
        def done(jid,error):
            self.submitting=False;self.checked_configuration=None
            for i in [1,3]:self.action_buttons[i].setEnabled(True)
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.job_id=jid;self.info.setText('GPU任务已排队：'+jid+'；当前任务参数固定，新任务配置与其独立。');self.refresh()
        self.runner.run(submit,done)

    def cancel(self):
        row=next((r for r in self.rows if r['id']==self.selected_run),None)
        if (not row or row['state'] not in {'QUEUED','PREPARING','RUNNING'}) and self.job_id:
            job=self.s.jobs.get(self.job_id)
            if job['state'] in {'QUEUED','RUNNING'}:
                jid=self.job_id
                if QMessageBox.question(self,'确认取消训练','取消当前已提交任务？历史与已有检查点保留。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
                    self.runner.run(lambda:self.s.jobs.cancel(jid),lambda _,e:self.info.setText(e or '已请求取消。'))
                return
        if not row or row['state'] not in {'QUEUED','PREPARING','RUNNING'}:self.info.setText('请选择正在执行或排队的训练；完成记录不会删除。');return
        jid=row.get('job_id')
        if jid and QMessageBox.question(self,'确认取消训练','取消TrainingRun '+row['id']+'？历史及已有检查点保留。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)==QMessageBox.StandardButton.Yes:
            self.runner.run(lambda:self.s.jobs.cancel(jid),lambda _,e:self.info.setText(e or '已请求取消，历史与检查点保留。'))

    def reflow_controls(self):
        wide=self.width()>=1100
        self.config_layout.setDirection(QBoxLayout.Direction.LeftToRight if wide else QBoxLayout.Direction.TopToBottom)
        columns=5 if wide else 2 if self.width()>=650 else 1
        for i,b in enumerate(self.action_buttons):self.actions.addWidget(b,i//columns,i%columns)
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if hasattr(self,'action_buttons'):self.reflow_controls()
