from PySide6.QtCore import Qt,QPointF
from PySide6.QtGui import QImage,QColor
from uuid import uuid4
import pytest
from ivad_app.gui.annotation_canvas import AnnotationCanvas

def scene_point(canvas,x,y):return canvas.mapFromScene(QPointF(x,y))
def drag(qtbot,canvas,a,b):
    qtbot.mousePress(canvas.viewport(),Qt.MouseButton.LeftButton,pos=scene_point(canvas,*a));qtbot.mouseMove(canvas.viewport(),scene_point(canvas,*b));qtbot.mouseRelease(canvas.viewport(),Qt.MouseButton.LeftButton,pos=scene_point(canvas,*b));qtbot.wait(20)

@pytest.fixture
def canvas(qtbot):
    widget=AnnotationCanvas();qtbot.addWidget(widget);widget.resize(800,480);widget.show()
    image=QImage(320,180,QImage.Format.Format_RGB888);image.fill(QColor('gray'));widget.set_image(image);widget.label_id=str(uuid4());qtbot.wait(50);return widget

def test_box_move_resize_delete_undo_redo_raw_coordinates(qtbot,canvas):
    canvas.set_tool('box');drag(qtbot,canvas,(20,30),(100,80));assert canvas.shapes[0]['geometry']==pytest.approx([20,30,80,50],abs=1)
    canvas.set_tool('select');drag(qtbot,canvas,(60,50),(70,60));assert canvas.shapes[0]['geometry'][:2]==pytest.approx([30,40],abs=1)
    corner=canvas.vertices(canvas.shapes[0])[2];drag(qtbot,canvas,corner,(130,110));assert canvas.shapes[0]['geometry'][2:]==pytest.approx([100,70],abs=1)
    canvas.delete_selected();assert not canvas.shapes;canvas.undo();assert len(canvas.shapes)==1;canvas.redo();assert not canvas.shapes

def test_polygon_vertex_roi_zoom_coordinates(qtbot,canvas):
    canvas.set_tool('polygon')
    for point in [(10,10),(100,10),(100,100)]:qtbot.mouseClick(canvas.viewport(),Qt.MouseButton.LeftButton,pos=scene_point(canvas,*point))
    qtbot.keyClick(canvas,Qt.Key.Key_Return);assert canvas.shapes[0]['kind']=='polygon'
    canvas.set_tool('select');drag(qtbot,canvas,(100,10),(120,20));assert canvas.shapes[0]['geometry'][1]==pytest.approx([120,20],abs=1)
    canvas.set_tool('roi_box');drag(qtbot,canvas,(140,40),(220,120));assert canvas.shapes[1]['kind']=='roi_box'
    canvas.scale(1.5,1.5);canvas.auto_fit=False;canvas.set_tool('box');drag(qtbot,canvas,(30,110),(80,160));assert canvas.shapes[-1]['geometry']==pytest.approx([30,110,50,50],abs=1)

def test_invalid_self_intersecting_polygon_rejected(qtbot,canvas):
    errors=[];canvas.error.connect(errors.append);canvas.add('polygon',[[10,10],[100,100],[10,100],[100,10]])
    assert not canvas.shapes and errors
