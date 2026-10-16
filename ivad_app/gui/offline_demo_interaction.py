"""Selection/range/cache interactions, separate from GPU execution."""
from fractions import Fraction
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QListWidget,QListWidgetItem,QDialogButtonBox,QFileDialog,QMessageBox,QTableWidgetItem

def time_text(us):
    ms=round(us/1000);seconds,ms=divmod(ms,1000);minutes,seconds=divmod(seconds,60);hours,minutes=divmod(minutes,60)
    return (f'{hours:02d}:' if hours else '')+f'{minutes:02d}:{seconds:02d}.{ms:03d}'

class OfflineDemoInteraction:
    def choose_project_video(self):
        dialog=QDialog(self);dialog.setWindowTitle('选择当前项目录像');dialog.resize(760,450);v=QVBoxLayout(dialog);items=QListWidget();v.addWidget(items)
        for r in self.media_rows:
            if r['state']!='READY':continue
            camera=next((c['name'] for c in self.camera_rows if c['id']==r.get('camera_id')),'未关联摄像头');item=QListWidgetItem(r['name']+' · '+camera+' · '+str(round(r['video']['duration_us']/1e6,3))+'秒');item.setData(Qt.ItemDataRole.UserRole,r['id']);items.addItem(item)
        controls=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);v.addWidget(controls);controls.accepted.connect(dialog.accept);controls.rejected.connect(dialog.reject);items.itemDoubleClicked.connect(lambda *_:dialog.accept())
        if dialog.exec()==QDialog.DialogCode.Accepted and items.currentItem():self.media.setCurrentIndex(self.media.findData(items.currentItem().data(Qt.ItemDataRole.UserRole)))
    def filter_models(self,*_):
        old=self.model.currentData();cid=self.camera.currentData();self.model.blockSignals(True);self.model.clear();self.model.addItem('请选择兼容模型',None)
        candidates=[m for m in self.model_rows if cid in m.get('camera_ids',[]) or (self.other_models.isChecked() and m['state']=='EXPERIMENTAL')]
        for m in candidates:self.model.addItem(m['model']+' · '+m['id'][:8]+' · '+m['state'],m['id'])
        idx=self.model.findData(old)
        if idx<=0:idx=next((i for i in range(1,self.model.count()) if next(m for m in candidates if m['id']==self.model.itemData(i))['state']=='EXPERIMENTAL'),0)
        self.model.setCurrentIndex(idx);self.model.blockSignals(False);self.show_model();self.configuration_changed()
    def slider_changed(self,start,end):
        for spin,value in [(self.start_time,start),(self.end_time,end)]:spin.blockSignals(True);spin.setValue(value/1e6);spin.blockSignals(False)
        self.range_label.setText(time_text(start)+' → '+time_text(end)+f' · 长度 {(end-start)/1e6:.3f} 秒');self.configuration_changed()
    def precise_changed(self,handle):
        self.range_slider.set_range(round(self.start_time.value()*1e6),round(self.end_time.value()*1e6),handle=handle);self.slider_changed(self.range_slider.start,self.range_slider.end);self.preview_seek(self.range_slider.start if handle==0 else self.range_slider.end)
    def preview_seek(self,value):
        self.pending_seek=int(value);self.preview_timer.start(130)
    def configuration_changed(self,*_):
        if self.manifest:
            m=self.manifest;p=m['parameters'];identity=m.get('identity',{}).get('configuration',{})
            same=(m['media_id']==self.media.currentData() and m['model_id']==self.model.currentData() and all(p[k]==v for k,v in [('confidence',self.confidence.value()),('start',self.start_time.value()),('end',self.end_time.value())]) and identity.get('device_id')==self.gpu.currentData() and identity.get('camera_context')==self.camera.currentData())
            self.cache_state.setText(('当前配置与已有缓存一致，开始前仍须完整校验。' if same else '当前配置与已有缓存不一致。')+f" 回放实际：{m['model_id'][:8]} · 阈值{p['confidence']} · [{p['start']:.3f},{p['end']:.3f})秒。")
        else:self.cache_state.setText('当前仅选择/预览录像；点击开始才运行AI或校验匹配缓存。')
    def configuration_fingerprint(self):
        return (self.root,self.camera.currentData(),self.media.currentData(),self.model.currentData(),self.gpu.currentData(),self.confidence.value(),self.start_time.value(),self.end_time.value())
    def inference_payload(self):
        if not self.source_ready:raise ValueError('请先选择可解码的视频，等待原片预览加载。')
        if not self.root or not self.media.currentData() or not self.model.currentData() or not self.gpu.currentData():raise ValueError('请选择视频、兼容模型及已检查的NVIDIA GPU。')
        row=next(r for r in self.media_rows if r['id']==self.media.currentData());cid=self.camera.currentData()
        if row.get('camera_id') and cid!=row['camera_id']:raise ValueError('当前录像已有可信摄像头关联，请选择其来源摄像头；不会改写原归属。')
        if not row.get('camera_id') and cid and self.demo_camera_consent!=(row['id'],cid):
            if QMessageBox.question(self,'确认仅用于演示','该视频未关联摄像头。仅将当前摄像头用于本次演示配置，不修改原媒体归属，是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return None
            self.demo_camera_consent=(row['id'],cid)
        if self.end_time.value()-self.start_time.value()<self.range_slider.minimum/1e6-.000001:raise ValueError('片段短于当前视频一个标称帧间隔。')
        return dict(root=self.root,media_id=row['id'],model_id=self.model.currentData(),device_id=self.gpu.currentData(),camera_id=cid,confidence=self.confidence.value(),start=self.start_time.value(),end=self.end_time.value())
    def start(self):self.find_or_start(True)
    def use_cache(self):self.find_or_start(False)
    def find_or_start(self,allow_run):
        if self.job or self.busy:return
        try:payload=self.inference_payload()
        except Exception as exc:self.set_message(str(exc));return
        if payload is None:return
        self.busy=True;root=self.root;generation=self.session_generation;fingerprint=self.configuration_fingerprint();self.watch();self.set_message('正在校验来源、权重与完整缓存身份…')
        def done(path,error):
            if root!=self.root or generation!=self.session_generation:return
            self.busy=False
            if fingerprint!=self.configuration_fingerprint():self.set_message("配置已变化，请重新开始校验。");return
            if error:self.set_message(error);return
            if path:self.set_message('完全匹配缓存，直接回放；未启动GPU。');self.load_run(path,expected=payload)
            elif allow_run:self.submit('p35_offline',payload,'demo')
            else:self.set_message('没有完全匹配缓存，未启动GPU；旧结果可在“检测详情与导出”历史中回看。')
        self.w.runner.run(lambda:self.s.offline.matching_cache(payload),done)
    def render_results(self,*_):
        if not self.manifest:return
        m=self.manifest;source=next((x['name'] for x in self.media_rows if x['id']==m['media_id']),m['media_id']);self.result_rows=[];self.results.blockSignals(True)
        for r in m['frames']:
            if not r['boxes'] and not self.show_all.isChecked():continue
            names='、'.join(sorted({m['classes'][int(b[5])] for b in r['boxes']})) or '无检测目标';confidence='、'.join(f'{b[4]:.3f}' for b in r['boxes']) or '—';self.result_rows.append((r,[f"{r['time_us']/1e6:.3f}",names,confidence,m['model_id'][:8],len(r['boxes']),source]))
        self.results.setRowCount(len(self.result_rows))
        for i,(r,values) in enumerate(self.result_rows):
            for j,value in enumerate(values):
                item=QTableWidgetItem(str(value));item.setToolTip(str(r['boxes']) if j==1 else str(value));self.results.setItem(i,j,item)
        self.results.blockSignals(False)
    def seek_result(self):
        i=self.results.currentRow()
        if self.manifest and 0<=i<len(self.result_rows):self.tabs.setCurrentIndex(1);self.player.seek(self.result_rows[i][0]['cache_time_us'])
