import copy
from PySide6.QtCore import Qt,QTimer,Signal,QItemSelectionModel
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QListWidget,QComboBox,QLabel,QSplitter,QWidget,QMessageBox,QScrollArea,QCheckBox,QInputDialog,QLineEdit,QAbstractItemView
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QShortcut,QKeySequence
from ivad_app.gui.pages import Page,button
from ivad_app.gui.annotation_canvas import AnnotationCanvas
from ivad_app.gui.video_player import qimage

class AnnotationPage(Page):
    labels_requested=Signal()
    saved=Signal()
    def __init__(self,services,runner):
        super().__init__('标注工作台','人工真值 · 原始图片像素坐标 · ROI独立存储；多边形右键/Enter完成，Esc取消。')
        self.s,self.runner=services,runner;self.root=None;self.frame_id=None;self.revision=self.roi_revision=0;self.dirty=self.saving=False;self.pending=None;self.save_error=False;self.roi_snapshot=[];self.loading=False;self.loaded_camera_roi=False;self.load_serial=0;self.roi_notice=''
        self.current_tag='UNKNOWN';self.loaded_payload={};self.normal_confirmed=False;self.media_id=None;self.camera_id=None;self.camera_records=[];self.batch_busy=False;self.checked_ids=set();self.excluded=False
        toolbar=QHBoxLayout();self.tool=QComboBox();self.tool.setObjectName('annotation_tool')
        for text,value in [('选择/移动/顶点编辑','select'),('矩形框','box'),('多边形','polygon'),('矩形ROI','roi_box'),('多边形ROI','roi_polygon')]:self.tool.addItem(text,value)
        toolbar.addWidget(self.tool);toolbar.addWidget(button('适应窗口',lambda:self.canvas.fit()));toolbar.addWidget(button('撤销',lambda:self.canvas.undo(),name='annotation_undo'));toolbar.addWidget(button('重做',lambda:self.canvas.redo(),name='annotation_redo'))
        self.delete_button=button('删除选中',lambda:self.canvas.delete_selected(),name='annotation_delete');self.delete_button.setEnabled(False);toolbar.addWidget(self.delete_button)
        toolbar.addWidget(button('故障类型…',self.labels_requested.emit,name='annotation_labels'));self.layout.addLayout(toolbar)
        splitter=QSplitter();self.frames=QListWidget();self.frames.setObjectName('annotation_frames');self.frames.setMinimumWidth(190);self.frames.setMaximumWidth(280);self.frames.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        browser=QWidget();browser.setMaximumWidth(280);browser_layout=QVBoxLayout(browser);browser_layout.setContentsMargins(0,0,0,0)
        self.media_filter=QComboBox();self.media_filter.addItem('全部来源',None);self.media_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.addWidget(self.media_filter);browser_layout.addWidget(self.frames);splitter.addWidget(browser);self.frame_rows=[]
        self.state_filter=QComboBox();self.state_filter.setObjectName('frame_state_filter')
        for text,value in [('有效帧（默认）','ACTIVE'),('全部处理状态','ALL'),('仅未处理','UNPROCESSED'),('仅正常','NORMAL'),('仅异常','ABNORMAL'),('仅待复核','UNCERTAIN'),('仅已剔除','EXCLUDED'),('仅冲突','CONFLICT')]:self.state_filter.addItem(text,value)
        self.state_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.insertWidget(1,self.state_filter)
        self.frames.itemChanged.connect(self.check_changed);self.frames.itemSelectionChanged.connect(self.update_checked_count)
        self.selected_count=QLabel('已选0张');browser_layout.addWidget(self.selected_count)
        actions=[('全选筛选结果',lambda:self.select_checked(), 'frames_select_all'),('选未处理帧',lambda:self.select_checked(True),'frames_select_unprocessed'),('取消选择',self.clear_checked,'frames_clear_selection'),('批量标记正常',lambda:self.batch_action('normal'),'frames_batch_normal'),('批量剔除',lambda:self.batch_action('exclude'),'frames_batch_exclude'),('批量恢复',lambda:self.batch_action('restore'),'frames_batch_restore')]
        for i in range(0,len(actions),2):
            row=QHBoxLayout();row.setSpacing(4)
            for text,handler,name in actions[i:i+2]:
                b=button(text,handler,name=name);b.setStyleSheet('QPushButton { padding:6px 4px; }');row.addWidget(b)
            browser_layout.addLayout(row)
        self.frames.setMinimumHeight(120)
        self.canvas=AnnotationCanvas();splitter.addWidget(self.canvas)
        props=QWidget();props.setObjectName('annotation_properties');props.setStyleSheet('QWidget#annotation_properties { background: #ffffff; }');props.setMinimumWidth(230);props.setMaximumWidth(310);p=QVBoxLayout(props)
        self.classes=QComboBox();self.classes.setObjectName('annotation_class');self.classes.currentIndexChanged.connect(self.class_changed)
        self.review=QComboBox();self.review.setObjectName('annotation_review')
        for value in ['DRAFT','REVIEWED','APPROVED','REJECTED']:self.review.addItem(value,value)
        self.image_tag=QComboBox();self.image_tag.setObjectName('image_tag')
        for text,value in [('未知/待确认','UNKNOWN'),('正常','NORMAL'),('异常','ABNORMAL')]:self.image_tag.addItem(text,value)
        self.image_label=QComboBox();self.image_label.addItem('无整帧故障类别',None)
        self.roi_scope=QComboBox();self.roi_scope.addItems(['ROI关联当前视频','ROI关联摄像头'])
        self.objects=QListWidget();self.objects.setMaximumHeight(150);self.objects.currentRowChanged.connect(self.select_object)
        for text,widget in [('目标类别',self.classes),('审核状态',self.review),('整帧标签',self.image_tag),('整帧故障类别',self.image_label),('ROI作用域',self.roi_scope),('当前对象',self.objects)]:p.addWidget(QLabel(text));p.addWidget(widget)
        p.addWidget(QLabel('当前图片处理'))
        self.reason=QLineEdit();self.reason.setPlaceholderText('无法判断原因（可选）');p.addWidget(self.reason);self.reason.textEdited.connect(self.mark_dirty)
        self.auto_next=QCheckBox('快捷保存后自动进入下一张');self.auto_next.setChecked(True);p.addWidget(self.auto_next)
        self.runner.run(lambda:self.s.settings.get('annotation_ux',{'auto_next':True}),lambda value,error:self.auto_next.setChecked(value.get('auto_next',True)) if not error else None)
        self.auto_next.toggled.connect(lambda value:self.runner.run(lambda:self.s.settings.set('annotation_ux',{'auto_next':value})))
        self.quick_button=button('保存待复核并进入下一张',self.quick_save,True,'annotation_quick_save');p.addWidget(self.quick_button)
        self.auto_next.toggled.connect(self.update_quick_text)
        p.addWidget(button('剔除当前帧并进入下一张',lambda:self.batch_action('exclude',True),name='frame_exclude'))
        p.addWidget(button('恢复当前帧',lambda:self.batch_action('restore',True),name='frame_restore'))
        self.save_button=button('保存标注',self.save_now,True,'save_annotation');p.addWidget(self.save_button);p.addWidget(button('放弃修改并重载',self.reload_discard));p.addStretch()
        p.addWidget(button('恢复历史标注…',self.restore_history,name='annotation_restore_history'))
        p.addWidget(QLabel('所属摄像头（录像及其片段共用）'));self.camera_choice=QComboBox();self.camera_choice.setObjectName('annotation_camera');self.camera_choice.addItem('未关联摄像头',None);p.addWidget(self.camera_choice)
        for text,handler,name in [('新建摄像头…',lambda:self.edit_camera(False),'camera_create'),('编辑摄像头名称…',lambda:self.edit_camera(True),'camera_rename'),('保存摄像头关联',self.associate_camera,'camera_associate')]:p.addWidget(button(text,handler,name=name))
        props.setMinimumHeight(920);scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(props);scroll.setMinimumWidth(250);scroll.setMaximumWidth(330);splitter.addWidget(scroll);splitter.setSizes([220,650,290]);self.layout.addWidget(splitter,1)
        row=QHBoxLayout();row.addWidget(button('上一张',lambda:self.navigate(-1)));row.addWidget(button('下一张',lambda:self.navigate(1)));self.info=QLabel('请打开项目并抽帧。');self.info.setWordWrap(True);row.addWidget(self.info,1);self.layout.addLayout(row)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(350);self.debounce.timeout.connect(self.save_now)
        self.canvas.changed.connect(self.mark_dirty);self.canvas.selected.connect(self.selection);self.canvas.error.connect(self.info.setText)
        self.tool.currentIndexChanged.connect(lambda:self.canvas.set_tool(self.tool.currentData()))
        self.frames.currentRowChanged.connect(self.select_frame)
        for widget in [self.review,self.image_label]:widget.currentIndexChanged.connect(self.mark_dirty)
        self.image_tag.currentIndexChanged.connect(self.tag_changed)
        self.roi_scope.currentIndexChanged.connect(lambda:self.request_load(self.frame_id,force=True) if self.frame_id else None)
        self.save_shortcut=QShortcut(QKeySequence('Ctrl+S'),self);self.save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.save_shortcut.activated.connect(self.save_now)
        self.quick_shortcut=QShortcut(QKeySequence('Ctrl+Return'),self);self.quick_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.quick_shortcut.activated.connect(self.quick_save)

    def set_project(self,root):
        self.root=root;self.frame_id=None;self.dirty=False;self.saving=False;self.pending=None;self.save_error=False;self.debounce.stop();self.checked_ids.clear();self.frames.clear();self.frame_rows=[];self.canvas.pixmap=None;self.canvas.shapes=[];self.canvas.render();self.setEnabled(bool(root))
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
        self.load_cameras()

    def filter_frames(self):
        selected=self.frame_id;self.frames.blockSignals(True);self.frames.clear();mid=self.media_filter.currentData()
        source_order={value:i for i,value in enumerate(dict.fromkeys(r['media_id'] for r in self.frame_rows))}
        for row in sorted(self.frame_rows,key=lambda r:(source_order[r['media_id']],r['time_us'],r['id'])):
            if mid and row['media_id']!=mid:continue
            state=row.get('processing_state','UNPROCESSED');flt=self.state_filter.currentData()
            if (flt=='ACTIVE' and state=='EXCLUDED') or (flt not in {'ACTIVE','ALL'} and flt!=state):continue
            self.frames.addItem(f"{row['time_us']/1000000:.3f}s · {row['id'][:8]}"+(' Missing' if row['state']=='MISSING' else ''));self.frames.item(self.frames.count()-1).setData(Qt.ItemDataRole.UserRole,row['id'])
            item=self.frames.item(self.frames.count()-1);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if row['id'] in self.checked_ids else Qt.CheckState.Unchecked)
            names={'UNPROCESSED':('○','未处理','#7c8794'),'NORMAL':('✓','已确认正常','#1a874b'),'ABNORMAL':('!','已标注异常','#c63737'),'UNCERTAIN':('?','无法判断/待复核','#a67b00'),'EXCLUDED':('×','已剔除（文件保留）','#7c8794'),'CONFLICT':('!','数据冲突','#c63737')}
            symbol,title,color=names[state];pix=QPixmap(22,22);pix.fill(Qt.GlobalColor.transparent);painter=QPainter(pix);painter.setPen(QColor(color));font=painter.font();font.setPixelSize(20);painter.setFont(font);painter.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,symbol);painter.end();item.setIcon(QIcon(pix));item.setToolTip(title+'；审核：'+row.get('review_status','DRAFT'))
        index=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==selected),-1)
        self.frames.setCurrentRow(index);self.frames.blockSignals(False)
        if index<0 and self.frames.count():self.frames.setCurrentRow(0)
        if not self.frames.count():self.info.setText('当前筛选没有图片；可切换“全部处理状态”或“仅已剔除”查看。')
        self.update_checked_count()

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
            self.current_tag=data['payload']['image_tag'];self.loaded_payload=copy.deepcopy(data['payload']);self.normal_confirmed=False;self.media_id=data['frame']['media_id'];self.camera_id=data['frame']['camera_id'];self.excluded=data['processing_state']=='EXCLUDED'
            self.roi_scope.blockSignals(True);self.roi_scope.setCurrentIndex(int(self.loaded_camera_roi));self.roi_scope.model().item(1).setEnabled(data['camera_available']);self.roi_scope.blockSignals(False)
            self.roi_notice=data['notice'];self.roi_scope.setToolTip(data['notice'] or 'ROI 为可选辅助信息，与目标标注及整帧标签独立。')
            self.canvas.set_image(qimage(image));self.canvas.set_shapes(data['payload']['objects']+data['roi_objects']);self.canvas.label_id=self.classes.currentData()
            for widget,value in [(self.review,data['status']),(self.image_tag,data['payload']['image_tag']),(self.image_label,data['payload'].get('image_label_id'))]:widget.blockSignals(True);widget.setCurrentIndex(max(0,widget.findData(value)));widget.blockSignals(False)
            self.reason.setText(data['payload'].get('uncertain_reason',''));self.update_mode();self.load_cameras()
            self.dirty=False;self.update_objects();self.restore_selection();self.info.setText(f"PTS {data['frame']['pts_us']} µs · {image.width}×{image.height} · 标注修订 {self.revision} · Human Generated\n"+data['notice'])
        self.runner.run(operation,done)

    def restore_selection(self):
        self.frames.blockSignals(True)
        self.frames.setCurrentRow(next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==self.frame_id),-1),QItemSelectionModel.SelectionFlag.NoUpdate)
        self.frames.blockSignals(False)

    def mark_dirty(self,*args):
        if not self.frame_id or self.loading or self.excluded:return
        if self.image_tag.currentData()=='NORMAL' and any(not s['kind'].startswith('roi_') for s in self.canvas.shapes):
            self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(2);self.image_tag.blockSignals(False);self.current_tag='ABNORMAL';self.update_mode()
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
        payload=dict(self.loaded_payload,objects=[o for o in shapes if not o['kind'].startswith('roi_')],image_tag=self.image_tag.currentData(),image_label_id=self.image_label.currentData(),uncertain_reason=self.reason.text(),operator='local_operator',normal_conversion_confirmed=self.normal_confirmed)
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

    def tag_changed(self,*args):
        tag=self.image_tag.currentData()
        if self.loading or not self.frame_id:return
        if tag=='NORMAL':
            conflict=any(not s['kind'].startswith('roi_') for s in self.canvas.shapes) or self.image_label.currentData() or (self.current_tag=='ABNORMAL' and self.review.currentData() in {'REVIEWED','APPROVED'})
            if conflict:
                self.debounce.stop()
                answer=QMessageBox.question(self,'确认改为正常','当前图片已有异常标注，改为正常可能清除相关内容。是否继续？\n原标注保留历史，可通过“恢复历史标注…”恢复。',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)
                self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(self.image_tag.findData(self.current_tag));self.image_tag.blockSignals(False)
                if answer!=QMessageBox.StandardButton.Yes:
                    if self.dirty:self.debounce.start()
                    return
                if self.dirty or self.saving:self.pending=self.apply_normal;self.save_now();return
                self.apply_normal();return
            self.image_label.blockSignals(True);self.image_label.setCurrentIndex(0);self.image_label.blockSignals(False)
        self.current_tag=tag;self.update_mode();self.mark_dirty()

    def apply_normal(self):
        self.normal_confirmed=True;self.current_tag='NORMAL'
        self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(1);self.image_tag.blockSignals(False)
        self.image_label.blockSignals(True);self.image_label.setCurrentIndex(0);self.image_label.blockSignals(False)
        self.review.blockSignals(True);self.review.setCurrentText('DRAFT');self.review.blockSignals(False)
        self.canvas.shapes=[s for s in self.canvas.shapes if s['kind'].startswith('roi_')];self.canvas.selected_index=None;self.canvas.commit();self.update_mode();self.mark_dirty()

    def update_mode(self):
        normal=self.image_tag.currentData()=='NORMAL';enabled=not self.excluded and not self.loading
        self.image_tag.setEnabled(enabled);self.review.setEnabled(enabled);self.canvas.setEnabled(enabled);self.save_button.setEnabled(enabled);self.quick_button.setEnabled(enabled)
        self.image_label.setEnabled(enabled and not normal);self.classes.setEnabled(enabled and not normal)
        for i in [1,2]:self.tool.model().item(i).setEnabled(enabled and not normal)
        if normal and self.tool.currentData() in {'box','polygon'}:self.tool.setCurrentIndex(0)
        self.reason.setVisible(self.image_tag.currentData()=='UNKNOWN');self.reason.setEnabled(enabled)
        names={'NORMAL':'保存正常帧','ABNORMAL':'保存异常标注','UNKNOWN':'保存待复核'}
        self.quick_button.setText(names[self.image_tag.currentData()]+('并进入下一张' if self.auto_next.isChecked() else ''))

    def update_quick_text(self,*args):
        names={'NORMAL':'保存正常帧','ABNORMAL':'保存异常标注','UNKNOWN':'保存待复核'}
        self.quick_button.setText(names[self.image_tag.currentData()]+('并进入下一张' if self.auto_next.isChecked() else ''))

    def quick_save(self):
        if not self.frame_id or self.excluded:return
        self.mark_dirty()
        if self.auto_next.isChecked():self.pending=lambda:self.navigate(1)
        self.save_now()

    def chosen_frames(self):
        chosen={self.frames.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.frames.count()) if self.frames.item(i).checkState()==Qt.CheckState.Checked}
        selected=self.frames.selectedItems()
        if len(selected)>1:chosen.update(item.data(Qt.ItemDataRole.UserRole) for item in selected)
        return sorted(chosen)
    def check_changed(self,item):
        fid=item.data(Qt.ItemDataRole.UserRole)
        if item.checkState()==Qt.CheckState.Checked:self.checked_ids.add(fid)
        else:self.checked_ids.discard(fid)
        self.update_checked_count()
    def update_checked_count(self):
        if hasattr(self,'selected_count'):self.selected_count.setText(f'已选{len(self.chosen_frames())}张；未画框不等于正常')
    def clear_checked(self):
        self.checked_ids.clear();self.frames.clearSelection()
        for i in range(self.frames.count()):self.frames.item(i).setCheckState(Qt.CheckState.Unchecked)
        self.update_checked_count()
    def select_checked(self,unprocessed=False):
        self.clear_checked();states={r['id']:r.get('processing_state','UNPROCESSED') for r in self.frame_rows}
        for i in range(self.frames.count()):
            item=self.frames.item(i)
            if not unprocessed or states[item.data(Qt.ItemDataRole.UserRole)]=='UNPROCESSED':item.setCheckState(Qt.CheckState.Checked)
        self.update_checked_count()

    def batch_action(self,action,single=False):
        if not self.root or self.batch_busy:return
        if self.dirty or self.saving:
            self.pending=lambda:self.batch_action(action,single);self.save_now();return
        ids=[self.frame_id] if single and self.frame_id else self.chosen_frames()
        if not ids:self.info.setText('请先勾选或多选图片。');return
        reason=''
        if action=='exclude':
            reason,ok=QInputDialog.getItem(self,'剔除原因','无效画面原因（无法判断故障请用待复核，不应剔除）',['严重运动模糊','失焦/明显模糊','图像解码错误','转码花屏/画面损坏','严重曝光异常','摄像头画面丢失','其他人工指定原因'],0,True)
            if not ok or not reason.strip():return
        root=self.root;fid=self.frame_id;self.batch_busy=True
        row=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==fid),-1)
        next_id=self.frames.item(row+1).data(Qt.ItemDataRole.UserRole) if 0<=row<self.frames.count()-1 else None
        def preview_done(preview,error):
            if root!=self.root:self.batch_busy=False;return
            if error:self.batch_busy=False;self.info.setText(error);return
            message=f"已选{preview['selected']}张，可处理{len(preview['eligible'])}张，跳过{len(preview['skipped'])}张。\n已有标注/审核{preview['annotated']}张；旧数据集引用{preview['referenced']}张。\n"+'\n'.join(sorted({r['reason'] for r in preview['skipped']}))
            if not preview['eligible'] or QMessageBox.question(self,'确认帧操作',message+'\n批量正常仅限操作员已检查确认正常的图片。是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                self.batch_busy=False;self.info.setText(message);return
            def done(result,error):
                self.batch_busy=False
                if root!=self.root:return
                if error:self.info.setText('批次失败，未部分提交：'+error);return
                self.clear_checked();self.info.setText(f"已保存：{result['changed']}张，跳过{len(result['skipped'])}张；图片文件和历史保留。")
                self.saved.emit()
                if single and action=='exclude' and self.auto_next.isChecked() and next_id:self.request_load(next_id)
                elif self.frame_id:self.request_load(self.frame_id,force=True)
            self.runner.run(lambda:self.s.annotations.batch_apply(preview,reason,root),done)
        self.runner.run(lambda:self.s.annotations.batch_preview(ids,action,root),preview_done)

    def load_cameras(self,selected=None):
        if not self.root:return
        root=self.root;fid=self.frame_id
        def done(rows,error):
            if error or root!=self.root or fid!=self.frame_id:return
            self.camera_records=rows;self.camera_choice.blockSignals(True);self.camera_choice.clear();self.camera_choice.addItem('未关联摄像头',None)
            for r in rows:self.camera_choice.addItem(r['name']+' · '+r['id'][:8],r['id'])
            self.camera_choice.setCurrentIndex(max(0,self.camera_choice.findData(selected or self.camera_id)));self.camera_choice.blockSignals(False)
        self.runner.run(lambda:self.s.cameras.list(root),done)
    def edit_camera(self,existing):
        root=self.root;camera_id=self.camera_choice.currentData() if existing else None
        record=next((r for r in self.camera_records if r['id']==camera_id),None)
        if existing and not record:self.info.setText('请选择已有摄像头。');return
        name,ok=QInputDialog.getText(self,'编辑摄像头名称' if existing else '新建摄像头','摄像头显示名称',text=record['name'] if record else '')
        if not ok:return
        def done(row,error):
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.load_cameras(row['id']);self.info.setText('摄像头已保存，UUID不变；新建后点击保存摄像头关联。')
        self.runner.run(lambda:self.s.cameras.save(name,camera_id,record['revision'] if record else None,root),done)
    def associate_camera(self):
        if not self.media_id or self.dirty or self.saving:self.info.setText('请先等待或保存当前标注，再关联摄像头。');return
        root=self.root;mid=self.media_id;cid=self.camera_choice.currentData();old=self.camera_id
        def done(result,error):
            if root!=self.root:return
            if error:self.info.setText(error);return
            self.saved.emit();self.request_load(self.frame_id,force=True);self.info.setText('摄像头已关联，同录像及来源片段复用；标注UUID不变。')
        self.runner.run(lambda:self.s.cameras.associate(mid,cid,old,root),done)
    def restore_history(self):
        if not self.frame_id or self.dirty or self.saving:self.info.setText('请先保存当前修改，再恢复历史。');return
        root=self.root;fid=self.frame_id;expected=self.revision
        def done(rows,error):
            if error or root!=self.root or fid!=self.frame_id:return
            choices=[f"修订{r['revision']} · {r['payload'].get('image_tag')} · {r['status']}" for r in rows]
            if not choices:self.info.setText('没有可恢复的历史标注。');return
            choice,ok=QInputDialog.getItem(self,'恢复历史标注','恢复会生成新修订，旧修订及ROI保持',choices,0,False)
            if not ok:return
            revision=rows[choices.index(choice)]['revision']
            self.runner.run(lambda:self.s.annotations.restore_revision(fid,revision,expected,root),lambda value,error:self.request_load(fid,force=True) if not error and root==self.root else self.info.setText(error or '项目已切换'))
        self.runner.run(lambda:self.s.annotations.revisions(fid,root),done)
    def flush(self,callback):
        if self.save_error:self.info.setText('标注保存失败，请修正或明确放弃本次修改后再切换/退出。');return False
        if self.dirty or self.saving:self.pending=callback;self.save_now();return False
        return True
    def reload_discard(self):
        if not self.frame_id:return
        if self.dirty and QMessageBox.question(self,'放弃未保存修改','是否放弃本次未保存的标注修改并重新载入？',QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel)!=QMessageBox.StandardButton.Discard:return
        if self.saving:self.info.setText('请等待正在执行的保存完成。');return
        self.dirty=False;self.save_error=False;self.request_load(self.frame_id,force=True)
