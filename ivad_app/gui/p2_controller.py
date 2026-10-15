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
        super().__init__(window);self.window=window;self.s=window.s;self.runner=window.runner;self.root=None;self.refreshing=False;self.refresh_pending=False;self.tracked={};self.jobs_checking=False
        self.media=MediaPage();self.annotation=AnnotationPage(self.s,self.runner);self.dataset=DatasetPage()
        for key,page in [('media',self.media),('annotation',self.annotation),('dataset',self.dataset)]:
            old=window.pages[key];window.stack.removeWidget(old);old.deleteLater();window.pages[key]=page;window.stack.addWidget(page);page.setEnabled(False)
        self.media.import_requested.connect(lambda p:self.submit('p2_import',p));self.media.extract_requested.connect(lambda p:self.submit('p2_extract',p));self.media.capture_requested.connect(self.capture)
        self.media.clip_file_requested.connect(lambda p:self.submit('p2_clip',p));self.media.cancel_clip_requested.connect(lambda:self.cancel_tasks('p2_clip'))
        self.media.load_requested.connect(self.load_media);self.media.relocate_requested.connect(self.relocate);self.media.clip_requested.connect(self.save_clip);self.media.clip_delete_requested.connect(self.delete_clip)
        self.media.check_requested.connect(self.check);self.media.cancel_requested.connect(self.cancel_tasks)
        self.media.labels_requested.connect(self.labels);self.annotation.labels_requested.connect(self.labels);self.annotation.saved.connect(self.refresh)
        self.dataset.version_check_requested.connect(self.check_dataset_version);self.dataset.split_requested.connect(self.split_preview);self.dataset.batch_requested.connect(self.dataset_batch);self.dataset.preview_requested.connect(self.preview);self.dataset.freeze_requested.connect(lambda p:self.submit('p2_freeze',p));self.dataset.export_requested.connect(lambda p:self.submit('p2_export',p))
        self.timer=QTimer(self);self.timer.setInterval(700);self.timer.timeout.connect(self.watch_jobs);self.timer.start()
        from ivad_app.gui.p2_hotfix_controller import P2HotfixController
        self.hotfix=P2HotfixController(self)

    def set_project(self,project):
        self.hotfix.set_project(project)
        root=project.root if project else None
        if root!=self.root:
            self.root=root;self.media.player.stop();self.media.media_id=None;self.media.selected_media=None;self.media.camera_dirty=False;self.media.table.setRowCount(0);self.media.media_rows=[];self.annotation.set_project(root)
            self.dataset.set_project(root);self.dataset.candidates.setRowCount(0);self.dataset.versions.setRowCount(0)
        for page in [self.media,self.annotation,self.dataset]:page.setEnabled(bool(root))
        if root:self.refresh()

    def refresh(self):
        if not self.root:return
        if self.refreshing:self.refresh_pending=True;return
        root=self.root;self.refreshing=True;self.refresh_pending=False
        def collect():
            frames=self.s.media.frames(root);states=self.s.annotations.frames_status(root)
            for frame in frames:frame.update(states.get(frame['id'],{}))
            return self.s.media.list(root,include_inactive=self.media.show_inactive.isChecked()),frames,self.s.annotations.labels(root),self.s.datasets.screening(root),self.s.datasets.versions(root),self.s.cameras.list(root)
        def done(result,error):
            self.refreshing=False
            if root!=self.root:self.refresh();return
            if error:
                if self.refresh_pending:QTimer.singleShot(0,self.refresh)
                return
            media,frames,labels,candidates,versions,cameras=result;selected=self.media.media_id
            self.media.media_rows=media
            put_table(self.media.table,[[('CLIP · ' if r.get('kind')=='CLIP' else '')+r['name'],r['mode'],r['state'],f"{r['video'].get('duration_us',0)/1000000:.3f}s",r['video'].get('codec',''),f"{r['video'].get('display_width','')}×{r['video'].get('display_height','')}"] for r in media])
            if not selected:
                self.media.table.blockSignals(True);self.media.table.clearSelection();self.media.table.setCurrentCell(-1,-1);self.media.table.blockSignals(False)
            if selected:
                self.media.table.blockSignals(True)
                for i,row in enumerate(media):
                    if row['id']==selected:self.media.table.selectRow(i)
                self.media.table.blockSignals(False)
            self.annotation.set_data(frames,labels)
            self.hotfix.update_data(media,frames)
            old_clip=self.media.clip_label.currentData();self.media.clip_label.clear();self.media.clip_label.addItem('无故障类别',None)
            for label in labels:self.media.clip_label.addItem(label['name'],label['id'])
            self.media.clip_label.setCurrentIndex(max(0,self.media.clip_label.findData(old_clip)))
            self.dataset.set_data(candidates,cameras,labels,versions,self.annotation.camera_id)
            if self.refresh_pending:QTimer.singleShot(0,self.refresh)
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
        self.runner.run(lambda:self.s.datasets.preview(ids,root,admission='experimental'),done)
    def check_dataset_version(self,version_id):
        root=self.root
        def done(result,error):
            if root!=self.root:return
            import json
            self.dataset.detail.setPlainText(error or json.dumps(result,ensure_ascii=False,indent=2));self.dataset.summary.setText(error or '冻结版本检查：'+result['status']+'；来源记录见详情。此检查不代替训练准入或工业审核。')
        self.runner.run(lambda:self.s.datasets.check_version(version_id,root),done)
    def split_preview(self,payload):
        root=self.root
        def done(result,error):
            if root!=self.root:return
            if error:self.dataset.split_detail.setPlainText(error);return
            import json
            self.dataset.split_detail.setPlainText(json.dumps({k:result[k] for k in ['split_status','count','objects','classes','expected_counts','split_counts','source_groups','split_groups','cross_source_groups','near_duplicate_cross_split','issues','warnings']},ensure_ascii=False,indent=2))
        self.runner.run(lambda:self.s.datasets.split_preview(payload['frame_ids'],root,**{k:payload[k] for k in ['strategy','ratios','seed','allow_leakage','admission']}),done)
    def dataset_batch(self,action,ids):
        root=self.root
        if not ids:self.dataset.batch_info.setText('成功0，跳过0，失败0：请先勾选当前筛选图片。');return
        from PySide6.QtWidgets import QMessageBox
        if QMessageBox.question(self.dataset,'确认全局帧状态修改',f'将对所选{len(ids)}张执行'+('剔除' if action=='exclude' else '恢复')+'。历史标注、冻结快照和原文件保留。确认？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.dataset.setEnabled(False)
        def operation():
            counts={'success':0,'skipped':0,'failed':0};errors=[]
            for fid in ids:
                try:
                    preview=self.s.annotations.batch_preview([fid],action,root)
                    result=self.s.annotations.batch_apply(preview,'数据集管理人工'+action,root=root);counts['success']+=result['changed'];counts['skipped']+=len(result['skipped'])
                except Exception as exc:counts['failed']+=1;errors.append(str(exc))
            return counts,errors
        def done(result,error):
            self.dataset.setEnabled(bool(self.root))
            if root!=self.root:return
            if error:self.dataset.batch_info.setText(f'成功0，跳过0，失败{len(ids)}：'+error);return
            c,errors=result;self.dataset.batch_info.setText(f"成功{c['success']}，跳过{c['skipped']}，失败{c['failed']}。"+'；'.join(errors[:2]));self.refresh()
        self.runner.run(operation,done)
    def check(self):
        root=self.root
        def done(result,error):
            if not error:self.media.info.setText(str(result));self.window.show_notice('项目数据检查：'+result['status']);self.refresh()
        self.runner.run(lambda:self.s.media.check(root),done)
    def shutdown(self):self.media.player.shutdown()
