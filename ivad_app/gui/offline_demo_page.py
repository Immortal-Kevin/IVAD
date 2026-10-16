"""Integrated P3.5 offline demo, explicitly preprocessing playback, never alarm events."""
import json
from pathlib import Path
from PySide6.QtCore import QTimer,Qt
from PySide6.QtWidgets import QWidget,QFileDialog
from ivad_app.gui.offline_demo_layout import OfflineDemoLayout
from ivad_app.gui.offline_demo_interaction import OfflineDemoInteraction
from ivad_app.video.reader import FileVideoSource
from fractions import Fraction
import math

class OfflineDemoPage(OfflineDemoInteraction,OfflineDemoLayout,QWidget):
    def __init__(self,window):
        super().__init__();self.setObjectName('p35Offline');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);self.setStyleSheet('QWidget#p35Offline, QWidget#p35OfflineBody {background:#f2f5fa; color:#18314f;}');self.w=window;self.s=window.s;self.root=None;self.busy=False;self.job=None;self.run_path=None;self.manifest=None;self.media_rows=[];self.model_rows=[]
        self.session_generation=0;self.load_generation=0;self.task_context=None;self.last_job_id=None;self.camera_rows=[];self.pending_media=None;self.demo_camera_consent=None;self.preview_generation=0;self.source_ready=False;self.build_layout()
        self.preview_timer=QTimer(self);self.preview_timer.setSingleShot(True);self.preview_timer.timeout.connect(lambda:self.preview.seek(self.pending_seek) if self.preview.loaded else None)
        self.timer=QTimer(self);self.timer.setInterval(400);self.timer.timeout.connect(self.watch);self.timer.start();self.setEnabled(False)
    def set_root(self,root):
        if root!=self.root:
            self.session_generation+=1;self.load_generation+=1;self.busy=False;self.task_context=None;self.last_job_id=None;self.status_bar.setText("尚未开始识别");self.tabs.setCurrentIndex(0);self.root=root;self.job=None;self.run_path=None;self.manifest=None;self.player.stop();self.preview.stop();self.demo_camera_consent=None;self.results.setRowCount(0);self.refresh()
        self.setEnabled(bool(root) and not self.s.lite)
    def refresh(self):
        if not self.root or self.busy:return
        self.busy=True;root=self.root;generation=self.session_generation
        def done(value,error):
            if root!=self.root or generation!=self.session_generation:return
            self.busy=False
            if error:self.set_message(error);return
            self.media_rows,self.model_rows,gpus,self.camera_rows=value
            project=self.s.projects.current;self.project_label.setText((project.site+' · '+project.name) if project.site else project.name)
            for combo,rows in [(self.media,[('未选择视频',None)]+[(r['name'],r['id']) for r in self.media_rows if r['state']=='READY']),(self.camera,[('未选择摄像头',None)]+[(r['name'],r['id']) for r in self.camera_rows]),(self.gpu,[(r.name,r.id) for r in gpus if r.id.startswith('nvidia:') and r.backend_available])]:
                old=combo.currentData();combo.blockSignals(True);combo.clear()
                for text,data in rows:combo.addItem(text,data)
                index=combo.findData(old)
                if index>=0:combo.setCurrentIndex(index)
                combo.blockSignals(False)
            if self.pending_media:
                self.media.setCurrentIndex(self.media.findData(self.pending_media));self.pending_media=None
            self.select_media();self.filter_models();self.refresh_history()
        self.w.runner.run(lambda:(*self.s.offline.choices(root),self.s.cameras.list(root)),done)
    def refresh_history(self):
        old=self.run_path;self.history.blockSignals(True);self.history.clear();self.history.addItem('选择本项目已完成演示缓存',None)
        for p in sorted((Path(self.root)/'demos').glob('*/manifest.json')):
            try:
                m=json.loads(p.read_text(encoding='utf8'))
                if m['state']=='SUCCEEDED' and (p.parent/'manifest.sha256').is_file():self.history.addItem(m['created_at']+' · '+m['id'][:8],str(p.parent))
            except (OSError,ValueError,KeyError):continue
        self.history.setCurrentIndex(max(0,self.history.findData(old)));self.history.blockSignals(False)
    def select_media(self):
        self.source_ready=False;self.preview_generation+=1;generation=self.preview_generation;self.preview_timer.stop();self.preview.stop()
        r=next((r for r in self.media_rows if r['id']==self.media.currentData()),None)
        if not r:self.media_info.setText('请选择演示视频。');return
        idx=self.camera.findData(r.get('camera_id'));self.camera.setCurrentIndex(max(0,idx));root=self.root
        def collect():
            row=self.s.media.get(r['id'],root);return row,FileVideoSource.probe(Path(row['accessible_path']))
        def done(value,error):
            if root!=self.root or generation!=self.preview_generation:return
            if error:self.media_info.setText('视频解码失败：'+error);self.set_message(error);return
            row,meta=value;duration=meta['duration_us'];minimum=max(1000,math.ceil(1000/float(Fraction(meta['nominal_fps'])))*1000) if meta['nominal_fps'] else 40000
            for c in [self.start_time,self.end_time]:c.blockSignals(True);c.setMaximum(duration/1e6);c.blockSignals(False)
            self.range_slider.configure(duration,minimum);self.slider_changed(self.range_slider.start,self.range_slider.end)
            owner=next((c['name'] for c in self.camera_rows if c['id']==row.get('camera_id')),'未关联（可确认仅用于演示的摄像头）')
            self.media_info.setText(row['name']+f" · {duration/1e6:.3f}秒 · {meta['display_width']}×{meta['display_height']} · {meta['container']} / {meta['codec']} · 摄像头："+owner)
            self.preview.load(row['accessible_path'],meta);self.source_ready=True
        self.w.runner.run(collect,done);self.configuration_changed()
    def show_model(self):
        r=next((r for r in self.model_rows if r['id']==self.model.currentData()),None)
        if not r:self.model_info.setText('没有可用实验模型；先检查模型仓库及冻结版本。');return
        self.model_info.setText(r['model']+' · '+r['id'][:8]+' · '+r['state']+'\n故障：'+ '、'.join(c['name'] for c in r['class_map'])+' · '+r.get('dataset_display','DatasetVersion')+' · '+r.get('split_status','历史审核')+'\n工程实验，未完成独立工业验证。');self.model_info.setToolTip('ModelVersion '+r['id']+'\nDatasetVersion '+r['dataset_version'])
    def import_video(self):
        if self.job or not self.root:return
        name,_=QFileDialog.getOpenFileName(self,'选择本机演示视频（复制到项目，原文件不移动不修改）','','视频 (*.mp4 *.avi *.mkv *.mov *.ts *.m4v);;所有文件 (*)')
        if name:self.submit('p2_import',dict(root=self.root,mode='COPY',paths=[name]),'import')
    def submit(self,kind,payload,operation):
        if self.job or self.busy:return
        self.busy=True;root=self.root;pid=self.s.projects.current.id;generation=self.session_generation;self.watch()
        def done(jid,error):
            if root!=self.root or generation!=self.session_generation:return
            self.busy=False
            if error:self.set_message(error);self.tabs.setCurrentIndex(0);return
            self.job=jid;self.last_job_id=jid;self.operation=operation
            if operation=="demo":
                self.task_context=dict(payload);self.load_generation+=1;self.player.stop();self.results.setRowCount(0);self.result_rows=[];self.detail_context.setText("当前任务运行中；历史缓存仍保留，尚未载入本次结果。");self.update_status("等待中");self.tabs.setCurrentIndex(1)
            self.set_message('后台任务已排队：'+jid)
        self.w.runner.run(lambda:self.s.jobs.submit(kind,pid,payload),done)
    def cancel(self):
        if self.job:self.w.runner.run(lambda:self.s.jobs.cancel(self.job))
    def watch(self):
        active=bool(self.job or self.busy);self.refresh_button.setEnabled(not active);self.history.setEnabled(not active);self.start_button.setEnabled(bool(self.root) and self.source_ready and not active);self.select_button.setEnabled(not active);self.reuse_button.setEnabled(not active);self.cancel_button.setEnabled(bool(self.job));self.export_button.setEnabled(bool(self.run_path) and self.player.loaded and not active);self.shot_button.setEnabled(bool(self.run_path) and self.player.loaded and not active)
        for control in [self.model,self.media,self.gpu,self.confidence,self.start_time,self.end_time,self.range_slider,self.camera,self.other_models]:control.setEnabled(not active)
        if not self.job:return
        r=self.s.jobs.get(self.job);
        if self.operation=="demo":self.update_status({"QUEUED":"等待中","RUNNING":"GPU 处理中","SUCCEEDED":"处理完成","FAILED":"FAILED 失败","CANCELLED":"已取消","INTERRUPTED":"已中断"}.get(r["state"],r["state"]),r["progress"])
        self.set_message(f"{r['state']} · {r['progress']}% · 预处理回放；日志见任务中心。")
        if r['state'] not in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:return
        self.job=None
        if r['state']=='SUCCEEDED':
            if self.operation=='import':
                self.pending_media=next(iter(r['result']['imported']),None) or next((x['id'] for x in r['result']['duplicates']),None);self.refresh();self.set_message('导入完成：'+str(r['result']))
            else:self.load_run(r['result']['path'],expected=self.task_context,completed=True);self.refresh_history()
        else:self.set_message(r['state']+'：'+str(r['error'])+'；失败/取消缓存不会载入，日志保留。',playback=True)
    def load_history(self):
        if self.history.currentData():self.load_run(self.history.currentData())
    def load_run(self,path,expected=None,completed=False):
        root=self.root;self.load_generation+=1;generation=self.load_generation;session=self.session_generation;fingerprint=self.configuration_fingerprint()
        def collect():
            manifest=self.s.offline.load(path)
            if expected and manifest.get("identity")!=self.s.offline.cache_identity(expected):raise ValueError("缓存完整身份与本次请求不一致。")
            return manifest
        def done(m,error):
            if root!=self.root or session!=self.session_generation or generation!=self.load_generation:return
            if expected and fingerprint!=self.configuration_fingerprint():self.set_message("配置已变化，未加载旧请求缓存。");return
            if error:self.set_message(error);self.update_status("FAILED 缓存加载失败");return
            if expected and (m["media_id"]!=expected["media_id"] or m["model_id"]!=expected["model_id"] or any(m["parameters"][k]!=expected[k] for k in ["start","end","confidence"])):
                self.set_message("缓存与本次任务配置不一致，拒绝加载。");self.update_status("FAILED 缓存不匹配");return
            self.run_path=path;self.manifest=m;self.player.load(str(Path(path)/'annotated.mp4'),m['cache_metadata']);self.timing.setText('预处理回放 · 缓存0秒对应原视频 '+str(m['first_source_time_us']/1e6)+' 秒。'+m['source_notice']);self.render_results();self.configuration_changed()
            self.detail_context.setText("缓存任务状态 "+m["state"]+" · Cache "+m["id"]+"\n"+self.timing.text()+'\nModelVersion '+m['model_id']+' · MediaAsset '+m['media_id']+' · DatasetVersion '+m['dataset_version']+' · GPU '+str(m.get('gpu','未知'))+' · 参数 '+str(m['parameters']));self.diagnostics.setText('缓存 '+path+'；推理日志 worker-console.log；任务中心保留状态。')
            self.update_status("处理完成，可以播放" if completed else "已加载缓存",manifest=m);self.tabs.setCurrentIndex(1)
            self.set_message(f"预处理回放：{len(m['frames'])}帧；缓存处理{m['end_to_end_fps']:.2f} FPS；不是实时报警。",playback=True)
        self.w.runner.run(collect,done)
    def set_message(self,text,playback=False):
        if playback or self.job or not self.manifest:self.info.setText(text)
        self.config_info.setText(text);self.task_details.setText(text)

    def update_status(self,state,progress=None,manifest=None):
        m=manifest;context=self.task_context or {}
        mid=m['model_id'] if m else context.get('model_id');media_id=m['media_id'] if m else context.get('media_id')
        model=next((x for x in self.model_rows if x['id']==mid),{})
        media=next((x for x in self.media_rows if x['id']==media_id),{})
        cid=(m.get('identity',{}).get('configuration',{}).get('camera_context') or media.get('camera_id')) if m else context.get('camera_id')
        camera=next((x['name'] for x in self.camera_rows if x['id']==cid),'未关联摄像头')
        confidence=m['parameters']['confidence'] if m else context.get('confidence','—')
        self.status_bar.setText(f"{camera} | {model.get('model','模型不可用')} · {(mid or '—')[:8]} | 置信度 {confidence} | {state}"+(f" {progress}%" if progress is not None else '')+f" | {model.get('state','状态未知')}")
        self.experiment_status.setText('工程实验模型，尚未完成独立工业验证。'+model.get('split_status','数据限制未知')+' · 预处理回放，不是实时推理。')
        self.status_bar.setToolTip('任务 '+str(self.job or self.last_job_id)+' · 缓存 '+str(self.run_path))

    def export(self):
        if not self.run_path:return
        parent=QFileDialog.getExistingDirectory(self,'导出演示结果到新独立目录（不覆盖）')
        if parent:
            path=self.run_path;self.w.runner.run(lambda:self.s.offline.export(path,parent),lambda value,error:self.set_message(error or '已导出：'+value))
    def screenshot(self):
        if not self.run_path or self.player.last_image is None:return
        parent=QFileDialog.getExistingDirectory(self,'保存当前检测截图及来源JSON')
        if parent:
            path=self.run_path;position=self.player.position_us;self.w.runner.run(lambda:self.s.offline.screenshot(path,parent,position),lambda value,error:self.set_message(error or '截图已保存：'+value))
