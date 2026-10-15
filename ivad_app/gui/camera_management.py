from PySide6.QtWidgets import QWidget,QVBoxLayout,QHBoxLayout,QFormLayout,QLineEdit,QLabel,QCheckBox
from ivad_app.gui.pages import table,button

class CameraPanel(QWidget):
    def __init__(self,controller):
        super().__init__();self.controller=controller;self.rows=[];self.record=None;self.dirty=False;layout=QVBoxLayout(self)
        self.project=QLabel('请打开项目');self.project.setWordWrap(True);layout.addWidget(self.project)
        self.table=table(['编号','显示名称','UUID','位置','启用']);self.table.setMinimumHeight(125);self.table.itemSelectionChanged.connect(self.select);layout.addWidget(self.table,1)
        form=QFormLayout();layout.addLayout(form);self.uuid=QLabel('新建时自动生成');self.uuid.setWordWrap(True);form.addRow('Camera UUID',self.uuid)
        self.fields={}
        for key,label in [('code','摄像头编号'),('name','显示名称'),('location','安装位置（可选）'),('equipment','设备说明（可选）')]:
            widget=QLineEdit();widget.setMaxLength(200);widget.setObjectName('camera_'+key);self.fields[key]=widget;form.addRow(label,widget)
            widget.textEdited.connect(lambda:setattr(self,'dirty',True))
        self.enabled=QCheckBox('启用（停用仍保留历史关联，不物理删除）');self.enabled.setChecked(True);form.addRow(self.enabled)
        self.enabled.clicked.connect(lambda:setattr(self,'dirty',True))
        row=QHBoxLayout();layout.addLayout(row);row.addWidget(button('新建摄像头',self.new,name='project_camera_new'));row.addWidget(button('保存摄像头资料',controller.save_camera,name='project_camera_save'));row.addWidget(button('刷新',controller.refresh_cameras))
        self.info=QLabel('摄像头属于当前项目，重命名不会改变UUID。');self.info.setWordWrap(True);layout.addWidget(self.info)
    def new(self):
        self.record=None;self.dirty=False;self.table.clearSelection();self.uuid.setText('新建时自动生成')
        for w in self.fields.values():w.clear()
        self.enabled.setChecked(True)
    def select(self):
        i=self.table.currentRow()
        if not 0<=i<len(self.rows):return
        self.record=self.rows[i];row=self.record;self.uuid.setText(row['id']);self.fields['name'].setText(row['name'])
        for k in ['code','location','equipment']:self.fields[k].setText(row['details'].get(k,''))
        self.enabled.setChecked(row['details'].get('enabled',True))
        self.dirty=False
