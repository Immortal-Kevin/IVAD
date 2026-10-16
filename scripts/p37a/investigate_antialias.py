import sys,os
from pathlib import Path
root=Path(__file__).resolve().parents[2];out=root/'artifacts/p37a-20261016/parity/predict-antialias';os.environ['MPLCONFIGDIR']=str(out/'mpl')
sys.path.insert(0,str(root/'experiments/p36_rfdetr'))
import rfdetr.detr as detr
original=detr.F.resize
def resize(*a,**kw):kw['antialias']=True;return original(*a,**kw)
detr.F.resize=resize
from evaluate import run
run(str(root/'artifacts/p36-rfdetr-20261016/engineering-seeded-run/checkpoint_best_total.pth'),str(root/'artifacts/p36-rfdetr-20261016/coco'),str(out))
