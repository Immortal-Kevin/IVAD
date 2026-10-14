import copy
from PySide6.QtCore import Qt,QTimer,Signal
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QListWidget,QComboBox,QLabel,QSplitter,QWidget,QMessageBox,QScrollArea
from ivad_app.gui.pages import Page,button
from ivad_app.gui.annotation_canvas import AnnotationCanvas
from ivad_app.gui.video_player import qimage

class AnnotationPage(Page):
    labels_requested=Signal()
    saved=Signal()
    def __init__(self,services,runner):
        super().__init__('标注工作台','人工真值 · 原始图片像素坐标 · ROI独立存储；多边形右键/Enter完成，Esc取消。')
        self.s,self.runner=services,runner;self.root=None;self.frame_id=None;self.revision=self.roi_revision=0;self.dirty=self.saving=False;self.pending=None;self.save_error=False;self.roi_snapshot=[];self.loading=False;self.loaded_camera_roi=False;self.load_serial=0;self.roi_notice=''
        toolbar=QHBoxLayout();self.tool=QComboBox();self.tool.setObjectName('annotation_tool')
        for text,value in [('选择/移动/顶点编辑','select'),('矩形框','box'),('多边形','polygon'),('矩形ROI','roi_box'),('多边形ROI','roi_polygon')]:self.tool.addItem(text,value)
        toolbar.addWidget(self.tool);toolbar.addWidget(button('适应窗口',lambda:self.canvas.fit()));toolbar.addWidget(button('撤销',lambda:self.canvas.undo(),name='annotation_undo'));toolbar.addWidget(button('重做',lambda:self.canvas.redo(),name='annotation_redo'))
        self.delete_button=button('删除选中',lambda:self.canvas.delete_selected(),name='annotation_delete');self.delete_button.setEnabled(False);toolbar.addWidget(self.delete_button)
        toolbar.addWidget(button('故障类型…',self.labels_requested.emit,name='annotation_labels'));self.layout.addLayout(toolbar)
        splitter=QSplitter();self.frames=QListWidget();self.frames.setObjectName('annotation_frames');self.frames.setMinimumWidth(120);self.frames.setMaximumWidth(220)
        browser=QWidget();browser.setMaximumWidth(220);browser_layout=QVBoxLayout(browser);browser_layout.setContentsMargins(0,0,0,0)
        self.media_filter=QComboBox();self.media_filter.addItem('全部来源',None);self.media_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.addWidget(self.media_filter);browser_layout.addWidget(self.frames);splitter.addWidget(browser);self.frame_rows=[]
        self.canvas=AnnotationCanvas();splitter.addWidget(self.canvas)
        props=QWidget();props.setObjectName('annotation_properties');props.setStyleSheet('QWidget#annotation_properties { background: #ffffff; }');props.setMinimumWidth(150);props.setMaximumWidth(210);p=QVBoxLayout(props)
        self.classes=QComboBox();self.classes.setObjectName('annotation_class');self.classes.currentIndexChanged.connect(self.class_changed)
        self.review=QComboBox();self.review.setObjectName('annotation_review')
        for value in ['DRAFT','REVIEWED','APPROVED','REJECTED']:self.review.addItem(value,value)
        self.image_tag=QComboBox();self.image_tag.setObjectName('image_tag')
        for text,value in [('未知/待确认','UNKNOWN'),('正常','NORMAL'),('异常','ABNORMAL')]:self.image_tag.addItem(text,value)
        self.image_label=QComboBox();self.image_label.addItem('无整帧故障类别',None)
        self.roi_scope=QComboBox();self.roi_scope.addItems(['ROI关联当前视频','ROI关联摄像头'])
        self.objects=QListWidget();self.objects.setMaximumHeight(150);self.objects.currentRowChanged.connect(self.select_object)
        for text,widget in [('目标类别',self.classes),('审核状态',self.review),('整帧标签',self.image_tag),('整帧故障类别',self.image_label),('ROI作用域',self.roi_scope),('当前对象',self.objects)]:p.addWidget(QLabel(text));p.addWidget(widget)
        self.save_button=button('保存标注',self.save_now,True,'save_annotation');p.addWidget(self.save_button);p.addWidget(button('放弃修改并重载',self.reload_discard));p.addStretch()
        props.setMinimumHeight(560);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(props);scroll.setMinimumWidth(170);scroll.setMaximumWidth(230);splitter.addWidget(scroll);splitter.setSizes([140,700,200]);self.layout.addWidget(splitter,1)
        row=QHBoxLayout();row.addWidget(button('上一张',lambda:self.navigate(-1)));row.addWidget(button('下一张',lambda:self.navigate(1)));self.info=QLabel('请打开项目并抽帧。');self.info.setWordWrap(True);row.addWidget(self.info,1);self.layout.addLayout(row)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(350);self.debounce.timeout.connect(self.save_now)
        self.canvas.changed.connect(self.mark_dirty);self.canvas.selected.connect(self.selection);self.canvas.error.connect(self.info.setText)
        self.tool.currentIndexChanged.connect(lambda:self.canvas.set_tool(self.tool.currentData()))
        self.frames.currentRowChanged.connect(self.select_frame)
        for widget in [self.review,self.image_tag,self.image_label]:widget.currentIndexChanged.connect(self.mark_dirty)
        self.roi_scope.currentIndexChanged.connect(lambda:self.request_load(self.frame_id,force=True) if self.frame_id else None)

    def set_project(self,root):
        self.root=root;self.frame_id=None;self.dirty=False;self.saving=False;self.pending=None;self.save_error=False;self.debounce.stop();self.frames.clear();self.frame_rows=[];self.canvas.pixmap=None;self.canvas.shapes=[];self.canvas.render();self.setEnabled(bool(root))
    def set_data(self,frames,labels):
        self.frame_rows=frames;selected_filter=self.media_filter.currentData();self.media_filter.blockSignals(True);self.media_filter.clear();self.media_filter.addItem('全部来源',None)
        for mid in dict.fromkeys(r['media_id'] for r in frames):self.media_filter.addItem('录像 '+mid[:8],mid)
        self.media_filter.setCurrentIndex(max(0,self.media_filter.findData(selected_filter)));self.media_filter.blockSignals(False);self.filter_frames()
        old=self.classes.currentData();old_image=self.image_label.currentData()
        self.classes.blockSignals(True);self.image_label.blockSignals(True);self.classes.clear();self.image_label.clear();self.image_label.addItem('无整帧故障类别',None)
        for label in labels:
            text=label['name']+('（停用）' if not label['enabled'] else '')
            self.classes.addItem(text,label['id']);self.image_label.addItem(text,label['id'])
        self.classes.setCurrentIndex(max(0,self.classes.findData(old)));self.image_label.setCurrentIndex(max(0,self.image_label.findData(old_image)));self.classes.blockSignals(False);self.image_label.blockSignals(False)
        self.canvas.label_names={r['id']:r['name'] for r in labels};self.canvas.label_id=self.classes.currentData()
        if not self.frame_id and self.frames.count():self.frames.setCurrentRow(0)

    def filter_frames(self):
        selected=self.frame_id;self.frames.blockSignals(True);self.frames.clear();mid=self.media_filter.currentData()
        source_order={value:i for i,value in enumerate(dict.fromkeys(r['media_id'] for r in self.frame_rows))}
        for row in sorted(self.frame_rows,key=lambda r:(source_order[r['media_id']],r['time_us'],r['id'])):
            if mid and row['media_id']!=mid:continue
            self.frames.addItem(f"{row['time_us']/1000000:.3f}s · {row['id'][:8]}"+(' Missing' if row['state']=='MISSING' else ''));self.frames.item(self.frames.count()-1).setData(Qt.ItemDataRole.UserRole,row['id'])
        index=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==selected),-1)
        self.frames.setCurrentRow(index);self.frames.blockSignals(False)
        if index<0 and self.frames.count():self.frames.setCurrentRow(0)

    def select_frame(self,index):
        if index>=0:self.request_load(self.frames.item(index).data(Qt.ItemDataRole.UserRole))
    def navigate(self,delta):
        row=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==self.frame_id),self.frames.currentRow())+delta
        if 0<=row<self.frames.count():self.frames.setCurrentRow(row)
    def request_load(self,frame_id,force=False):
        if not frame_id or (frame_id==self.frame_id and not force):return
        if self.save_error:
            dialog=QMessageBox(self);dialog.setWindowTitle('当前标注尚未保存');dialog.setText('保存失败。请选择保存后继续、不保存继续或取消。')
            save=dialog.addButton('保存后继续',QMessageBox.ButtonRole.AcceptRole)
            discard=dialog.addButton('不保存继续',QMessageBox.ButtonRole.DestructiveRole)
            dialog.addButton('取消',QMessageBox.ButtonRole.RejectRole);dialog.exec()
            if dialog.clickedButton()==save:
                self.pending=lambda:self.request_load(frame_id,force=force);self.save_error=False;self.save_now();return
            if dialog.clickedButton()==discard:self.dirty=False;self.save_error=False;self.debounce.stop()
            else:self.restore_selection();return
        if self.dirty or self.saving:
            self.pending=lambda:self.request_load(frame_id,force=force);self.save_now();return
        root=self.root;camera_roi=self.roi_scope.currentIndex()==1;self.loading=True;self.load_serial+=1;serial=self.load_serial;self.canvas.setEnabled(False)
        for widget in [self.review,self.image_tag,self.image_label,self.classes,self.roi_scope]:widget.setEnabled(False)
        def operation():
            frame,image=self.s.media.frame_image(frame_id,root);data=self.s.annotations.load(frame_id,root,camera_roi);return image,data
        def done(result,error):
            if serial!=self.load_serial or root!=self.root:return
            self.loading=False
            self.canvas.setEnabled(True)
            for widget in [self.review,self.image_tag,self.image_label,self.classes,self.roi_scope]:widget.setEnabled(True)
            if error:
                self.roi_scope.blockSignals(True);self.roi_scope.setCurrentIndex(int(self.loaded_camera_roi));self.roi_scope.blockSignals(False);self.restore_selection();self.info.setText(error);return
            self.loaded_camera_roi=result[1]['camera_roi']
            image,data=result;self.frame_id=frame_id;self.revision=data['revision'];self.roi_revision=data['roi_revision'];self.roi_snapshot=copy.deepcopy(data['roi_objects']);self.save_error=False
            self.roi_scope.blockSignals(True);self.roi_scope.setCurrentIndex(int(self.loaded_camera_roi));self.roi_scope.model().item(1).setEnabled(data['camera_available']);self.roi_scope.blockSignals(False)
            self.roi_notice=data['notice'];self.roi_scope.setToolTip(data['notice'] or 'ROI 为可选辅助信息，与目标标注及整帧标签独立。')
            self.canvas.set_image(qimage(image));self.canvas.set_shapes(data['payload']['objects']+data['roi_objects']);self.canvas.label_id=self.classes.currentData()
            for widget,value in [(self.review,data['status']),(self.image_tag,data['payload']['image_tag']),(self.image_label,data['payload'].get('image_label_id'))]:widget.blockSignals(True);widget.setCurrentIndex(max(0,widget.findData(value)));widget.blockSignals(False)
            self.dirty=False;self.update_objects();self.restore_selection();self.info.setText(f"PTS {data['frame']['pts_us']} µs · {image.width}×{image.height} · 标注修订 {self.revision} · Human Generated\n"+data['notice'])
        self.runner.run(operation,done)

    def restore_selection(self):
        self.frames.blockSignals(True)
        self.frames.setCurrentRow(next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==self.frame_id),-1))
        self.frames.blockSignals(False)

    def mark_dirty(self,*args):
        if not self.frame_id or self.loading:return
        self.dirty=True;self.save_error=False;self.info.setText('有修改，自动保存中…');self.update_objects();self.debounce.start()
    def update_objects(self):
        self.objects.blockSignals(True);self.objects.clear()
        for obj in self.canvas.shapes:self.objects.addItem(obj['kind']+' · '+self.canvas.label_names.get(obj.get('label_id'),'ROI'))
        self.objects.setCurrentRow(self.canvas.selected_index if self.canvas.selected_index is not None else -1);self.objects.blockSignals(False)
    def select_object(self,index):
        self.canvas.selected_index=index if index>=0 else None;self.canvas.render();self.selection(self.canvas.shapes[index] if 0<=index<len(self.canvas.shapes) else None)
    def selection(self,obj):
        self.delete_button.setEnabled(obj is not None)
        if obj and obj.get('label_id'):
            self.classes.blockSignals(True);self.classes.setCurrentIndex(max(0,self.classes.findData(obj['label_id'])));self.classes.blockSignals(False);self.canvas.label_id=self.classes.currentData()
        self.update_objects()
    def class_changed(self,*args):
        self.canvas.label_id=self.classes.currentData();index=self.canvas.selected_index
        if index is not None and index<len(self.canvas.shapes) and not self.canvas.shapes[index]['kind'].startswith('roi_'):
            self.canvas.shapes[index]['label_id']=self.canvas.label_id;self.canvas.commit()

    def save_now(self):
        self.debounce.stop()
        if self.saving:return
        if not self.dirty:
            if self.pending:callback=self.pending;self.pending=None;callback()
            return
        if not self.root or not self.frame_id:return
        root,frame_id=self.root,self.frame_id;shapes=copy.deepcopy(self.canvas.shapes);rois=[o for o in shapes if o['kind'].startswith('roi_')]
        payload={'objects':[o for o in shapes if not o['kind'].startswith('roi_')],'image_tag':self.image_tag.currentData(),'image_label_id':self.image_label.currentData()}
        status=self.review.currentData();revision=self.revision;roi_revision=self.roi_revision;camera=self.loaded_camera_roi;changed_roi=rois if rois!=self.roi_snapshot else None
        self.saving=True;self.dirty=False
        def done(result,error):
            self.saving=False
            if root!=self.root or frame_id!=self.frame_id:return
            if error:self.dirty=True;self.save_error=True;self.pending=None;self.restore_selection();self.info.setText('保存失败：'+error+'；可重试保存，或切换图片时明确选择不保存继续。');return
            self.revision=result['revision'];self.roi_revision=result['roi_revision'];self.roi_snapshot=rois;self.info.setText(f'已保存 · 修订 {self.revision} · {status}\n'+self.roi_notice);self.saved.emit()
            if self.dirty:self.save_now()
            elif self.pending:callback=self.pending;self.pending=None;callback()
        self.runner.run(lambda:self.s.annotations.save(frame_id,payload,status,revision,changed_roi,roi_revision,camera,root),done)
    def flush(self,callback):
        if self.save_error:self.info.setText('标注保存失败，请修正或明确放弃本次修改后再切换/退出。');return False
        if self.dirty or self.saving:self.pending=callback;self.save_now();return False
        return True
    def reload_discard(self):
        if not self.frame_id:return
        if self.dirty and QMessageBox.question(self,'放弃未保存修改','是否放弃本次未保存的标注修改并重新载入？',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Discard:return
        if self.saving:self.info.setText('请等待正在执行的保存完成。');return
        self.dirty=False;self.save_error=False;self.request_load(self.frame_id,force=True)
