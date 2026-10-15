"""Wire incremental project camera, media safety and independent review controls."""
from PySide6.QtCore import Qt,QTimer
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QGridLayout,QGroupBox,QCheckBox,QComboBox,QLabel,QMessageBox,QDialog,QDialogButtonBox
from ivad_app.gui.pages import button,table
from ivad_app.gui.camera_management import CameraPanel

class P2HotfixController:
    def __init__(self,p2):
        self.p2=p2;self.w=p2.window;self.s=p2.s;self.runner=p2.runner;self.root=None;self.camera_busy=False;self.camera_pending=False;self.review_rows=[];self.detail_requested=False
        projects=self.w.pages['projects'];self.tabs=projects.tabs
        self.cameras=CameraPanel(self);projects.camera_layout.addWidget(self.cameras)
        projects.recent.cellDoubleClicked.connect(lambda *_:setattr(self,'detail_requested',True))
        media=p2.media;left=media.table.parentWidget().layout();media.show_inactive=QCheckBox('显示已停用 / 已移除录像');left.addWidget(media.show_inactive);media.show_inactive.toggled.connect(p2.refresh)
        grid=QGridLayout();left.addLayout(grid)
        for i,(text,fn,name) in enumerate([('从项目移除视频',self.remove_media,'media_remove'),('查看下游依赖',self.show_dependencies,'media_dependencies'),('恢复普通列表',self.restore_media,'media_restore')]):grid.addWidget(button(text,fn,name=name),i//2,i%2)
        media.camera_association_requested.connect(self.associate_camera)
        p2.annotation.camera_navigation.connect(self.go_media)
    def set_project(self,project):
        root=project.root if project else None
        if root!=self.root:
            self.cameras.rows=[];self.cameras.table.setRowCount(0);self.cameras.new(force=True)
            self.p2.media.set_cameras([])
        self.root=root;self.cameras.setEnabled(bool(root))
        self.cameras.project.setText(f'所属项目：{project.name}\n项目UUID：{project.id}' if project else '请先打开项目')
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
            old=(self.cameras.record or {}).get('id');self.cameras.rows=rows;self.cameras.loading=True;self.cameras.table.blockSignals(True)
            put_table(self.cameras.table,[[r['details'].get('code',''),r['name'],r['id'],r['details'].get('location',''),'启用' if r['details'].get('enabled',True) else '停用'] for r in rows]);self.cameras.table.blockSignals(False);self.cameras.loading=False
            if old and not self.cameras.dirty:
                for i,r in enumerate(rows):
                    if r['id']==old:self.cameras.load_record(r)
            elif old:self.cameras.restore_selection()
            self.p2.media.set_cameras(rows);self.p2.annotation.load_cameras()
            if self.camera_pending:QTimer.singleShot(0,self.refresh_cameras)
        self.runner.run(lambda:self.s.cameras.list(root),done)
    def save_camera(self,on_success=None):
        if not self.root:return
        root=self.root;panel=self.cameras;record=panel.record;mode=panel.mode;name=panel.fields['name'].text();info={k:panel.fields[k].text() for k in ['code','location','equipment']};info['enabled']=panel.enabled.isChecked();panel.setEnabled(False)
        def done(result,error):
            panel.setEnabled(bool(self.root))
            if root!=self.root:return
            panel.info.setText(error or (result or {}).get('diagnostic_warning') or ('新建摄像头已提交，完整性检查通过。' if mode=='CREATE' else '当前摄像头修改已提交，其他记录保持不变。'))
            if not error:
                panel.load_record(result);self.refresh_cameras();self.p2.refresh()
                if on_success:on_success()
        self.runner.run(lambda:self.s.cameras.save(name,record['id'] if record else None,record['revision'] if record else None,root,details=info,mode=mode),done)
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
        self.refresh_cameras()
