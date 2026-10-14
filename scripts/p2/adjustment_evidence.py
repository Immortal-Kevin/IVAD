"""P2 adjustment evidence only; never overwrite prior P0/P1/P2 artifacts."""
import os,sys,json,threading
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from PySide6.QtCore import QTimer,Qt,QPoint,QPointF,QEvent
from PySide6.QtGui import QEnterEvent,QMouseEvent
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow
from scripts.p2.make_samples import make_all
class Context:
    job_id='adjustment-evidence';cancel=threading.Event()
    def check(self):pass
    def progress(self,value):pass
    def log(self,value):pass
out=ROOT/'artifacts/p2-adjustment';label=os.environ.get('IVAD_EVIDENCE_LABEL','native');base=out/'demo';base.mkdir(parents=True,exist_ok=True)
app=QApplication([]);services=ApplicationServices(ROOT,base/'application')
existing=list(base.glob('IVAD-*/project.json'))
if existing:project=services.projects.open(str(existing[0].parent))
else:
    project=services.projects.create(str(base),'P2补充界面与人工片段样例')
    samples=make_all(out/'samples')
    imported=services.media.import_batch(Context(),{'root':project.root,'paths':[str(p) for p in sorted(samples.glob('*')) if p.name!='corrupt.mp4'],'mode':'COPY'})
    services.media.save_video_clip(Context(),{'root':project.root,'media_id':imported['imported'][0],'start_us':200000,'end_us':800000,'name':'CLIP_人工故障时间范围.mp4'})
window=MainWindow(services,auto_probe=False);available=app.primaryScreen().availableGeometry();window.resize(min(1440,available.width()-30),min(760,available.height()-65));window.show();window.show_page('media');media=window.p2.media
def capture():
    if window.p2.refreshing or not media.media_rows:QTimer.singleShot(100,capture);return
    media.table.selectRow(0);QTimer.singleShot(300,ready)
def ready():
    if media.player.last_image is None:QTimer.singleShot(100,ready);return
    app.processEvents();window.grab().save(str(out/f'ui-player-{label}.png'))
    media.tabs.setCurrentIndex(1);QTest.qWait(100);window.grab().save(str(out/f'ui-sampling-{label}.png'))
    media.tabs.setCurrentIndex(3);QTest.qWait(100);window.grab().save(str(out/f'ui-save-clip-{label}.png'))
    bar=media.tabs.tabBar();pos=QPointF(bar.tabRect(0).center());gp=QPointF(bar.mapToGlobal(pos.toPoint()))
    QApplication.sendEvent(bar,QEnterEvent(pos,pos,gp));QApplication.sendEvent(bar,QMouseEvent(QEvent.Type.MouseMove,pos,gp,Qt.MouseButton.NoButton,Qt.MouseButton.NoButton,Qt.KeyboardModifier.NoModifier));app.processEvents();bar.grab().save(str(out/f'tabs-hover-{label}.png'))
    screen=app.primaryScreen();data={'dpr':screen.devicePixelRatio(),'window':[window.width(),window.height()],'table':[media.table.width(),media.table.height()],'old_max_table_height':160,'rows':media.table.rowCount(),'split_sizes':media.splitter.sizes(),'tab_widths':[bar.tabRect(i).width() for i in range(bar.count())],'project':project.root,'media_check':services.media.check(project.root)}
    (out/f'ui-{label}.json').write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');window.close()
QTimer.singleShot(400,capture);QTimer.singleShot(30000,window.close);app.exec()
