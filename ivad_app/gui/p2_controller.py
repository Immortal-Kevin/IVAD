"""扩展既有主窗口和服务桥，所有耗时P2操作继续走原JobService/AsyncRunner。"""
from PySide6.QtCore import QObject,QTimer,Qt
from PySide6.QtWidgets import QTableWidgetItem
from ivad_app.gui.media_page import MediaPage
from ivad_app.gui.annotation_page import AnnotationPage
from ivad_app.gui.dataset_page import DatasetPage
from ivad_app.gui.label_dialog import LabelDialog

def put_table(table,rows):
    table.blockSignals(True);table.setRowCount(len(rows))
    for i,values in enumerate(rows):
        for j,value in enumerate(values):item=QTableWidgetItem(str(value));item.setToolTip(str(value));table.setItem(i,j,item)
    table.blockSignals(False)

class P2Controller(QObject):
    def __init__(self,window):
        super().__init__(window);self.window=window;self.s=window.s;self.runner=window.runner;self.root=None;self.refreshing=False;self.tracked={};self.jobs_checking=False
        self.media=MediaPage();self.annotation=AnnotationPage(self.s,self.runner);self.dataset=DatasetPage()
        for key,page in [('media',self.media),('annotation',self.annotation),('dataset',self.dataset)]:
            old=window.pages[key];window.stack.removeWidget(old);old.deleteLater();window.pages[key]=page;window.stack.addWidget(page);page.setEnabled(False)
        self.media.import_requested.connect(lambda p:self.submit('p2_import',p));self.media.extract_requested.connect(lambda p:self.submit('p2_extract',p));self.media.capture_requested.connect(self.capture)
        self.media.clip_file_requested.connect(lambda p:self.submit('p2_clip',p));self.media.cancel_clip_requested.connect(lambda:self.cancel_tasks('p2_clip'))
        self.media.load_requested.connect(self.load_media);self.media.relocate_requested.connect(self.relocate);self.media.clip_requested.connect(self.save_clip);self.media.clip_delete_requested.connect(self.delete_clip)
        self.media.check_requested.connect(self.check);self.media.cancel_requested.connect(self.cancel_tasks)
        self.media.labels_requested.connect(self.labels);self.annotation.labels_requested.connect(self.labels);self.annotation.saved.connect(self.refresh)
        self.dataset.preview_requested.connect(self.preview);self.dataset.freeze_requested.connect(lambda p:self.submit('p2_freeze',p));self.dataset.export_requested.connect(lambda p:self.submit('p2_export',p))
        self.timer=QTimer(self);self.timer.setInterval(700);self.timer.timeout.connect(self.watch_jobs);self.timer.start()

    def set_project(self,project):
        root=project.root if project else None
        if root!=self.root:
            self.root=root;self.media.player.stop();self.media.media_id=None;self.media.table.setRowCount(0);self.media.media_rows=[];self.annotation.set_project(root)
            self.dataset.candidates.setRowCount(0);self.dataset.versions.setRowCount(0)
        for page in [self.media,self.annotation,self.dataset]:page.setEnabled(bool(root))
        if root:self.refresh()

    def refresh(self):
        if not self.root or self.refreshing:return
        root=self.root;self.refreshing=True
        def collect():return self.s.media.list(root),self.s.media.frames(root),self.s.annotations.labels(root),self.s.datasets.candidates(root),self.s.datasets.versions(root)
        def done(result,error):
            self.refreshing=False
            if root!=self.root:self.refresh();return
            if error:return
            media,frames,labels,candidates,versions=result;selected=self.media.media_id
            self.media.media_rows=media
            put_table(self.media.table,[[('CLIP · ' if r.get('kind')=='CLIP' else '')+r['name'],r['mode'],r['state'],f"{r['video'].get('duration_us',0)/1000000:.3f}s",r['video'].get('codec',''),f"{r['video'].get('display_width','')}×{r['video'].get('display_height','')}"] for r in media])
            if selected:
                self.media.table.blockSignals(True)
                for i,row in enumerate(media):
                    if row['id']==selected:self.media.table.selectRow(i)
                self.media.table.blockSignals(False)
            self.annotation.set_data(frames,labels)
            old_clip=self.media.clip_label.currentData();self.media.clip_label.clear();self.media.clip_label.addItem('无故障类别',None)
            for label in labels:self.media.clip_label.addItem(label['name'],label['id'])
            self.media.clip_label.setCurrentIndex(max(0,self.media.clip_label.findData(old_clip)))
            selected_frames=set(self.dataset.selected_frames());self.dataset.candidate_rows=candidates;self.dataset.candidates.setRowCount(len(candidates))
            for i,row in enumerate(candidates):
                item=QTableWidgetItem('');item.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if row['id'] in selected_frames else Qt.CheckState.Unchecked);self.dataset.candidates.setItem(i,0,item)
                for j,value in enumerate([row['id'],row['media_id'][:8],f"{row['time_us']/1000000:.3f}",str(row['objects'])+'/'+','.join(row['types']),row['review_status']+'/'+row['image_tag']],1):item=QTableWidgetItem(value);item.setToolTip(value);self.dataset.candidates.setItem(i,j,item)
            self.dataset.version_rows=versions
            put_table(self.dataset.versions,[[r['name'],r['number'],r['summary']['images'],r['summary']['objects'],str(r['summary']['splits']),r['id']] for r in versions])
            existing=self.dataset.existing.currentData();self.dataset.existing.blockSignals(True);self.dataset.existing.clear();self.dataset.existing.addItem('新数据集',None)
            seen=set()
            for version in versions:
                if version['dataset_id'] not in seen:self.dataset.existing.addItem(version['name'],version['dataset_id']);seen.add(version['dataset_id'])
            self.dataset.existing.setCurrentIndex(max(0,self.dataset.existing.findData(existing)));self.dataset.existing.blockSignals(False)
        self.runner.run(collect,done)

    def submit(self,kind,payload):
        if not self.root:self.window.show_error('请先打开项目。');return
        root=self.root;project=self.s.projects.current;value=dict(payload,root=root)
        def done(job,error):
            if not error:self.tracked[job]={'root':root,'kind':kind,'media_id':payload.get('media_id')};self.window.show_notice('P2非AI任务已排队，可在任务中心查看或取消。')
        self.runner.run(lambda:self.s.jobs.submit(kind,project.id,value),done)

    def watch_jobs(self):
        if self.jobs_checking or not self.tracked or self.window.is_closing:return
        ids=list(self.tracked);self.jobs_checking=True
        def done(rows,error):
            self.jobs_checking=False
            if error:return
            for job in rows:
                info=self.tracked.get(job['id'])
                if info and info['root']==self.root and info['kind']=='p2_clip' and job['state'] in {'RUNNING','QUEUED'}:self.media.info.setText(f"视频片段保存：{job['state']} · {job['progress']}%，可在任务中心查看。")
                if job['state'] in {'SUCCEEDED','FAILED','CANCELLED','INTERRUPTED'}:
                    info=self.tracked.pop(job['id'],None)
                    if info and info['root']==self.root:
                        result=job['result'];kind=info['kind']
                        if job['state']!='SUCCEEDED':message=f"任务{job['state']}："+(job['error'] or '已提交的完整资源保留。')
                        elif kind=='p2_import':message=f"导入完成：成功{len(result.get('imported',[]))}、重复{len(result.get('duplicates',[]))}、失败{len(result.get('failed',[]))}。逐项结果见任务日志。"
                        elif kind=='p2_extract':message=f"已生成{result.get('count',0)}张候选图片，可在标注工作台人工审核。"
                        elif kind=='p2_clip':message='视频片段已保存：'+result.get('name','')+'，左侧CLIP资源可播放和抽帧。'
                        elif kind=='p2_freeze':message=f"数据集v{result.get('number')}已冻结：{result.get('images',0)}图片/{result.get('objects',0)}目标。"+'；'.join(result.get('warnings',[])[:2])
                        else:message='数据集导出完成：'+result.get('path','')+'；'.join(result.get('warnings',[]))
                        self.media.info.setText(message);self.dataset.summary.setText(message)
                        if job['state']=='FAILED':self.window.show_error(job['error'])
                        else:self.window.show_notice(message)
                        self.refresh()
            self.update_cancel_buttons()
        self.update_cancel_buttons()
        self.runner.run(lambda:[self.s.jobs.get(job_id) for job_id in ids],done)

    def update_cancel_buttons(self):
        self.media.cancel_button.setEnabled(any(v['root']==self.root and v['kind']=='p2_extract' and v.get('media_id')==self.media.media_id for v in self.tracked.values()))
        self.media.cancel_clip_button.setEnabled(any(v['root']==self.root and v['kind']=='p2_clip' and v.get('media_id')==self.media.media_id for v in self.tracked.values()))
    def cancel_tasks(self,kind='p2_extract'):
        for job,info in list(self.tracked.items()):
            if info['root']==self.root and info['kind']==kind and info.get('media_id')==self.media.media_id:self.runner.run(lambda job=job:self.s.jobs.cancel(job))
    def load_media(self,media_id):
        self.update_cancel_buttons()
        root=self.root
        def done(row,error):
            if error:self.media.player.stop();self.media.info.setText(error);return
            if root==self.root and media_id==self.media.media_id:self.media.load_media(row);self.reload_clips()
        self.runner.run(lambda:self.s.media.get(media_id,root),done)
    def capture(self,media_id,time_us):
        root=self.root
        def done(frame,error):
            if not error and root==self.root:self.media.info.setText('候选帧已保存。');self.refresh()
        self.runner.run(lambda:self.s.media.capture(media_id,time_us,root),done)
    def relocate(self,media_id,path):
        root=self.root
        self.runner.run(lambda:self.s.media.relocate(media_id,path,root),lambda _,error:self.refresh() if not error else None)
    def reload_clips(self):
        root=self.root;media_id=self.media.media_id
        if not media_id:return
        def done(rows,error):
            if error or root!=self.root or media_id!=self.media.media_id:return
            self.media.clip_rows=rows;put_table(self.media.clips,[[r['start_us']/1000000,r['end_us']/1000000,r['tag'],r['label_id'] or '',r['status'],r['revision']] for r in rows])
        self.runner.run(lambda:self.s.annotations.clips(media_id,root),done)
    def save_clip(self,value):
        root=self.root
        def done(row,error):
            if not error:self.media.selected_clip=row;self.media.info.setText('人工片段标签已保存。');self.reload_clips()
        self.runner.run(lambda:self.s.annotations.save_clip(value,root),done)
    def delete_clip(self,clip_id,revision):
        root=self.root
        def done(_,error):
            if not error:self.media.new_clip();self.reload_clips()
        self.runner.run(lambda:self.s.annotations.delete_clip(clip_id,revision,root),done)
    def labels(self):
        if not self.root:return
        dialog=LabelDialog(self.s.annotations,self.runner,self.root,self.refresh,self.window);dialog.exec()
    def preview(self,ids):
        root=self.root
        def done(result,error):
            if not error:self.dataset.summary.setText(f"检查：{result['count']}图片/{result['objects']}目标/{result['groups']}独立组\n"+'；'.join(result['issues']+result['warnings']))
        self.runner.run(lambda:self.s.datasets.preview(ids,root),done)
    def check(self):
        root=self.root
        def done(result,error):
            if not error:self.media.info.setText(str(result));self.window.show_notice('项目数据检查：'+result['status']);self.refresh()
        self.runner.run(lambda:self.s.media.check(root),done)
    def shutdown(self):self.media.player.shutdown()
