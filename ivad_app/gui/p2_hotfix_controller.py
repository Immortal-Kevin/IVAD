"""Wire incremental project camera, media safety and independent review controls."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QTabWidget,QGroupBox,QCheckBox,QComboBox,QLabel,QMessageBox,QDialog,QDialogButtonBox
from ivad_app.gui.pages import button,table
from ivad_app.gui.camera_management import CameraPanel

class P2HotfixController:
    def __init__(self,p2):
        self.p2=p2;self.w=p2.window;self.s=p2.s;self.runner=p2.runner;self.root=None;self.camera_busy=False;self.camera_pending=False;self.review_rows=[];self.detail_requested=False
        projects=self.w.pages['projects'];tabs=QTabWidget();self.tabs=tabs;details=QWidget();layout=QVBoxLayout(details)
        while projects.layout.count()>2:layout.addItem(projects.layout.takeAt(2))
        tabs.addTab(details,'项目详情');self.cameras=CameraPanel(self);tabs.addTab(self.cameras,'摄像头管理');projects.layout.addWidget(tabs,1)
        projects.recent.cellDoubleClicked.connect(lambda *_:setattr(self,'detail_requested',True))
        layout.insertWidget(0,button('进入项目详情 / 摄像头列表',lambda:tabs.setCurrentIndex(1),name='project_camera_details'))
        media=p2.media;left=media.table.parentWidget().layout();media.show_inactive=QCheckBox('显示已停用 / 已移除录像');left.addWidget(media.show_inactive);media.show_inactive.toggled.connect(p2.refresh)
        grid=QGridLayout();left.addLayout(grid)
        for i,(text,fn,name) in enumerate([('从项目移除视频',self.remove_media,'media_remove'),('查看下游依赖',self.show_dependencies,'media_dependencies'),('恢复普通列表',self.restore_media,'media_restore')]):grid.addWidget(button(text,fn,name=name),i//2,i%2)
        media.camera_association_requested.connect(self.associate_camera)
        p2.annotation.camera_navigation.connect(self.go_media)
        group=QGroupBox('独立人工审核（已标注不等于已审核）');review=QVBoxLayout(group);self.review_table=table(['选择','图片 / 来源','标注完成','详细审核状态']);self.review_table.setMinimumHeight(130);review.addWidget(self.review_table)
        row=QHBoxLayout();review.addLayout(row);self.review_status=QComboBox()
        for text,status in [('DRAFT · 未审核','DRAFT'),('REVIEWED · 人工已审核','REVIEWED'),('APPROVED · 人工批准','APPROVED'),('REJECTED · 审核拒绝','REJECTED')]:self.review_status.addItem(text,status)
        row.addWidget(self.review_status);row.addWidget(button('提交所选图片审核',self.review_selected,name='dataset_review_submit'));self.review_info=QLabel('请选择有实际标注的图片，检查内容后再明确审核。');self.review_info.setWordWrap(True);review.addWidget(self.review_info);p2.dataset.layout.insertWidget(0,group)
    def set_project(self,project):
        root=project.root if project else None
        if root!=self.root:self.cameras.new()
        self.root=root;self.cameras.setEnabled(bool(root));self.review_table.setRowCount(0);self.review_rows=[]
        self.cameras.project.setText(f'所属项目：{project.name}\n项目UUID：{project.id}' if project else '请打开项目')
        if self.detail_requested and root:self.tabs.setCurrentIndex(1);self.detail_requested=False
        self.refresh_cameras()
    def refresh_cameras(self):
        if not self.root:return
        if self.camera_busy:self.camera_pending=True;return
        root=self.root;self.camera_busy=True;self.camera_pending=False
        def done(rows,error):
            self.camera_busy=False
            if root!=self.root:self.refresh_cameras();return
            if error:self.cameras.info.setText(error);return
            from ivad_app.gui.p2_controller import put_table
            old=(self.cameras.record or {}).get('id');self.cameras.rows=rows;self.cameras.table.blockSignals(True)
            put_table(self.cameras.table,[[r['details'].get('code',''),r['name'],r['id'],r['details'].get('location',''),'启用' if r['details'].get('enabled',True) else '停用'] for r in rows]);self.cameras.table.blockSignals(False)
            if old and not self.cameras.dirty:
                for i,r in enumerate(rows):
                    if r['id']==old:self.cameras.table.selectRow(i);self.cameras.select()
            self.p2.media.set_cameras(rows);self.p2.annotation.load_cameras()
            if self.camera_pending:QTimer.singleShot(0,self.refresh_cameras)
        self.runner.run(lambda:self.s.cameras.list(root),done)
    def save_camera(self):
        if not self.root:return
        root=self.root;panel=self.cameras;record=panel.record;name=panel.fields['name'].text();info={k:panel.fields[k].text() for k in ['code','location','equipment']};info['enabled']=panel.enabled.isChecked();panel.setEnabled(False)
        def done(result,error):
            panel.setEnabled(bool(self.root))
            if root!=self.root:return
            panel.info.setText(error or '已保存项目摄像头，UUID及历史关联保留。')
            if not error:panel.record=result;panel.dirty=False;self.refresh_cameras();self.p2.refresh()
        self.runner.run(lambda:self.s.cameras.save(name,record['id'] if record else None,record['revision'] if record else None,root,details=info),done)
    @staticmethod
    def impact(preview):
        names={'clips':'片段','frames':'抽帧图片','annotations':'标注','annotation_revisions':'标注历史','dataset_versions':'冻结数据集','training_runs':'训练记录','model_versions':'模型版本','rois':'ROI','clip_labels':'片段标签','active_jobs':'运行/排队任务'}
        return '录像：'+preview['name']+'\n'+'；'.join(f'{names[k]} {v}' for k,v in preview['counts'].items())
    def associate_camera(self,mid,cid,old):
        if not self.p2.annotation.flush(lambda:self.associate_camera(mid,cid,old)):return
        root=self.root
        def confirm(preview,error):
            if error or root!=self.root:
                if error:self.p2.media.info.setText(error)
                return
            if QMessageBox.question(self.p2.media,'确认摄像头影响范围',self.impact(preview)+'\n将更新本录像及继承关联的片段；已有不同/显式片段关联保留。旧冻结快照与训练结果不改。是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
            def done(result,error):
                if root!=self.root:return
                self.p2.media.info.setText(error or f"关联已保存；保留显式片段{len(result['preserved_explicit_clips'])}条。")
                if not error:
                    if self.p2.media.selected_media and self.p2.media.selected_media['id']==mid:self.p2.media.camera_dirty=False;self.p2.media.selected_media['camera_id']=cid
                    self.refresh_cameras();self.p2.refresh()
                    if self.p2.annotation.frame_id and self.p2.annotation.media_id in result['media_ids']:self.p2.annotation.request_load(self.p2.annotation.frame_id,force=True)
            self.runner.run(lambda:self.s.cameras.associate(mid,cid,old,root,expected_signature=preview['signature']),done)
        self.runner.run(lambda:self.s.media.dependencies(mid,root),confirm)
    def go_media(self,mid):
        def go():
            self.w.show_page('media')
            for i,r in enumerate(self.p2.media.media_rows):
                if r['id']==mid:self.p2.media.table.selectRow(i);break
        if self.p2.annotation.flush(go):go()
    def show_dependencies(self):
        mid=self.p2.media.media_id;root=self.root
        if mid:self.runner.run(lambda:self.s.media.dependencies(mid,root),lambda p,e:QMessageBox.information(self.p2.media,'下游依赖',e or self.impact(p)))
    def remove_media(self):
        mid=self.p2.media.media_id;root=self.root
        if not mid:return
        def confirm(preview,error):
            if error or root!=self.root:
                if error:self.p2.media.info.setText(error)
                return
            dialog=QDialog(self.p2.media);dialog.setWindowTitle('从项目移除视频' if not preview['has_dependencies'] else '有下游依赖：仅允许隐藏/停用');layout=QVBoxLayout(dialog);label=QLabel(self.impact(preview)+'\nREFERENCE外部原文件绝不删除。存在引用时仅隐藏，不级联删除。');label.setWordWrap(True);layout.addWidget(label)
            cleanup=QCheckBox('明确清理项目内COPY副本（不删除原始录像）');cleanup.setEnabled(not preview['has_dependencies'] and preview['mode']=='COPY');layout.addWidget(cleanup)
            buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Ok|QDialogButtonBox.StandardButton.Cancel);buttons.accepted.connect(dialog.accept);buttons.rejected.connect(dialog.reject);layout.addWidget(buttons)
            if dialog.exec()!=QDialog.DialogCode.Accepted:return
            def done(result,error):
                if root!=self.root:return
                self.p2.media.info.setText(error or ('媒体列表已更新；副本清理待完成，保留隔离文件。' if result.get('cleanup_pending') else '媒体列表已更新，历史引用/外部原录像保留。'))
                if not error:self.p2.media.player.stop();self.p2.media.media_id=None;self.p2.media.selected_media=None;self.p2.refresh()
            self.runner.run(lambda:self.s.media.remove(mid,root,hide_only=preview['has_dependencies'],cleanup_copy=cleanup.isChecked(),expected_signature=preview['signature']),done)
        self.runner.run(lambda:self.s.media.dependencies(mid,root),confirm)
    def restore_media(self):
        mid=self.p2.media.media_id;root=self.root
        if mid:self.runner.run(lambda:self.s.media.remove(mid,root,restore=True),lambda _,e:(self.p2.media.info.setText(e or '已恢复普通列表。'),self.p2.refresh()))
    def update_data(self,media,frames):
        self.refresh_cameras();selected={self.review_rows[i]['id'] for i in range(len(self.review_rows)) if self.review_table.item(i,0) and self.review_table.item(i,0).checkState()==Qt.CheckState.Checked}
        self.review_rows=[f for f in frames if f.get('annotation_revision',0)>0];self.review_table.setRowCount(len(self.review_rows))
        from PySide6.QtWidgets import QTableWidgetItem
        for i,f in enumerate(self.review_rows):
            check=QTableWidgetItem();check.setFlags(Qt.ItemFlag.ItemIsEnabled|Qt.ItemFlag.ItemIsUserCheckable);check.setCheckState(Qt.CheckState.Checked if f['id'] in selected else Qt.CheckState.Unchecked);self.review_table.setItem(i,0,check)
            for j,value in enumerate([f['id'][:8]+' · '+f.get('media_name',''),('已剔除（无效）' if f['processing_state']=='EXCLUDED' else '已标注' if f['completion_state']=='LABELED' else '未标注'),f['review_status']+(' · 内容待重新审核' if f['review_stale'] else '')],1):self.review_table.setItem(i,j,QTableWidgetItem(value))
    def review_selected(self):
        root=self.root;expected={f['id']:f['annotation_revision'] for i,f in enumerate(self.review_rows) if self.review_table.item(i,0).checkState()==Qt.CheckState.Checked};status=self.review_status.currentData()
        if not expected:self.review_info.setText('请先勾选图片，人工核查内容。');return
        if QMessageBox.question(self.p2.dataset,'人工审核确认',f'确认已逐张检查所选{len(expected)}张，更新底层审核为{status}？“已标注”不会自动审核。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        self.runner.run(lambda:self.s.annotations.review_frames(expected,status,root),lambda _,e:(self.review_info.setText(e or '人工审核已保存，旧记录保留。'),self.p2.refresh()))
