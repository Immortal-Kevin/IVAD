from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog,QVBoxLayout,QHBoxLayout,QFormLayout,QListWidget,QLineEdit,QPlainTextEdit,QComboBox,QCheckBox,QLabel
from ivad_app.gui.pages import button

class LabelDialog(QDialog):
    def __init__(self,service,runner,root,on_changed,parent=None):
        super().__init__(parent);self.setWindowTitle('故障类型与标签库');self.resize(700,520)
        self.service,self.runner,self.root,self.on_changed=service,runner,root,on_changed;self.records=[];self.current=None
        layout=QVBoxLayout(self);layout.addWidget(QLabel('类别UUID稳定；以下初始类别仅是可编辑模板，不代表有可用模型。'))
        row=QHBoxLayout();self.list=QListWidget();self.list.currentRowChanged.connect(self.select);row.addWidget(self.list,1)
        form=QFormLayout();self.name=QLineEdit();self.name.setObjectName('label_name');self.description=QPlainTextEdit();self.description.setMaximumHeight(100)
        self.device=QLineEdit();self.parent_label=QComboBox();self.kind=QComboBox()
        for text,value in [('矩形框','box'),('多边形','polygon'),('整帧','image'),('片段','clip')]:self.kind.addItem(text,value)
        self.enabled=QCheckBox('启用类别');self.enabled.setChecked(True)
        for name,widget in [('名称',self.name),('描述',self.description),('设备类型',self.device),('父级类别',self.parent_label),('默认标注类型',self.kind),('',self.enabled)]:form.addRow(name,widget)
        row.addLayout(form,2);layout.addLayout(row,1);buttons=QHBoxLayout()
        buttons.addWidget(button('新类别',self.new,name='new_label'));buttons.addWidget(button('保存类别',self.save,True,'save_label'));buttons.addWidget(button('删除未引用类别',self.delete));buttons.addWidget(button('关闭',self.accept));layout.addLayout(buttons)
        self.message=QLabel('');self.message.setWordWrap(True);layout.addWidget(self.message);self.reload()
    def reload(self):
        def done(rows,error):
            if error:self.message.setText(error);return
            self.records=rows;self.list.blockSignals(True);self.list.clear()
            for row in rows:self.list.addItem(row['name']+('（停用）' if not row['enabled'] else ''))
            self.list.blockSignals(False);self.new();self.on_changed()
        self.runner.run(lambda:self.service.labels(self.root),done)
    def new(self):
        self.current=None;self.list.setCurrentRow(-1);self.name.clear();self.description.clear();self.device.clear();self.enabled.setChecked(True);self.kind.setCurrentIndex(0);self.parents()
    def parents(self):
        self.parent_label.clear();self.parent_label.addItem('无父级',None)
        for row in self.records:
            if not self.current or row['id']!=self.current['id']:self.parent_label.addItem(row['name'],row['id'])
    def select(self,index):
        if not 0<=index<len(self.records):return
        row=self.records[index];self.current=row;self.name.setText(row['name']);self.description.setPlainText(row['description']);self.device.setText(row['device_type']);self.enabled.setChecked(bool(row['enabled']));self.parents()
        self.parent_label.setCurrentIndex(max(0,self.parent_label.findData(row['parent_id'])));self.kind.setCurrentIndex(max(0,self.kind.findData(row['annotation_type'])))
    def save(self):
        value={'name':self.name.text(),'description':self.description.toPlainText(),'device_type':self.device.text(),'parent_id':self.parent_label.currentData(),'annotation_type':self.kind.currentData(),'enabled':self.enabled.isChecked()}
        if self.current:value.update(id=self.current['id'],revision=self.current['revision'])
        def done(row,error):
            self.message.setText(error or '类别已保存。')
            if not error:self.reload()
        self.runner.run(lambda:self.service.save_label(value,self.root),done)
    def delete(self):
        if not self.current:self.message.setText('请先选择类别。');return
        label_id=self.current['id']
        def done(_,error):
            self.message.setText(error or '未引用类别已删除。')
            if not error:self.reload()
        self.runner.run(lambda:self.service.delete_label(label_id,self.root),done)
