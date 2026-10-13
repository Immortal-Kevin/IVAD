"""原始图片像素几何校验；拒绝越界、退化与自交多边形。"""
import math
from ivad_app.core.contracts import AppError

def polygon_area(points):
    return abs(sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1])))/2

def _cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
def _on(a,b,c): return abs(_cross(a,b,c))<1e-8 and min(a[0],b[0])-1e-8<=c[0]<=max(a[0],b[0])+1e-8 and min(a[1],b[1])-1e-8<=c[1]<=max(a[1],b[1])+1e-8
def intersects(a,b,c,d):
    return (_cross(a,b,c)*_cross(a,b,d)<0 and _cross(c,d,a)*_cross(c,d,b)<0) or any([_on(a,b,c),_on(a,b,d),_on(c,d,a),_on(c,d,b)])

def validate_geometry(kind, geometry, width, height):
    try:
        if kind in {'box','roi_box'}:
            if len(geometry)!=4: raise ValueError()
            x,y,w,h = map(float,geometry)
            if not all(math.isfinite(v) for v in [x,y,w,h]) or min(x,y)<0 or min(w,h)<=0 or x+w>width+1e-6 or y+h>height+1e-6: raise ValueError()
        elif kind in {'polygon','roi_polygon'}:
            if not 3<=len(geometry)<=500 or any(len(p)!=2 for p in geometry): raise ValueError()
            pts = [list(map(float,p)) for p in geometry]
            if len(set(map(tuple,pts))) != len(pts) or polygon_area(pts)<1: raise ValueError()
            if any(not all(math.isfinite(v) for v in p) or not 0<=p[0]<=width or not 0<=p[1]<=height for p in pts): raise ValueError()
            for i in range(len(pts)):
                for j in range(i+1,len(pts)):
                    if j in {i,(i+1)%len(pts)} or i==(j+1)%len(pts): continue
                    if intersects(pts[i],pts[(i+1)%len(pts)],pts[j],pts[(j+1)%len(pts)]): raise ValueError()
        else: raise ValueError()
    except (ValueError, TypeError, IndexError):
        raise AppError('GEOMETRY_INVALID', '标注几何无效：检查坐标越界、面积、顶点数量或多边形自交。')

def bounding_box(kind, geom):
    if kind=='box': return list(geom)
    xs,ys=zip(*geom); return [min(xs),min(ys),max(xs)-min(xs),max(ys)-min(ys)]
