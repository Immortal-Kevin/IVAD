"""Integrated P3.5 offline demo, explicitly preprocessing playback, never alarm events."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QComboBox,QDoubleSpinBox,QLabel,QFileDialog,QTableWidgetItem,QScrollArea
from ivad_app.gui.pages import button,table
from ivad_app.gui.video_player import VideoPlayer

class OfflineDemoPage(QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName('p35Offline');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);self.setStyleSheet('QWidget#p35Offline, QWidget#p35OfflineBody {background:#f2f5fa; color:#18314f;}');self.w=window;self.s=window.s;self.root=None;self.busy=False;self.job=None;self.run_path=None;self.manifest=None;self.media_rows=[];self.model_rows=[]
        outer=QVBoxLayout(self);scroll=QScrollArea();scroll.setWidgetResizable(True);outer.addWidget(scroll);body=QWidget();body.setObjectName('p35OfflineBody');body.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);v=QVBoxLayout(body);scroll.setWidget(body)
        title=QLabel('P3.5 · 离线 AI 识别演示');title.setObjectName('title');v.addWidget(title)
        self.warning=QLabel('工程实验，未完成独立工业验证。预处理回放：先GPU识别生成缓存，再播放；检测结果不是已确认工业报警。');self.warning.setWordWrap(True);v.addWidget(self.warning)
        self.model=QComboBox();self.media=QComboBox();self.gpu=QComboBox();self.confidence=QDoubleSpinBox();self.confidence.setRange(.01,1);self.confidence.setSingleStep(.05);self.confidence.setValue(.25);self.confidence.setToolTip('低阈值保留更多预测，也可能增加误检；不是报警阈值。')
        self.start_time=QDoubleSpinBox();self.end_time=QDoubleSpinBox()
        for w in [self.start_time,self.end_time]:w.setRange(0,1000000);w.setDecimals(3);w.setSuffix(' 秒')
        form=QFormLayout();v.addLayout(form)
        for text,control in [('实验模型版本',self.model),('项目录像',self.media),('NVIDIA GPU',self.gpu),('置信度阈值',self.confidence)]:form.addRow(text,control)
        row=QHBoxLayout();row.addWidget(self.start_time);row.addWidget(self.end_time);form.addRow('原视频处理范围 [起点,终点)',row)
        self.model_info=QLabel();self.model_info.setWordWrap(True);v.addWidget(self.model_info)
        row=QHBoxLayout();v.addLayout(row)
        self.refresh_button=button('刷新录像/模型/GPU',self.refresh,name='offline_refresh');self.import_button=button('导入演示 MP4…',self.import_video,name='offline_import');self.start_button=button('开始 AI 识别',self.start,True,'offline_start');self.cancel_button=button('取消预处理',self.cancel,name='offline_cancel')
        for b in [self.refresh_button,self.import_button,self.start_button,self.cancel_button]:row.addWidget(b)
        self.refresh_button.setToolTip('刷新项目录像、实验模型和已检查GPU列表。首次使用请先到“设备与后端”执行检查。')
        self.gpu.setToolTip('只允许已检查可用的NVIDIA CUDA；Worker执行时复核，不允许CPU回退。')
        self.info=QLabel('请打开项目，选择实验模型及录像。首次建议只处理10秒。');self.info.setWordWrap(True);v.addWidget(self.info)
        self.history=QComboBox();self.history.addItem('选择本项目已完成演示缓存',None);self.history.currentIndexChanged.connect(self.load_history);v.addWidget(self.history)
        self.player=VideoPlayer();self.player.setMinimumHeight(300);self.player.capture_button.hide();v.addWidget(self.player,1)
        self.timing=QLabel('缓存时间从0开始；结果表显示原视频相对时间。');self.timing.setWordWrap(True);v.addWidget(self.timing)
        self.results=table(['原视频相对时间（秒）','检测类别','Confidence','模型版本','框数']);self.results.setMinimumHeight(160);self.results.itemSelectionChanged.connect(self.seek_result);v.addWidget(self.results)
        row=QHBoxLayout();v.addLayout(row);self.export_button=button('导出带框视频 + CSV/JSON',self.export,name='offline_export');self.shot_button=button('导出当前检测截图',self.screenshot,name='offline_screenshot');row.addWidget(self.export_button);row.addWidget(self.shot_button)
        self.media.currentIndexChanged.connect(self.select_media);self.model.currentIndexChanged.connect(self.show_model)
        self.timer=QTimer(self);self.timer.setInterval(400);self.timer.timeout.connect(self.watch);self.timer.start();self.setEnabled(False)
    def set_root(self,root):
        if root!=self.root:
            self.root=root;self.job=None;self.run_path=None;self.manifest=None;self.player.stop();self.results.setRowCount(0);self.refresh()
        self.setEnabled(bool(root) and not self.s.lite)
    def refresh(self):
        if not self.root or self.busy:return
        self.busy=True;root=self.root
        def done(value,error):
            self.busy=False
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.media_rows,self.model_rows,gpus=value
            for combo,rows in [(self.media,[(r['name'],r['id']) for r in self.media_rows if r['state']=='READY']),(self.model,[(r['model']+' · '+r['id'][:8]+' · EXPERIMENTAL',r['id']) for r in self.model_rows]),(self.gpu,[(r.name,r.id) for r in gpus if r.id.startswith('nvidia:') and r.backend_available])]:
                old=combo.currentData();combo.blockSignals(True);combo.clear()
                for text,data in rows:combo.addItem(text,data)
                index=combo.findData(old)
                if index>=0:combo.setCurrentIndex(index)
                combo.blockSignals(False)
            self.select_media();self.show_model();self.refresh_history()
        self.w.runner.run(lambda:self.s.offline.choices(root),done)
    def refresh_history(self):
        old=self.run_path;self.history.blockSignals(True);self.history.clear();self.history.addItem('选择本项目已完成演示缓存',None)
        for p in sorted((Path(self.root)/'demos').glob('*/manifest.json')):
            try:
                m=json.loads(p.read_text(encoding='utf8'))
                if m['state']=='SUCCEEDED' and (p.parent/'manifest.sha256').is_file():self.history.addItem(m['created_at']+' · '+m['id'][:8],str(p.parent))
            except (OSError,ValueError,KeyError):continue
        self.history.setCurrentIndex(max(0,self.history.findData(old)));self.history.blockSignals(False)
    def select_media(self):
        r=next((r for r in self.media_rows if r['id']==self.media.currentData()),None)
        if r:
            duration=r['video']['duration_us']/1e6;self.start_time.setMaximum(duration);self.end_time.setMaximum(duration);self.start_time.setValue(0);self.end_time.setValue(min(10,duration))
        self.show_model()
    def show_model(self):
        r=next((r for r in self.model_rows if r['id']==self.model.currentData()),None)
        if not r:self.model_info.setText('没有可用实验模型；先检查模型仓库及冻结版本。');return
        self.model_info.setText('模型 '+r['id']+' · '+r['state']+'\n故障：'+ '、'.join(c['name'] for c in r['class_map'])+' · '+r.get('dataset_display','DatasetVersion')+' · '+r['dataset_version']+'\n工程实验，未完成独立工业验证。来源信息将在任务结果中核验显示。')
    def import_video(self):
        if self.job or not self.root:return
        name,_=QFileDialog.getOpenFileName(self,'导入演示MP4（复制到项目，不改原录像）','','MP4 (*.mp4)')
        if name:self.submit('p2_import',dict(root=self.root,mode='COPY',paths=[name]),'import')
    def submit(self,kind,payload,operation):
        if self.job or self.busy:return
        self.busy=True;root=self.root;pid=self.s.projects.current.id
        def done(jid,error):
            self.busy=False
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.job=jid;self.operation=operation;self.info.setText('后台任务已排队：'+jid)
        self.w.runner.run(lambda:self.s.jobs.submit(kind,pid,payload),done)
    def start(self):
        if not self.root or not self.media.currentData() or not self.model.currentData() or not self.gpu.currentData():self.info.setText('请选择项目录像、有效实验模型和可用NVIDIA GPU。');return
        if self.end_time.value()<=self.start_time.value():self.info.setText('终点必须晚于起点。');return
        self.submit('p35_offline',dict(root=self.root,media_id=self.media.currentData(),model_id=self.model.currentData(),device_id=self.gpu.currentData(),confidence=self.confidence.value(),start=self.start_time.value(),end=self.end_time.value()),'demo')
    def cancel(self):
        if self.job:self.w.runner.run(lambda:self.s.jobs.cancel(self.job))
    def watch(self):
        active=bool(self.job or self.busy);self.start_button.setEnabled(bool(self.root) and not active);self.import_button.setEnabled(not active);self.cancel_button.setEnabled(bool(self.job));self.export_button.setEnabled(bool(self.run_path));self.shot_button.setEnabled(bool(self.run_path))
        for control in [self.model,self.media,self.gpu,self.confidence,self.start_time,self.end_time]:control.setEnabled(not active)
        if not self.job:return
        r=self.s.jobs.get(self.job);self.info.setText(f"{r['state']} · {r['progress']}% · 预处理回放；日志见任务中心。")
        if r['state'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:return
        self.job=None
        if r['state']=='SUCCEEDED':
            if self.operation=='import':self.refresh();self.info.setText('导入完成：'+str(r['result']))
            else:self.load_run(r['result']['path']);self.refresh_history()
        else:self.info.setText(r['state']+'：'+r['error']+'；失败/取消缓存不会载入，日志保留。')
    def load_history(self):
        if self.history.currentData():self.load_run(self.history.currentData())
    def load_run(self,path):
        root=self.root
        def done(m,error):
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.run_path=path;self.manifest=m;self.player.load(str(Path(path)/'annotated.mp4'),m['cache_metadata']);self.timing.setText('预处理回放 · 缓存0秒对应原视频 '+str(m['first_source_time_us']/1e6)+' 秒。'+m['source_notice']+'\n回放模型 '+m['model_id']+' · 视频 '+m['media_id']+' · DatasetVersion '+m['dataset_version']);self.result_rows=[];self.results.blockSignals(True)
            for r in m['frames']:
                names='、'.join(sorted({m['classes'][int(b[5])] for b in r['boxes']})) or '无检测目标';confidence='、'.join(f'{b[4]:.3f}' for b in r['boxes']) or '—';self.result_rows.append((r,[f"{r['time_us']/1e6:.3f}",names,confidence,m['model_id'][:8],len(r['boxes'])]))
            self.results.setRowCount(len(self.result_rows))
            for i,(_,values) in enumerate(self.result_rows):
                for j,value in enumerate(values):self.results.setItem(i,j,QTableWidgetItem(str(value)))
            self.results.blockSignals(False);self.info.setText(f"预处理完成：{len(m['frames'])}帧，缓存处理{m['end_to_end_fps']:.2f} FPS，模型调用{m['inference_fps']:.2f} FPS；不是实时报警。")
        self.w.runner.run(lambda:self.s.offline.load(path),done)
    def seek_result(self):
        i=self.results.currentRow()
        if self.manifest and 0<=i<len(self.result_rows):self.player.seek(self.result_rows[i][0]['cache_time_us'])
    def export(self):
        if not self.run_path:return
        parent=QFileDialog.getExistingDirectory(self,'导出演示结果到新独立目录（不覆盖）')
        if parent:
            path=self.run_path;self.w.runner.run(lambda:self.s.offline.export(path,parent),lambda value,error:self.info.setText(error or '已导出：'+value))
    def screenshot(self):
        if not self.run_path or self.player.last_image is None:return
        parent=QFileDialog.getExistingDirectory(self,'保存当前检测截图及来源JSON')
        if parent:
            path=self.run_path;position=self.player.position_us;self.w.runner.run(lambda:self.s.offline.screenshot(path,parent,position),lambda value,error:self.info.setText(error or '截图已保存：'+value))
