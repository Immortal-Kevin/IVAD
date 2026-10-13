"""Qt场景坐标=原始图片像素；缩放/DPI仅作用于显示变换。"""
import copy, math
from uuid import uuid4
from PySide6.QtCore import Qt, Signal, QPointF, QRectF
from PySide6.QtGui import QPixmap, QPainterPath, QColor, QPen, QBrush, QPainter
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from ivad_app.annotations.geometry import validate_geometry
from ivad_app.core.contracts import AppError

class AnnotationCanvas(QGraphicsView):
    changed=Signal()
    selected=Signal(object)
    error=Signal(str)
    def __init__(self):
        super().__init__();self.setObjectName('annotation_canvas')
        self.setScene(QGraphicsScene(self));self.setRenderHints(QPainter.RenderHint.Antialiasing|QPainter.RenderHint.SmoothPixmapTransform)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.pixmap=None;self.width_px=self.height_px=0;self.shapes=[];self.selected_index=None
        self.tool='select';self.label_id=None;self.label_names={};self.points=[];self.drag=None;self.pan=None
        self.history=[[]];self.history_index=0;self.auto_fit=True

    def set_image(self,image):
        self.pixmap=QPixmap.fromImage(image);self.width_px=image.width();self.height_px=image.height()
        self.points=[];self.drag=None;self.selected_index=None;self.auto_fit=True;self.render();self.fit()

    def set_shapes(self,shapes):
        self.shapes=copy.deepcopy(shapes);self.history=[copy.deepcopy(shapes)];self.history_index=0;self.selected_index=None;self.render()

    def set_tool(self,tool):self.tool=tool;self.points=[];self.drag=None;self.render()
    def fit(self):
        if self.pixmap:
            self.fitInView(QRectF(0,0,self.width_px,self.height_px),Qt.AspectRatioMode.KeepAspectRatio);self.auto_fit=True;self.render()
    def resizeEvent(self,event):
        super().resizeEvent(event)
        if self.auto_fit:self.fit()
    def wheelEvent(self,event):
        factor=1.15 if event.angleDelta().y()>0 else 1/1.15
        if 0.03<self.transform().m11()*factor<30:self.scale(factor,factor);self.auto_fit=False;self.render()
        event.accept()
    def point(self,event):
        p=self.mapToScene(event.position().toPoint());return [max(0,min(self.width_px,p.x())),max(0,min(self.height_px,p.y()))]
    @staticmethod
    def path(shape):
        path=QPainterPath();g=shape['geometry']
        if shape['kind'] in {'box','roi_box'}:path.addRect(QRectF(*g))
        else:
            path.moveTo(*g[0])
            for point in g[1:]:path.lineTo(*point)
            path.closeSubpath()
        return path
    @staticmethod
    def vertices(shape):
        g=shape['geometry']
        if shape['kind'] in {'box','roi_box'}:
            x,y,w,h=g;return [[x,y],[x+w,y],[x+w,y+h],[x,y+h]]
        return g
    def render(self):
        self.scene().clear()
        if not self.pixmap:return
        self.scene().addPixmap(self.pixmap);self.scene().setSceneRect(0,0,self.width_px,self.height_px)
        radius=4/max(self.transform().m11(),.01)
        for index,shape in enumerate(self.shapes):
            color=QColor('#d89624' if shape['kind'].startswith('roi_') else '#29b5d3')
            pen=QPen(color,2);pen.setCosmetic(True)
            self.scene().addPath(self.path(shape),pen,QBrush(QColor(color.red(),color.green(),color.blue(),45)))
            if index==self.selected_index:
                for x,y in self.vertices(shape):self.scene().addEllipse(x-radius,y-radius,2*radius,2*radius,QPen(Qt.GlobalColor.white),QBrush(color))
        if self.points:
            path=QPainterPath();path.moveTo(*self.points[0])
            for point in self.points[1:]:path.lineTo(*point)
            pen=QPen(QColor('#ffff00'),2);pen.setCosmetic(True);self.scene().addPath(path,pen)
        if self.drag and self.drag['mode']=='draw_box':
            a,b=self.drag['start'],self.drag.get('end',self.drag['start'])
            self.scene().addRect(QRectF(QPointF(*a),QPointF(*b)).normalized(),QPen(QColor('#ffff00')))

    def commit(self):
        try:
            for shape in self.shapes:validate_geometry(shape['kind'],shape['geometry'],self.width_px,self.height_px)
        except AppError as exc:
            self.shapes=copy.deepcopy(self.history[self.history_index]);self.error.emit(exc.message);self.render();return
        if self.shapes!=self.history[self.history_index]:
            self.history=self.history[:self.history_index+1]+[copy.deepcopy(self.shapes)]
            if len(self.history)>100:self.history=self.history[-100:]
            self.history_index=len(self.history)-1;self.changed.emit()
        self.render();self.selected.emit(self.shapes[self.selected_index] if self.selected_index is not None and self.selected_index<len(self.shapes) else None)

    def add(self,kind,geometry):
        if not kind.startswith('roi_') and not self.label_id:self.error.emit('请先选择故障类别。');return
        self.shapes.append({'id':str(uuid4()),'kind':kind,'geometry':geometry,'label_id':None if kind.startswith('roi_') else self.label_id,'source':'Human Generated'})
        self.selected_index=len(self.shapes)-1;self.commit()

    def mousePressEvent(self,event):
        if not self.pixmap:return
        if event.button()==Qt.MouseButton.MiddleButton:
            self.pan=event.position().toPoint();return
        if event.button()==Qt.MouseButton.RightButton and self.points:self.finish_polygon();return
        if event.button()!=Qt.MouseButton.LeftButton:return super().mousePressEvent(event)
        self.setFocus();point=self.point(event)
        if self.tool in {'box','roi_box'}:
            self.drag={'mode':'draw_box','start':point,'end':point};return
        if self.tool in {'polygon','roi_polygon'}:
            self.points.append(point);self.render();return
        radius=7/max(self.transform().m11(),.01)
        if self.selected_index is not None and self.selected_index<len(self.shapes):
            for vertex,p in enumerate(self.vertices(self.shapes[self.selected_index])):
                if math.dist(point,p)<=radius:
                    self.drag={'mode':'vertex','index':self.selected_index,'vertex':vertex,'before':copy.deepcopy(self.shapes[self.selected_index]),'start':point};return
        hit=next((i for i in range(len(self.shapes)-1,-1,-1) if self.path(self.shapes[i]).contains(QPointF(*point))),None)
        self.selected_index=hit
        if hit is not None:self.drag={'mode':'move','index':hit,'before':copy.deepcopy(self.shapes[hit]),'start':point}
        self.render();self.selected.emit(self.shapes[hit] if hit is not None else None)

    def mouseMoveEvent(self,event):
        if self.pan is not None:
            delta=event.position().toPoint()-self.pan;self.pan=event.position().toPoint()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value()-delta.x());self.verticalScrollBar().setValue(self.verticalScrollBar().value()-delta.y());return
        if not self.drag:return super().mouseMoveEvent(event)
        point=self.point(event);drag=self.drag
        if drag['mode']=='draw_box':drag['end']=point;self.render();return
        shape=self.shapes[drag['index']];before=drag['before'];kind=shape['kind']
        if drag['mode']=='vertex':
            if kind in {'box','roi_box'}:
                opposite=self.vertices(before)[(drag['vertex']+2)%4];rectangle=QRectF(QPointF(*opposite),QPointF(*point)).normalized()
                shape['geometry']=[rectangle.x(),rectangle.y(),rectangle.width(),rectangle.height()]
            else:
                shape['geometry']=copy.deepcopy(before['geometry']);shape['geometry'][drag['vertex']]=point
        else:
            vertices=self.vertices(before);xs,ys=zip(*vertices);dx=point[0]-drag['start'][0];dy=point[1]-drag['start'][1]
            dx=max(-min(xs),min(dx,self.width_px-max(xs)));dy=max(-min(ys),min(dy,self.height_px-max(ys)))
            if kind in {'box','roi_box'}:x,y,w,h=before['geometry'];shape['geometry']=[x+dx,y+dy,w,h]
            else:shape['geometry']=[[x+dx,y+dy] for x,y in before['geometry']]
        self.render()

    def mouseReleaseEvent(self,event):
        if event.button()==Qt.MouseButton.MiddleButton:self.pan=None;return
        if self.drag:
            drag=self.drag;self.drag=None
            if drag['mode']=='draw_box':
                rectangle=QRectF(QPointF(*drag['start']),QPointF(*self.point(event))).normalized()
                self.add(self.tool,[rectangle.x(),rectangle.y(),rectangle.width(),rectangle.height()])
            else:self.commit()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self,event):
        if self.tool in {'polygon','roi_polygon'}:self.finish_polygon();return
        super().mouseDoubleClickEvent(event)
    def finish_polygon(self):
        points=self.points;self.points=[]
        unique=[]
        for p in points:
            if not unique or p!=unique[-1]:unique.append(p)
        if len(unique)>1 and unique[0]==unique[-1]:unique.pop()
        if len(unique)<3:self.error.emit('多边形至少需要3个不同顶点。');self.render();return
        self.add(self.tool,unique)
    def delete_selected(self):
        if self.selected_index is not None and self.selected_index<len(self.shapes):
            self.shapes.pop(self.selected_index);self.selected_index=None;self.commit()
    def undo(self):
        if self.history_index>0:self.history_index-=1;self.shapes=copy.deepcopy(self.history[self.history_index]);self.selected_index=None;self.render();self.changed.emit();self.selected.emit(None)
    def redo(self):
        if self.history_index+1<len(self.history):self.history_index+=1;self.shapes=copy.deepcopy(self.history[self.history_index]);self.selected_index=None;self.render();self.changed.emit();self.selected.emit(None)
    def keyPressEvent(self,event):
        if event.key() in {Qt.Key.Key_Return,Qt.Key.Key_Enter} and self.points:self.finish_polygon();return
        if event.key()==Qt.Key.Key_Escape:self.points=[];self.drag=None;self.render();return
        if event.key()==Qt.Key.Key_Delete:self.delete_selected();return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key()==Qt.Key.Key_Z:self.undo();return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier and event.key()==Qt.Key.Key_Y:self.redo();return
        super().keyPressEvent(event)
