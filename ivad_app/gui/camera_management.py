from PySide6.QtCore import Qt,QSignalBlocker
from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QLabel,QCheckBox,QMessageBox
from ivad_app.gui.pages import table,button

class CameraPanel(QWidget):
    def __init__(self,controller):
        super().__init__();self.setObjectName('camera_management_panel');self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground,True)
        self.controller=controller;self.rows=[];self.record=None;self.dirty=False;self.loading=False;self.mode='CREATE'
        layout=QVBoxLayout(self);self.project=QLabel('请先打开项目');self.project.setWordWrap(True);layout.addWidget(self.project)
        self.mode_label=QLabel('当前模式：CREATE · 正在新建摄像头');layout.addWidget(self.mode_label)
        self.table=table(['编号','显示名称','UUID','位置','启用']);self.table.setMinimumHeight(125);self.table.itemSelectionChanged.connect(self.select);layout.addWidget(self.table,1)
        form=QFormLayout();layout.addLayout(form);self.uuid=QLabel('新建时自动生成');self.uuid.setWordWrap(True);form.addRow('Camera UUID',self.uuid)
        self.fields={}
        for key,label in [('code','摄像头编号'),('name','显示名称'),('location','安装位置（可选）'),('equipment','设备说明（可选）')]:
            widget=QLineEdit();widget.setMaxLength(200);widget.setObjectName('camera_'+key);self.fields[key]=widget;form.addRow(label,widget)
            widget.textChanged.connect(self.mark_dirty)
        self.enabled=QCheckBox('启用（停用仍保留历史关联，不物理删除）');self.enabled.setChecked(True);form.addRow(self.enabled);self.enabled.toggled.connect(self.mark_dirty)
        row=QHBoxLayout();layout.addLayout(row)
        row.addWidget(button('新建摄像头',self.new,name='project_camera_new'))
        row.addWidget(button('保存当前修改',controller.save_camera,name='project_camera_save'))
        row.addWidget(button('刷新',controller.refresh_cameras,name='project_camera_refresh'))
        self.info=QLabel('新建会生成新UUID；编辑只修改当前UUID。');self.info.setWordWrap(True);layout.addWidget(self.info)
    def mark_dirty(self,*_):
        if not self.loading:self.dirty=True
    def guard(self,action):
        if not self.dirty:action();return
        answer=QMessageBox.question(self,'摄像头资料尚未保存','保存修改后切换、放弃修改，或取消切换？',QMessageBox.StandardButton.Save|QMessageBox.StandardButton.Discard|QMessageBox.StandardButton.Cancel,QMessageBox.StandardButton.Cancel)
        if answer==QMessageBox.StandardButton.Save:self.controller.save_camera(on_success=action)
        elif answer==QMessageBox.StandardButton.Discard:action()
        else:self.restore_selection()
    def restore_selection(self):
        with QSignalBlocker(self.table):
            self.table.clearSelection()
            if self.record:
                for i,r in enumerate(self.rows):
                    if r['id']==self.record['id']:self.table.selectRow(i);break
    def new(self,force=False):
        if not force:self.guard(lambda:self.new(force=True));return
        self.loading=True
        try:
            self.record=None;self.mode='CREATE'
            with QSignalBlocker(self.table):self.table.clearSelection();self.table.setCurrentCell(-1,-1)
            self.uuid.setText('新建时自动生成');self.mode_label.setText('当前模式：CREATE · 正在新建摄像头')
            for w in self.fields.values():w.clear()
            self.enabled.setChecked(True);self.dirty=False
        finally:self.loading=False
    def load_record(self,row):
        self.loading=True
        try:
            self.record=row;self.mode='EDIT';self.uuid.setText(row['id']);self.fields['name'].setText(row['name'])
            for k in ['code','location','equipment']:self.fields[k].setText(row['details'].get(k,''))
            self.enabled.setChecked(row['details'].get('enabled',True));self.dirty=False
            self.mode_label.setText('当前模式：EDIT · 编辑摄像头 '+row['details'].get('code',''))
            self.restore_selection()
        finally:self.loading=False
    def select(self):
        if self.loading or not self.table.selectedItems():return
        i=self.table.currentRow()
        if not 0<=i<len(self.rows):return
        row=self.rows[i]
        if self.record and row['id']==self.record['id']:return
        self.guard(lambda:self.load_record(row))
