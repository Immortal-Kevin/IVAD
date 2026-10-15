import copy,time,math
from PySide6.QtCore import Qt,QTimer,Signal,QItemSelectionModel
from PySide6.QtWidgets import QHBoxLayout,QVBoxLayout,QListWidget,QComboBox,QLabel,QSplitter,QWidget,QMessageBox,QScrollArea,QCheckBox,QInputDialog,QLineEdit,QAbstractItemView,QBoxLayout,QApplication,QSizePolicy
from PySide6.QtGui import QIcon,QPixmap,QPainter,QColor,QShortcut,QKeySequence
from ivad_app.gui.pages import Page,button
from ivad_app.gui.annotation_canvas import AnnotationCanvas
from ivad_app.gui.video_player import qimage

class AnnotationPage(Page):
    camera_navigation=Signal(str)
    labels_requested=Signal()
    saved=Signal()
    def __init__(self,services,runner):
        super().__init__('标注工作台','人工真值 · 原始图片像素坐标 · ROI独立存储；多边形右键/Enter完成，Esc取消。')
        self.s,self.runner=services,runner;self.root=None;self.frame_id=None;self.revision=self.roi_revision=0;self.dirty=self.saving=False;self.pending=None;self.save_error=False;self.roi_snapshot=[];self.loading=False;self.loaded_camera_roi=False;self.load_serial=0;self.roi_notice=''
        self.current_tag='UNKNOWN';self.loaded_payload={};self.normal_confirmed=False;self.media_id=None;self.camera_id=None;self.camera_records=[];self.camera_load_serial=0;self.camera_choice_dirty=False;self.camera_desired=None;self.batch_busy=False;self.checked_ids=set();self.excluded=False;self.filter_signature=None;self.working_labels={};self.enabled_labels=set();self.shortcut_busy=False;self.shortcut_ready_at=0
        self.shortcut_timer=QTimer(self);self.shortcut_timer.setSingleShot(True);self.shortcut_timer.timeout.connect(self.finish_top_shortcut)
        self.top_toolbar=QWidget();self.top_toolbar.setObjectName('annotation_top_toolbar');self.top_toolbar.setSizePolicy(QSizePolicy.Policy.Ignored,QSizePolicy.Policy.Minimum);self.top_layout=QBoxLayout(QBoxLayout.Direction.LeftToRight,self.top_toolbar);self.top_layout.setContentsMargins(0,0,0,0)
        self.tool_controls=QWidget();toolbar=QHBoxLayout(self.tool_controls);toolbar.setContentsMargins(0,0,0,0)
        self.top_layout.addWidget(self.tool_controls,1);self.top_actions=QWidget();self.top_actions.setObjectName('annotation_top_actions');self.top_actions.setSizePolicy(QSizePolicy.Policy.Minimum,QSizePolicy.Policy.Fixed);actions=QHBoxLayout(self.top_actions);actions.setContentsMargins(0,0,0,0)
        self.normal_button=button('保存正常并下一张',lambda:self.trigger_top_shortcut('normal'),True,'annotation_normal_next')
        self.abnormal_button=button('保存异常并下一张',lambda:self.trigger_top_shortcut('abnormal'),True,'annotation_abnormal_next')
        for shortcut in [self.normal_button,self.abnormal_button]:shortcut.setMinimumWidth(shortcut.sizeHint().width());actions.addWidget(shortcut)
        self.top_layout.addWidget(self.top_actions,0,Qt.AlignmentFlag.AlignRight);self.layout.addWidget(self.top_toolbar)
        self.tool=QComboBox();self.tool.setObjectName('annotation_tool')
        for text,value in [('选择/移动/顶点编辑','select'),('矩形框','box'),('多边形','polygon'),('矩形ROI','roi_box'),('多边形ROI','roi_polygon')]:self.tool.addItem(text,value)
        toolbar.addWidget(self.tool);toolbar.addWidget(button('适应窗口',lambda:self.canvas.fit()));toolbar.addWidget(button('撤销',lambda:self.canvas.undo(),name='annotation_undo'));toolbar.addWidget(button('重做',lambda:self.canvas.redo(),name='annotation_redo'))
        self.delete_button=button('删除选中',lambda:self.canvas.delete_selected(),name='annotation_delete');self.delete_button.setEnabled(False);toolbar.addWidget(self.delete_button)
        toolbar.addWidget(button('故障类型…',self.labels_requested.emit,name='annotation_labels'))
        splitter=QSplitter();self.frames=QListWidget();self.frames.setObjectName('annotation_frames');self.frames.setMouseTracking(True);self.frames.setMinimumWidth(190);self.frames.setMaximumWidth(280);self.frames.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.frames.viewport().setMouseTracking(True)
        from ivad_app.gui.frame_checkbox_delegate import FrameCheckboxDelegate
        self.frames.setItemDelegate(FrameCheckboxDelegate(self.frames))
        browser=QWidget();browser.setObjectName('annotation_browser');browser.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True);browser.setStyleSheet('QWidget#annotation_browser { background:#f2f5fa; }');browser.setMaximumWidth(280);browser_layout=QVBoxLayout(browser);browser_layout.setContentsMargins(0,0,0,0)
        self.media_filter=QComboBox();self.media_filter.addItem('全部来源',None);self.media_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.addWidget(self.media_filter);browser_layout.addWidget(self.frames);browser_scroll=QScrollArea();browser_scroll.setObjectName('annotation_browser_scroll');browser_scroll.setWidgetResizable(True);browser_scroll.setWidget(browser);browser_scroll.setMinimumWidth(230);browser_scroll.setMaximumWidth(300);splitter.addWidget(browser_scroll);self.frame_rows=[]
        self.state_filter=QComboBox();self.state_filter.setObjectName('frame_state_filter')
        for text,value in [('有效帧（默认）','ACTIVE'),('全部处理状态','ALL'),('仅未处理','UNPROCESSED'),('仅正常','NORMAL'),('仅异常','ABNORMAL'),('仅待复核','UNCERTAIN'),('仅已剔除','EXCLUDED'),('仅冲突','CONFLICT')]:self.state_filter.addItem(text,value)
        self.state_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.insertWidget(1,self.state_filter)
        self.camera_filter=QComboBox();self.camera_filter.setObjectName('frame_camera_filter');self.camera_filter.addItem('当前项目全部摄像头',None);self.camera_filter.addItem('未关联摄像头','__unlinked__')
        self.camera_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.insertWidget(0,self.camera_filter)
        self.worklist_filter=QComboBox();self.worklist_filter.setObjectName('frame_worklist_filter')
        for text,value in [('当前工作批次','CURRENT'),('全部帧（含已移出）','ALL'),('仅已移出批次','REMOVED')]:self.worklist_filter.addItem(text,value)
        self.worklist_filter.currentIndexChanged.connect(self.filter_frames);browser_layout.insertWidget(3,self.worklist_filter)
        self.cross_camera=QCheckBox('允许跨摄像头批量操作（需再次确认）')
        browser_layout.addWidget(self.cross_camera)
        self.batch_result=QLabel('批量操作仅处理当前可见的已选图片。');self.batch_result.setWordWrap(True);browser_layout.addWidget(self.batch_result)
        self.frames.itemChanged.connect(self.check_changed);self.frames.itemSelectionChanged.connect(self.update_checked_count)
        self.selected_count=QLabel('已选0张');browser_layout.addWidget(self.selected_count)
        actions=[('全选筛选结果',lambda:self.select_checked(), 'frames_select_all'),('选未处理帧',lambda:self.select_checked(True),'frames_select_unprocessed'),('取消选择',self.clear_checked,'frames_clear_selection'),('批量标记正常',lambda:self.batch_action('normal'),'frames_batch_normal'),('批量剔除无效帧',lambda:self.batch_action('exclude'),'frames_batch_exclude'),('恢复已剔除',lambda:self.batch_action('restore'),'frames_batch_restore'),('从当前批次移除',lambda:self.batch_action('remove'),'frames_batch_remove'),('移回当前批次',lambda:self.batch_action('return'),'frames_batch_return')]
        for i in range(0,len(actions),2):
            row=QHBoxLayout();row.setSpacing(4)
            for text,handler,name in actions[i:i+2]:
                b=button(text,handler,name=name);b.setStyleSheet('QPushButton { padding:6px 4px; }');row.addWidget(b)
            browser_layout.addLayout(row)
        self.frames.setMinimumHeight(120)
        self.canvas=AnnotationCanvas();splitter.addWidget(self.canvas)
        props=QWidget();props.setObjectName('annotation_properties');props.setStyleSheet('QWidget#annotation_properties { background: #ffffff; }');props.setMinimumWidth(230);props.setMaximumWidth(310);p=QVBoxLayout(props)
        self.classes=QComboBox();self.classes.setObjectName('annotation_class');self.classes.currentIndexChanged.connect(self.class_changed);self.classes.activated.connect(self.class_changed)
        self.review=QComboBox(self);self.review.hide();self.review.setObjectName('annotation_completion');self.review.setToolTip('标注完成不等于人工审核；详细审核在数据集管理中进行。')
        for text,value in [('未标注','UNLABELED'),('已标注','LABELED')]:self.review.addItem(text,value)
        self.image_tag=QComboBox();self.image_tag.setObjectName('image_tag')
        for text,value in [('未知/待确认','UNKNOWN'),('正常','NORMAL'),('异常','ABNORMAL')]:self.image_tag.addItem(text,value)
        self.image_label=QComboBox(self);self.image_label.hide();self.image_label.addItem('无整帧故障类别',None)
        self.roi_scope=QComboBox(self);self.roi_scope.addItems(['ROI关联当前视频','ROI关联摄像头']);self.roi_scope.hide()
        self.objects=QListWidget();self.objects.setMaximumHeight(150);self.objects.currentRowChanged.connect(self.select_object)
        p.addWidget(QLabel('当前摄像头'));self.camera_display=QLabel('未关联摄像头');self.camera_display.setWordWrap(True);p.addWidget(self.camera_display)
        for text,widget in [('当前处理方式',self.image_tag),('故障类型（用于新绘制目标）',self.classes),('当前对象',self.objects)]:p.addWidget(QLabel(text));p.addWidget(widget)
        self.fault_summary=QLabel('本帧故障：无');self.fault_summary.setWordWrap(True);p.addWidget(self.fault_summary)
        p.addWidget(button('修改所选对象类别',self.apply_object_label,name='annotation_apply_class'))
        p.addWidget(button('整帧标签详情…',self.edit_frame_label,name='annotation_frame_details'))
        p.addWidget(button('ROI 管理 / 来源说明',self.manage_roi,name='annotation_roi_manage'))
        self.processing_notice=QLabel('标注完成不等于已审核。');self.processing_notice.setWordWrap(True);p.addWidget(self.processing_notice)
        p.addWidget(QLabel('当前图片处理'))
        self.reason=QLineEdit();self.reason.setPlaceholderText('无法判断原因（可选）');p.addWidget(self.reason);self.reason.textEdited.connect(self.mark_dirty)
        self.auto_next=QCheckBox('待复核保存后自动下一张');self.auto_next.setChecked(True);p.addWidget(self.auto_next)
        self.runner.run(lambda:self.s.settings.get('annotation_ux',{'auto_next':True}),lambda value,error:self.auto_next.setChecked(value.get('auto_next',True)) if not error else None)
        self.auto_next.toggled.connect(lambda value:self.runner.run(lambda:self.s.settings.set('annotation_ux',{'auto_next':value})))
        self.quick_button=button('保存待复核并进入下一张',self.quick_save,True,'annotation_quick_save');p.addWidget(self.quick_button)
        self.auto_next.toggled.connect(self.update_quick_text)
        self.exclude_button=button('剔除并下一张',lambda:self.batch_action('exclude',True,True),name='frame_exclude');p.addWidget(self.exclude_button)
        p.addWidget(button('恢复当前帧',lambda:self.batch_action('restore',True),name='frame_restore'))
        self.save_button=button('保存标注',self.save_now,True,'save_annotation');p.addWidget(self.save_button);p.addWidget(button('放弃修改并重载',self.reload_discard));p.addStretch()
        p.addWidget(button('恢复历史标注…',self.restore_history,name='annotation_restore_history'))
        p.addWidget(button('前往视频管理关联摄像头',lambda:self.camera_navigation.emit(self.media_id or ''),name='camera_go_media'))
        scroll=QScrollArea();scroll.setWidgetResizable(True);scroll.setWidget(props);scroll.setMinimumWidth(250);scroll.setMaximumWidth(330);splitter.addWidget(scroll);splitter.setSizes([220,650,290]);self.layout.addWidget(splitter,1)
        row=QHBoxLayout();row.addWidget(button('上一张',lambda:self.navigate(-1)));row.addWidget(button('下一张',lambda:self.navigate(1)));self.info=QLabel('请打开项目并抽帧。');self.info.setWordWrap(True);row.addWidget(self.info,1);self.layout.addLayout(row)
        self.debounce=QTimer(self);self.debounce.setSingleShot(True);self.debounce.setInterval(350);self.debounce.timeout.connect(self.save_now)
        self.canvas.changed.connect(self.mark_dirty);self.canvas.selected.connect(self.selection);self.canvas.error.connect(self.info.setText)
        self.tool.currentIndexChanged.connect(lambda:self.canvas.set_tool(self.tool.currentData()))
        self.frames.currentRowChanged.connect(self.select_frame)
        self.image_label.currentIndexChanged.connect(self.mark_dirty)
        self.image_tag.currentIndexChanged.connect(self.tag_changed)
        self.roi_scope.currentIndexChanged.connect(lambda:self.request_load(self.frame_id,force=True) if self.frame_id else None)
        self.save_shortcut=QShortcut(QKeySequence('Ctrl+S'),self);self.save_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.save_shortcut.activated.connect(self.save_now)
        self.quick_shortcut=QShortcut(QKeySequence('Ctrl+Return'),self);self.quick_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut);self.quick_shortcut.activated.connect(self.quick_save)

    def resizeEvent(self,event):
        super().resizeEvent(event)
        if not hasattr(self,'top_toolbar'):return
        needed=self.tool_controls.minimumSizeHint().width()+self.top_actions.sizeHint().width()+self.top_layout.spacing()
        direction=QBoxLayout.Direction.LeftToRight if self.width()-self.layout.contentsMargins().left()-self.layout.contentsMargins().right()>=needed else QBoxLayout.Direction.TopToBottom
        if self.top_layout.direction()!=direction:self.top_layout.setDirection(direction)
    def sync_top_shortcuts(self):
        enabled=bool(self.root and self.frame_id) and not (self.excluded or self.loading or self.saving or self.shortcut_busy)
        self.normal_button.setEnabled(enabled);self.abnormal_button.setEnabled(enabled)
    def finish_top_shortcut(self):
        if self.saving or self.loading or self.pending:return
        remaining=self.shortcut_ready_at-time.monotonic()
        if self.shortcut_busy and remaining>0:self.shortcut_timer.start(max(1,math.ceil(remaining*1000)));return
        self.shortcut_busy=False;self.sync_top_shortcuts()
    def trigger_top_shortcut(self,kind):
        if self.shortcut_busy or self.saving or self.loading or not self.frame_id or self.excluded:return
        self.shortcut_busy=True;self.shortcut_ready_at=time.monotonic()+QApplication.doubleClickInterval()/1000;self.sync_top_shortcuts()
        if kind=='normal':self.save_normal_next()
        else:self.save_abnormal_next()
        self.finish_top_shortcut()
    def advance_top_shortcut(self):
        rows={row['id']:row for row in self.frame_rows}
        current=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==self.frame_id),-1)
        for index in range(current+1,self.frames.count()):
            fid=self.frames.item(index).data(Qt.ItemDataRole.UserRole);row=rows[fid]
            if row.get('processing_state')!='EXCLUDED' and row.get('state')=='READY':self.request_load(fid);return
        self.info.setText(self.info.text()+'\n已到当前筛选最后一张可处理图片；已保存，未跳转。')
        self.finish_top_shortcut()
    def set_project(self,root):
        self.shortcut_timer.stop();self.shortcut_busy=False;self.root=root;self.frame_id=None;self.media_id=None;self.camera_id=None;self.camera_choice_dirty=False;self.camera_load_serial+=1;self.dirty=False;self.saving=False;self.pending=None;self.save_error=False;self.debounce.stop();self.checked_ids.clear();self.frames.clear();self.frame_rows=[];self.filter_signature=None;self.batch_result.setText('批量操作仅处理当前可见的已选图片。');self.canvas.pixmap=None;self.canvas.shapes=[];self.canvas.render();self.setEnabled(bool(root));self.sync_top_shortcuts()
    def set_data(self,frames,labels):
        self.frame_rows=frames;selected_filter=self.media_filter.currentData();self.media_filter.blockSignals(True);self.media_filter.clear();self.media_filter.addItem('全部来源',None)
        for mid in dict.fromkeys(r['media_id'] for r in frames):self.media_filter.addItem(next((r.get('media_name','来源录像') for r in frames if r['media_id']==mid),'来源录像'),mid)
        self.media_filter.setCurrentIndex(max(0,self.media_filter.findData(selected_filter)));self.media_filter.blockSignals(False);self.filter_frames()
        old=self.classes.currentData();old_image=self.image_label.currentData()
        self.classes.blockSignals(True);self.image_label.blockSignals(True);self.classes.clear();self.classes.addItem('请选择故障类型',None);self.enabled_labels={r['id'] for r in labels if r['enabled']};self.image_label.clear();self.image_label.addItem('无整帧故障类别',None)
        for label in labels:
            text=label['name']+('（停用）' if not label['enabled'] else '')
            self.classes.addItem(text,label['id']);self.classes.model().item(self.classes.count()-1).setEnabled(bool(label['enabled']));self.image_label.addItem(text,label['id'])
        self.classes.setCurrentIndex(max(0,self.classes.findData(old)));self.image_label.setCurrentIndex(max(0,self.image_label.findData(old_image)));self.classes.blockSignals(False);self.image_label.blockSignals(False)
        self.canvas.label_names={r['id']:r['name'] for r in labels};self.canvas.label_id=self.classes.currentData() if self.classes.currentData() in self.enabled_labels else None
        if not self.frame_id and self.frames.count():self.frames.setCurrentRow(0)
        self.load_cameras()

    def filter_frames(self):
        signature=(self.camera_filter.currentData(),self.media_filter.currentData(),self.state_filter.currentData(),self.worklist_filter.currentData())
        if signature!=self.filter_signature:self.checked_ids.clear();self.filter_signature=signature
        selected=self.frame_id;self.frames.blockSignals(True);self.frames.clear();mid=self.media_filter.currentData()
        camera=self.camera_filter.currentData();worklist=self.worklist_filter.currentData()
        source_order={value:i for i,value in enumerate(dict.fromkeys(r['media_id'] for r in self.frame_rows))}
        for row in sorted(self.frame_rows,key=lambda r:(source_order[r['media_id']],r['time_us'],r['id'])):
            if mid and row['media_id']!=mid:continue
            if camera=='__unlinked__' and row.get('camera_id'):continue
            if camera not in {None,'__unlinked__'} and row.get('camera_id')!=camera:continue
            hidden=row.get('worklist_hidden',row.get('handling',{}).get('worklist_hidden',False))
            if (worklist=='CURRENT' and hidden) or (worklist=='REMOVED' and not hidden):continue
            state=row.get('processing_state','UNPROCESSED');flt=self.state_filter.currentData()
            if (flt=='ACTIVE' and state=='EXCLUDED') or (flt not in {'ACTIVE','ALL'} and flt!=state):continue
            source=row.get('media_identifier') or row.get('media_name','来源录像');source=source if len(source)<=30 else source[:27]+'…'
            self.frames.addItem(f"{row['time_us']/1000000:.3f}s · {source}"+(' Missing' if row['state']=='MISSING' else ''));self.frames.item(self.frames.count()-1).setData(Qt.ItemDataRole.UserRole,row['id'])
            item=self.frames.item(self.frames.count()-1);item.setFlags(item.flags()|Qt.ItemFlag.ItemIsUserCheckable);item.setCheckState(Qt.CheckState.Checked if row['id'] in self.checked_ids else Qt.CheckState.Unchecked)
            names={'UNPROCESSED':('○','未处理','#7c8794'),'NORMAL':('✓','已确认正常','#1a874b'),'ABNORMAL':('!','已标注异常','#c63737'),'UNCERTAIN':('?','无法判断/待复核','#a67b00'),'EXCLUDED':('×','已剔除（文件保留）','#7c8794'),'CONFLICT':('!','数据冲突','#c63737')}
            symbol,title,color=names[state];pix=QPixmap(22,22);pix.fill(Qt.GlobalColor.transparent);painter=QPainter(pix);painter.setPen(QColor(color));font=painter.font();font.setPixelSize(20);painter.setFont(font);painter.drawText(pix.rect(),Qt.AlignmentFlag.AlignCenter,symbol);painter.end();item.setIcon(QIcon(pix));item.setToolTip(title+'；'+('已标注' if row.get('completion_state')=='LABELED' else '未标注')+'\n来源：'+row.get('media_name','')+'\n摄像头：'+row.get('camera_name','未关联')+'\n帧UUID：'+row['id'])
        self.checked_ids.intersection_update({self.frames.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.frames.count())})
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
    def request_load(self,frame_id,force=False,roi_override=None):
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
        root=self.root;camera_roi=roi_override;self.loading=True;self.load_serial+=1;serial=self.load_serial;self.canvas.setEnabled(False);self.sync_top_shortcuts()
        for widget in [self.review,self.image_tag,self.image_label,self.classes,self.roi_scope]:widget.setEnabled(False)
        def operation():
            frame,image=self.s.media.frame_image(frame_id,root);data=self.s.annotations.load(frame_id,root,camera_roi);return image,data
        def done(result,error):
            if serial!=self.load_serial or root!=self.root:return
            self.loading=False
            self.canvas.setEnabled(True)
            for widget in [self.review,self.image_tag,self.image_label,self.classes,self.roi_scope]:widget.setEnabled(True)
            if error:
                self.roi_scope.blockSignals(True);self.roi_scope.setCurrentIndex(int(self.loaded_camera_roi));self.roi_scope.blockSignals(False);self.restore_selection();self.info.setText(error);self.finish_top_shortcut();return
            self.loaded_camera_roi=result[1]['camera_roi']
            image,data=result;self.frame_id=frame_id;self.revision=data['revision'];self.roi_revision=data['roi_revision'];self.roi_snapshot=copy.deepcopy(data['roi_objects']);self.save_error=False
            if self.media_id!=data['frame']['media_id']:self.camera_choice_dirty=False
            self.review_status=data['status'];self.current_tag=data['payload']['image_tag'];self.loaded_payload=copy.deepcopy(data['payload']);self.normal_confirmed=False;self.media_id=data['frame']['media_id'];self.camera_id=data['frame']['camera_id'];self.excluded=data['processing_state']=='EXCLUDED'
            self.roi_scope.blockSignals(True);self.roi_scope.setCurrentIndex(int(self.loaded_camera_roi));self.roi_scope.model().item(1).setEnabled(data['camera_available']);self.roi_scope.blockSignals(False)
            self.roi_notice=data['notice'];self.roi_scope.setToolTip(data['notice'] or 'ROI 为可选辅助信息，与目标标注及整帧标签独立。')
            self.canvas.set_image(qimage(image));self.canvas.set_shapes(data['payload']['objects']+data['roi_objects']);self.canvas.label_id=self.classes.currentData()
            for widget,value in [(self.review,data['completion_state']),(self.image_tag,data['payload']['image_tag']),(self.image_label,data['payload'].get('image_label_id'))]:widget.blockSignals(True);widget.setCurrentIndex(max(0,widget.findData(value)));widget.blockSignals(False)
            self.choose_working_label(data['payload']['objects']);self.reason.setText(data['payload'].get('uncertain_reason',''));self.update_mode();self.load_cameras()
            self.dirty=False;self.update_objects();self.restore_selection();self.info.setText(f"PTS {data['frame']['pts_us']} µs · {image.width}×{image.height} · 标注修订 {self.revision} · Human Generated\n"+data['notice']);self.finish_top_shortcut()
        self.runner.run(operation,done)

    def restore_selection(self):
        self.frames.blockSignals(True)
        self.frames.setCurrentRow(next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==self.frame_id),-1),QItemSelectionModel.SelectionFlag.NoUpdate)
        self.frames.blockSignals(False)

    def mark_dirty(self,*args,completion_edit=False):
        if not self.frame_id or self.loading or self.excluded:return
        if any(not shape['kind'].startswith('roi_') for shape in self.canvas.shapes):
            self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(2);self.image_tag.blockSignals(False);self.current_tag='ABNORMAL';self.update_mode()
        self.dirty=True;self.save_error=False;self.info.setText('有修改，自动保存中…');self.update_objects();self.debounce.start()
    def update_objects(self):
        self.objects.blockSignals(True);self.objects.clear()
        for obj in self.canvas.shapes:self.objects.addItem(obj['kind']+' · '+self.canvas.label_names.get(obj.get('label_id'),'ROI'))
        names={self.canvas.label_names.get(obj.get('label_id'),obj.get('label_id','未知')) for obj in self.canvas.shapes if not obj['kind'].startswith('roi_')}
        historical=self.image_label.currentText() if self.image_label.currentData() else '无'
        self.fault_summary.setText('目标故障：'+('、'.join(sorted(names)) if names else '无')+'\n历史整帧类别：'+historical)
        self.objects.setCurrentRow(self.canvas.selected_index if self.canvas.selected_index is not None else -1);self.objects.blockSignals(False)
    def select_object(self,index):
        self.canvas.selected_index=index if index>=0 else None;self.canvas.render();self.selection(self.canvas.shapes[index] if 0<=index<len(self.canvas.shapes) else None)
    def selection(self,obj):
        self.delete_button.setEnabled(obj is not None)
        self.update_objects()
    def working_key(self):
        return (self.root,'camera',self.camera_id) if self.camera_id else (self.root,'media',self.media_id)
    def choose_working_label(self,objects):
        # Reading historical truth never changes the session default or the objects.
        label=self.working_labels.get(self.working_key())
        self.classes.blockSignals(True);self.classes.setCurrentIndex(max(0,self.classes.findData(label)));self.classes.blockSignals(False)
        self.canvas.label_id=label if label in self.enabled_labels else None
    def class_changed(self,*args):
        label=self.classes.currentData();self.canvas.label_id=label if label in self.enabled_labels else None
        if self.frame_id and not self.loading:self.working_labels[self.working_key()]=self.canvas.label_id
    def apply_object_label(self):
        index=self.canvas.selected_index;label=self.classes.currentData()
        if self.excluded or index is None or not 0<=index<len(self.canvas.shapes) or label not in self.enabled_labels:return
        shape=self.canvas.shapes[index]
        if shape['kind'].startswith('roi_'):return
        shape['label_id']=label;self.canvas.commit()
    def edit_frame_label(self):
        if not self.frame_id or self.loading or self.excluded:return
        choices=[self.image_label.itemText(i)+(' · '+str(self.image_label.itemData(i)) if self.image_label.itemData(i) else '') for i in range(self.image_label.count())]
        choice,ok=QInputDialog.getItem(self,'整帧标签详情','整帧类别独立保留；确认后沿用自动保存，也可手动保存；不会创建检测框。',choices,max(0,self.image_label.currentIndex()),False)
        if not ok:return
        index=choices.index(choice)
        if index==self.image_label.currentIndex():return
        if self.image_label.itemData(index):
            self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(self.image_tag.findData('ABNORMAL'));self.image_tag.blockSignals(False);self.current_tag='ABNORMAL'
        self.image_label.setCurrentIndex(index);self.update_mode()
    def save_normal_next(self):
        if not self.frame_id or self.excluded or self.loading:return
        if self.saving or (self.dirty and self.image_tag.currentData()!='NORMAL'):
            self.pending=self.save_normal_next;self.save_now();return
        self.image_tag.setCurrentIndex(self.image_tag.findData('NORMAL'))
        if self.image_tag.currentData()!='NORMAL':return
        self.mark_dirty();self.pending=self.advance_top_shortcut;self.save_now()
    def save_abnormal_next(self):
        if not self.frame_id or self.excluded or self.loading:return
        if not any(not obj['kind'].startswith('roi_') for obj in self.canvas.shapes) and not self.image_label.currentData():
            self.info.setText('请先绘制故障目标，或在“整帧标签详情”明确分类类别；不会自动创建框。');return
        self.image_tag.blockSignals(True);self.image_tag.setCurrentIndex(self.image_tag.findData('ABNORMAL'));self.image_tag.blockSignals(False);self.current_tag='ABNORMAL'
        self.mark_dirty();self.update_mode();self.pending=self.advance_top_shortcut;self.save_now()

    def save_now(self):
        self.debounce.stop()
        if self.saving:return
        if not self.dirty:
            if self.pending:callback=self.pending;self.pending=None;callback()
            return
        if not self.root or not self.frame_id:return
        root,frame_id=self.root,self.frame_id;shapes=copy.deepcopy(self.canvas.shapes);rois=[o for o in shapes if o['kind'].startswith('roi_')]
        payload=dict(self.loaded_payload,objects=[o for o in shapes if not o['kind'].startswith('roi_')],image_tag=self.image_tag.currentData(),image_label_id=self.image_label.currentData(),uncertain_reason=self.reason.text(),operator='local_operator',normal_conversion_confirmed=self.normal_confirmed)
        completion=None;status=None;revision=self.revision;roi_revision=self.roi_revision;camera=self.loaded_camera_roi;changed_roi=rois if rois!=self.roi_snapshot else None
        self.saving=True;self.dirty=False;self.sync_top_shortcuts()
        def done(result,error):
            self.saving=False
            if root!=self.root or frame_id!=self.frame_id:return
            if error:self.dirty=True;self.save_error=True;self.pending=None;self.restore_selection();self.info.setText('保存失败：'+error+'；可重试保存，或切换图片时明确选择不保存继续。');self.finish_top_shortcut();return
            self.review.blockSignals(True);self.review.setCurrentIndex(max(0,self.review.findData(result['completion_state'])));self.review.blockSignals(False)
            self.revision=result['revision'];self.roi_revision=result['roi_revision'];self.roi_snapshot=rois;self.info.setText(f"已保存 · 修订 {self.revision} · "+('已标注' if result['completion_state']=='LABELED' else '未标注')+'；人工审核请前往数据集管理。\n'+self.roi_notice+'\n'+result.get('warning',''));self.saved.emit()
            if self.dirty:self.save_now()
            elif self.pending:callback=self.pending;self.pending=None;callback()
            self.finish_top_shortcut()
        self.runner.run(lambda:self.s.annotations.save(frame_id,payload,status,revision,changed_roi,roi_revision,camera,root,completion_state=completion),done)

    def tag_changed(self,*args):
        tag=self.image_tag.currentData()
        if self.loading or not self.frame_id:return
        if tag=='NORMAL':
            conflict=any(not s['kind'].startswith('roi_') for s in self.canvas.shapes) or self.image_label.currentData() or (self.current_tag=='ABNORMAL' and self.review_status in {'REVIEWED','APPROVED'})
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
        self.canvas.shapes=[s for s in self.canvas.shapes if s['kind'].startswith('roi_')];self.canvas.selected_index=None;self.canvas.commit();self.update_mode();self.mark_dirty()

    def update_mode(self):
        normal=self.image_tag.currentData()=='NORMAL';enabled=not self.excluded and not self.loading
        self.processing_notice.setText('已剔除：已处理的无效帧，不作为训练标注；恢复后保留原内容。' if self.excluded else '标注完成不等于已审核；请到数据集管理人工审核。')
        self.image_tag.setEnabled(enabled);self.review.setEnabled(False);self.canvas.setEnabled(enabled);self.save_button.setEnabled(enabled);self.quick_button.setEnabled(enabled);self.sync_top_shortcuts();self.exclude_button.setEnabled(not self.loading)
        self.image_label.setEnabled(enabled and not normal);self.classes.setEnabled(enabled and not normal)
        for i in [1,2]:self.tool.model().item(i).setEnabled(enabled and not normal)
        if normal and self.tool.currentData() in {'box','polygon'}:self.tool.setCurrentIndex(0)
        self.auto_next.setVisible(self.image_tag.currentData()=='UNKNOWN');self.quick_button.setVisible(self.image_tag.currentData()=='UNKNOWN');self.reason.setVisible(self.image_tag.currentData()=='UNKNOWN');self.reason.setEnabled(enabled)
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

    def batch_action(self,action,single=False,force_next=False):
        if not self.root or self.batch_busy:return
        if self.dirty or self.saving:
            self.pending=lambda:self.batch_action(action,single,force_next);self.save_now();return
        ids=[self.frame_id] if single and self.frame_id else self.chosen_frames()
        visible={self.frames.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.frames.count())};ids=[fid for fid in ids if fid in visible]
        if not ids:self.batch_result.setText('请先勾选当前可见图片。');return
        camera_ids={r.get('camera_id') for r in self.frame_rows if r['id'] in ids}
        if len(camera_ids)>1:
            if not self.cross_camera.isChecked():self.batch_result.setText('已选图片属于多个摄像头。请先按摄像头筛选；跨摄像头操作须使用独立勾选入口。');return
            if QMessageBox.question(self,'跨摄像头二次确认',f'本次将操作{len(camera_ids)}组摄像头来源的{len(ids)}张图片，是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:return
        reason=''
        if action=='exclude':
            reason,ok=QInputDialog.getItem(self,'剔除原因','由人工判断；轻微模糊不自动无效。无法判断故障请用待复核。',['严重模糊','图像解码错误','花屏或画面损坏','严重曝光异常','摄像头画面丢失','其他原因'],0,False)
            if not ok or not reason.strip():return
        root=self.root;fid=self.frame_id;criteria=self.filter_signature;self.batch_busy=True;self.batch_result.setText('正在检查已选图片及历史引用…')
        row=next((i for i in range(self.frames.count()) if self.frames.item(i).data(Qt.ItemDataRole.UserRole)==fid),-1)
        next_id=self.frames.item(row+1).data(Qt.ItemDataRole.UserRole) if 0<=row<self.frames.count()-1 else None
        def preview_done(preview,error):
            if root!=self.root or criteria!=self.filter_signature:self.batch_busy=False;self.batch_result.setText('项目或筛选已改变，操作取消，请重新选择。');return
            if error:self.batch_busy=False;self.batch_result.setText('检查失败：'+error);return
            message=f"已选{preview['selected']}张，可处理{len(preview['eligible'])}张，跳过{len(preview['skipped'])}张。\n已有标注/审核{preview['annotated']}张；旧数据集引用{preview['referenced']}张。\n"+'\n'.join(sorted({r['reason'] for r in preview['skipped']}))
            help_text='批量正常仅限操作员已检查确认正常的图片。' if action=='normal' else ('仅软剔除，文件和历史保留，可恢复。' if action=='exclude' else {'restore':'恢复原处理状态，保留标注和历史。','remove':'仅移出当前工作批次，不改变标注、训练资格或数据集引用。','return':'移回当前工作批次，不改变标注。'}[action])
            self.batch_result.setText(message)
            if not preview['eligible']:
                self.batch_busy=False;self.batch_result.setText(message+'\n成功0张，跳过'+str(len(preview['skipped']))+'张，失败0张。');QMessageBox.information(self,'没有可处理的图片',self.batch_result.text());return
            if QMessageBox.question(self,'确认帧操作',message+'\n'+help_text+'是否继续？',QMessageBox.StandardButton.Yes|QMessageBox.StandardButton.No,QMessageBox.StandardButton.No)!=QMessageBox.StandardButton.Yes:
                self.batch_busy=False;self.info.setText(message);return
            def done(result,error):
                self.batch_busy=False
                if root!=self.root:return
                if error:self.batch_result.setText(f'成功0张，失败{len(preview["eligible"])}张，跳过{len(preview["skipped"])}张；整个事务未提交：'+error);return
                self.clear_checked();self.batch_result.setText(f"成功{result['changed']}张，跳过{len(result['skipped'])}张，失败{result['failed']}张；图片、标注和历史保留。")

                if result.get('warning'):self.batch_result.setText(self.batch_result.text()+'\n'+result['warning'])
                self.saved.emit()
                if single and action=='exclude' and (force_next or self.auto_next.isChecked()) and next_id:self.request_load(next_id)
                elif self.frame_id:self.request_load(self.frame_id,force=True)
            self.runner.run(lambda:self.s.annotations.batch_apply(preview,reason,root),done)
        self.runner.run(lambda:self.s.annotations.batch_preview(ids,action,root),preview_done)

    def load_cameras(self,selected=None):
        if not self.root:return
        root=self.root;fid=self.frame_id;cid=self.camera_id
        def done(rows,error):
            if error or root!=self.root or fid!=self.frame_id or cid!=self.camera_id:return
            old=self.camera_filter.currentData();self.camera_records=rows;self.camera_filter.blockSignals(True);self.camera_filter.clear();self.camera_filter.addItem('当前项目全部摄像头',None);self.camera_filter.addItem('未关联摄像头','__unlinked__')
            for record in rows:self.camera_filter.addItem((record['details'].get('code') or '')+' · '+record['name'],record['id'])
            self.camera_filter.setCurrentIndex(max(0,self.camera_filter.findData(old)));self.camera_filter.blockSignals(False);self.filter_frames()
            camera=next((r for r in rows if r['id']==cid),None)
            self.camera_display.setText(((camera['details'].get('code') or '')+' · '+camera['name']+' · '+camera['id']+('（停用）' if not camera['details'].get('enabled',True) else '')) if camera else '未关联摄像头；不阻断基础标注')
        self.runner.run(lambda:self.s.cameras.list(root),done)
    def manage_roi(self):
        if not self.frame_id:return
        dialog=QMessageBox(self);dialog.setWindowTitle('ROI 管理');dialog.setText(self.roi_notice+'\n自动规则：当前视频有效ROI优先，其次摄像头ROI。区域仅辅助标注，不触发AI。')
        video=dialog.addButton('编辑视频 ROI',QMessageBox.ButtonRole.ActionRole)
        camera=dialog.addButton('编辑摄像头 ROI',QMessageBox.ButtonRole.ActionRole);camera.setEnabled(bool(self.camera_id))
        dialog.addButton('关闭',QMessageBox.ButtonRole.RejectRole);dialog.exec()
        target=dialog.clickedButton()
        if target in {video,camera}:
            action=lambda:self.request_load(self.frame_id,force=True,roi_override=target==camera)
            if self.flush(action):action()
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
