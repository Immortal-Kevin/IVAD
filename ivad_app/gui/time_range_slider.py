"""Two-handle, microsecond-based range; no video decoding or inference here."""
from PySide6.QtCore import Qt,Signal,QSize,QRectF
from PySide6.QtGui import QPainter,QColor,QPen
from PySide6.QtWidgets import QWidget

class TimeRangeSlider(QWidget):
    rangeChanged=Signal(object,object)
    seekRequested=Signal(object)
    def __init__(self,parent=None):
        super().__init__(parent);self.duration=1;self.minimum=1;self.start=0;self.end=1;self.active=0;self.dragging=False;self.setFocusPolicy(Qt.FocusPolicy.StrongFocus);self.setMinimumHeight(36)
        self.setToolTip('拖动起点/终点；点击轨道移动最近的手柄。空格切换手柄，左右键微调1毫秒，Shift+左右键100毫秒。范围使用视频相对时间，不启动AI。');self.setAccessibleName('视频起止双手柄范围')
    def sizeHint(self):return QSize(320,38)
    def configure(self,duration,minimum=1000):
        self.duration=max(1,int(duration));self.minimum=min(self.duration,max(1,int(minimum)));self.set_range(0,min(self.duration,max(self.minimum,10000000)),emit=False)
    def set_range(self,start,end,*,emit=True,handle=None):
        start=max(0,min(round(int(start)/1000)*1000,self.duration-self.minimum));end=max(self.minimum,min(round(int(end)/1000)*1000,self.duration))
        if end-start<self.minimum:
            if handle==1:end=min(self.duration,start+self.minimum)
            else:start=max(0,end-self.minimum)
        changed=(start,end)!=(self.start,self.end);self.start,self.end=start,end;self.update()
        if emit and changed:self.rangeChanged.emit(start,end)
    def x_for(self,value):return 12+(self.width()-24)*value/self.duration
    def value_for(self,x):return round(max(0,min(1,(x-12)/max(1,self.width()-24)))*self.duration)
    def paintEvent(self,event):
        p=QPainter(self);p.setRenderHint(QPainter.RenderHint.Antialiasing);y=self.height()/2
        p.setPen(QPen(QColor('#c8d5e4'),6));p.drawLine(12,int(y),self.width()-12,int(y));p.setPen(QPen(QColor('#2488bb'),6));p.drawLine(int(self.x_for(self.start)),int(y),int(self.x_for(self.end)),int(y))
        for i,value in enumerate([self.start,self.end]):
            p.setPen(QPen(QColor('#153e64'),2 if self.active==i and self.hasFocus() else 1));p.setBrush(QColor('#176a94' if self.isEnabled() else '#9caabc'));p.drawRoundedRect(QRectF(self.x_for(value)-6,y-11,12,22),3,3)
    def move_handle(self,value):
        self.set_range(value if self.active==0 else self.start,value if self.active==1 else self.end,handle=self.active);self.seekRequested.emit(self.start if self.active==0 else self.end)
    def mousePressEvent(self,event):
        if event.button()!=Qt.MouseButton.LeftButton:return
        self.setFocus();x=event.position().x();self.active=0 if abs(x-self.x_for(self.start))<=abs(x-self.x_for(self.end)) else 1;self.dragging=True;self.move_handle(self.value_for(x))
    def mouseMoveEvent(self,event):
        if self.dragging:self.move_handle(self.value_for(event.position().x()))
    def mouseReleaseEvent(self,event):
        if self.dragging:self.move_handle(self.value_for(event.position().x()));self.dragging=False
    def keyPressEvent(self,event):
        if event.key()==Qt.Key.Key_Space:self.active=1-self.active;self.update();return
        if event.key() in {Qt.Key.Key_Left,Qt.Key.Key_Right}:
            step=100000 if event.modifiers()&Qt.KeyboardModifier.ShiftModifier else 1000;value=self.start if self.active==0 else self.end;self.move_handle(value+(-step if event.key()==Qt.Key.Key_Left else step));return
        super().keyPressEvent(event)
