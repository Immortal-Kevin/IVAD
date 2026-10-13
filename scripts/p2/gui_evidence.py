"""Persistent lawful sample project and actual screenshots at requested Qt scale."""
import json,os,sys,threading
from pathlib import Path
from uuid import uuid4
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication,QScrollArea
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow
from scripts.p2.make_samples import make_all
class Context:
    job_id='evidence'
    cancel=threading.Event()
    def check(self):pass
    def progress(self,value):pass
    def log(self,value):pass
out=ROOT/'artifacts/p2';label=os.environ.get('IVAD_EVIDENCE_LABEL','native');base=out/('gui-evidence-'+label);base.mkdir(parents=True,exist_ok=True)
app=QApplication([]);services=ApplicationServices(ROOT,base/'application')
existing=list(base.glob('IVAD-*/project.json'))
if existing:project=services.projects.open(str(existing[0].parent))
else:
    project=services.projects.create(str(base),'P2合法样本与人工标注')
if not services.datasets.versions(project.root):
    samples=make_all(out/'samples');imported=services.media.import_batch(Context(),{'root':project.root,'paths':[str(samples/name) for name in ['sample.mp4','sample.mov','sample.mkv']],'mode':'COPY'})
    category=services.annotations.labels()[0];frames=[]
    for mid in imported['imported']+[r['id'] for r in imported['duplicates']]:
        extracted=services.media.extract(Context(),{'root':project.root,'media_id':mid,'options':{'mode':'fixed','start_us':0,'end_us':500000,'interval_us':300000,'maximum':2,'format':'PNG'}})
        fid=extracted['frames'][0];frames.append(fid)
        services.annotations.save(fid,{'objects':[{'id':str(uuid4()),'kind':'polygon','geometry':[[40,40],[140,40],[130,120],[40,110]],'label_id':category['id']}],'image_tag':'ABNORMAL'},'APPROVED',0,[{'id':str(uuid4()),'kind':'roi_box','geometry':[10,10,280,150]}],0)
    version=services.datasets.freeze(Context(),{'root':project.root,'name':'合法样本分割数据集','frame_ids':frames})
    for fmt in ['yolo_detect','yolo_segment','coco','ivad_native']:services.datasets.export(Context(),{'root':project.root,'version_id':version['version_id'],'format':fmt,'parent':str(base)})
window=MainWindow(services,auto_probe=False);window.show();window.show_page('annotation')
def capture():
    if window.p2.refreshing or window.p2.annotation.loading or not window.p2.annotation.frame_id:QTimer.singleShot(100,capture);return
    window.grab().save(str(out/f'gui-annotation-{label}.png'))
    window.show_page('dataset');app.processEvents();window.grab().save(str(out/f'gui-dataset-top-{label}.png'))
    window.p2.dataset.versions.selectRow(0);bar=window.p2.dataset.findChild(QScrollArea).verticalScrollBar();bar.setValue(bar.maximum());app.processEvents();window.grab().save(str(out/f'gui-dataset-{label}.png'))
    window.show_page('media');window.p2.media.table.selectRow(0);QTimer.singleShot(500,media_capture)
def media_capture():
    if window.p2.media.player.last_image is None:QTimer.singleShot(100,media_capture);return
    window.grab().save(str(out/f'gui-media-{label}.png'));screen=app.primaryScreen()
    (out/f'gui-dpi-{label}.json').write_text(json.dumps({'device_pixel_ratio':screen.devicePixelRatio(),'logical_dpi':screen.logicalDotsPerInch(),'window':[window.width(),window.height()],'annotation_properties_scroll':True,'project':project.root,'data_check':services.media.check(project.root)},ensure_ascii=False,indent=2),encoding='utf-8')
    window.close()
QTimer.singleShot(400,capture);QTimer.singleShot(45000,window.close);app.exec()
