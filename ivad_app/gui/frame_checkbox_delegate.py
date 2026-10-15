"""High-contrast list indicators with explicit hover and DPI-independent painter strokes."""
from PySide6.QtCore import Qt,QEvent,QPersistentModelIndex,QPointF
from PySide6.QtGui import QColor,QPen,QPainter,QPainterPath
from PySide6.QtWidgets import QStyledItemDelegate,QStyle,QStyleOptionViewItem

class FrameCheckboxDelegate(QStyledItemDelegate):
    def __init__(self,view):
        super().__init__(view);self.view=view;self.hovered=None;view.viewport().installEventFilter(self)
    def eventFilter(self,obj,event):
        if event.type()==QEvent.Type.MouseMove:
            index=self.view.indexAt(event.position().toPoint());value=QPersistentModelIndex(index) if index.isValid() else None
            if value!=self.hovered:self.hovered=value;self.view.viewport().update()
        elif event.type()==QEvent.Type.Leave:
            self.hovered=None;self.view.viewport().update()
        return False
    def paint(self,painter,option,index):
        super().paint(painter,option,index)
        state=index.data(Qt.ItemDataRole.CheckStateRole)
        if state is None:return
        opt=QStyleOptionViewItem(option);self.initStyleOption(opt,index)
        rect=self.view.style().subElementRect(QStyle.SubElement.SE_ItemViewItemCheckIndicator,opt,self.view).adjusted(1,1,-1,-1)
        enabled=bool(index.flags()&Qt.ItemFlag.ItemIsEnabled) and self.view.isEnabled();checked=state==Qt.CheckState.Checked.value;hover=enabled and self.hovered==index
        fill='#8396aa' if not enabled and checked else '#e7ebf0' if not enabled else '#16538e' if checked and hover else '#2166aa' if checked else '#e4f0ff' if hover else '#ffffff'
        painter.save();painter.setRenderHint(QPainter.RenderHint.Antialiasing);painter.setBrush(QColor(fill));painter.setPen(QPen(QColor('#8d9aaa' if not enabled else '#155a9e' if hover else '#3c5575'),2));painter.drawRoundedRect(rect,3,3)
        if checked:
            path=QPainterPath(QPointF(rect.left()+rect.width()*.22,rect.top()+rect.height()*.52));path.lineTo(rect.left()+rect.width()*.43,rect.top()+rect.height()*.73);path.lineTo(rect.left()+rect.width()*.82,rect.top()+rect.height()*.25)
            painter.setPen(QPen(QColor('white'),3,Qt.PenStyle.SolidLine,Qt.PenCapStyle.RoundCap,Qt.PenJoinStyle.RoundJoin));painter.drawPath(path)
        painter.restore()
