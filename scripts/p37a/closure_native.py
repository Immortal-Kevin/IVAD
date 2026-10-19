"""Native Windows GUI smoke on this round's copy, including sealed legacy playback."""
import ctypes,json,shutil,sys,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
OUT=ROOT/'artifacts/p37a-closure-20261019';COPY=OUT/'data-final/project-copy'
assert COPY.is_relative_to(OUT)
source=Path(json.loads((OUT/'before.json').read_text(encoding='utf8'))['root'])
if not (COPY/'frames').exists():shutil.copytree(source/'frames',COPY/'frames')
cache=next(p.parent for p in (source/'demos').glob('*/manifest.sha256'))
dst=COPY/'demos'/cache.name
if not dst.exists():shutil.copytree(cache,dst)
from PySide6.QtWidgets import QApplication
from ivad_app.core.application import ApplicationServices
from ivad_app.gui.main_window import MainWindow

def apartment():
    kind,qualifier=ctypes.c_int(),ctypes.c_int()
    result=ctypes.WinDLL('ole32').CoGetApartmentType(ctypes.byref(kind),ctypes.byref(qualifier))
    return dict(hresult=hex(result & 0xffffffff),kind=kind.value,qualifier=qualifier.value)

report=dict(com_before=apartment());app=QApplication(sys.argv);report.update(platform=app.platformName(),com_after=apartment())
assert report['platform']=='windows'
s=ApplicationServices(ROOT,OUT/'native-real-runtime');s.projects.open(str(COPY));s.training.rf._devices=[]
w=MainWindow(s,auto_probe=False);w.resize(1500,900);w.show()
def wait(test,seconds=15):
    until=time.monotonic()+seconds
    while not test():
        app.processEvents();time.sleep(.01)
        if time.monotonic()>until:raise TimeoutError('native GUI condition')
shots=OUT/'native-real-final';shots.mkdir(exist_ok=False)
try:
    t=w.pages['training'];wait(lambda:not t.busy and len(t.rows)>=2)
    assert all(r['backend']=='rfdetr' for r in t.rows)
    report['rf_training_rows']=len(t.rows)
    for key in ['training','dataset','models']:
        w.show_page(key);app.processEvents();assert w.grab().save(str(shots/(key+'.png')))
    w.show_page('offline');page=w.pages['offline'];wait(lambda:not page.busy)
    page.history.setCurrentIndex(page.history.findData(str(dst)));page.load_history()
    wait(lambda:page.player.loaded and page.manifest is not None and page.player.last_image is not None)
    assert page.manifest['id']==cache.name and not page.start_button.isEnabled()
    page.player.command('step',1);wait(lambda:page.player.position_us>0)
    previous=page.player.position_us;page.player.toggle();wait(lambda:page.player.position_us>previous);page.player.toggle()
    report['cache']=dict(id=page.manifest['id'],frames=len(page.manifest['frames']),model_id=page.manifest['model_id'],legacy_playback_without_worker=True,decoded_frame=True,step_and_play_pause=True,position_us=page.player.position_us)
    assert w.grab().save(str(shots/'offline-history.png'))
    report['status']='PASS'
finally:
    w.close();wait(lambda:w.may_close,40)
    (OUT/'native-real-final.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps(report,ensure_ascii=False))
