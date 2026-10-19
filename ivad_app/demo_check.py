"""Explicit local-candidate diagnostic; never runs on ordinary startup.

Uses synthetic inputs supplied outside the application directory. No fixtures,
test framework, screenshots or historical project data are shipped with the app.
"""
import ctypes
from ctypes import wintypes
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
from uuid import uuid4

from PySide6.QtCore import Qt, QEvent, QPointF, qVersion
from PySide6.QtGui import QMouseEvent, QKeyEvent
from PySide6.QtWidgets import QApplication, QPushButton, QFileDialog, QMessageBox, QScrollArea
from ivad_app.core.application import ApplicationServices
from ivad_app.core.contracts import AppError
from ivad_app.gui.main_window import MainWindow


def loaded_dlls():
    kernel = ctypes.WinDLL('kernel32'); psapi = ctypes.WinDLL('psapi')
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    handle = kernel.GetCurrentProcess(); modules = (ctypes.c_void_p * 2048)(); needed = wintypes.DWORD()
    psapi.EnumProcessModules.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    psapi.GetModuleFileNameExW.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.LPWSTR, wintypes.DWORD]
    if not psapi.EnumProcessModules(handle, modules, ctypes.sizeof(modules), ctypes.byref(needed)):
        raise ctypes.WinError()
    result = []
    for module in modules[:needed.value // ctypes.sizeof(ctypes.c_void_p)]:
        name = ctypes.create_unicode_buffer(32768)
        if psapi.GetModuleFileNameExW(handle, module, name, len(name)):
            result.append(name.value)
    return result


def run(directory):
    out = Path(directory).resolve()
    assert out.is_dir(), 'Create an explicit isolated validation directory first'
    restart = '--restart-check' in sys.argv
    result_file = out / ('restart-results.json' if restart else 'results.json')
    assert not result_file.exists(), 'Never overwrite validation evidence'
    result = dict(status='RUNNING', frozen=bool(getattr(sys, 'frozen', False)), steps=[],
                  scope='Actual EXE; automated native Qt events, injected file selections; same developer PC, not clean VM')
    result['qt_runtime']=qVersion()
    app = QApplication.instance() or QApplication(sys.argv[:1])
    services = window = None

    def wait(condition, seconds=35):
        until = time.monotonic() + seconds
        while time.monotonic() < until:
            app.processEvents(); time.sleep(.015)
            if condition():return
        raise AssertionError('GUI wait timed out; last steps: ' + str(result['steps'][-2:]))

    def record(name):
        result['steps'].append(dict(name=name, status='PASS'))
        (out / ('restart-progress.json' if restart else 'progress.json')).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf8')

    def click(parent, object_name):
        widget = parent.findChild(QPushButton, object_name)
        assert widget is not None, object_name
        ancestor = widget.parentWidget()
        while ancestor:
            if isinstance(ancestor, QScrollArea):ancestor.ensureWidgetVisible(widget);break
            ancestor = ancestor.parentWidget()
        app.processEvents(); assert widget.isEnabled(), object_name
        widget.click(); app.processEvents()

    def close():
        window.close(); wait(lambda:window.may_close); services.close()

    def mouse(canvas, kind, x, y):
        pos = canvas.mapFromScene(QPointF(x, y)); global_pos = canvas.viewport().mapToGlobal(pos)
        button = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseMove else Qt.MouseButton.LeftButton
        buttons = Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton
        app.sendEvent(canvas.viewport(), QMouseEvent(kind, QPointF(pos), QPointF(global_pos), button, buttons, Qt.KeyboardModifier.NoModifier))
        app.processEvents()

    try:
        assert result['frozen'], 'Must run from the real candidate EXE'
        services = ApplicationServices(Path(sys._MEIPASS), out / ('restart-appdata' if restart else 'appdata'))
        assert services.demo_lite and services.lite
        window = MainWindow(services, auto_probe=False); window.resize(1440, 960);window.show()
        wait(lambda:not window.refresh_busy)
        record('EXE GUI startup with no development Python PATH and no CUDA')
        if restart:
            previous = json.loads((out/'results.json').read_text(encoding='utf8'))
            assert previous['status']=='PASS'
            window.open_project(previous['project_root']); wait(lambda:services.projects.current and not window.project_busy)
            assert len(services.datasets.versions())==1
            saved = services.annotations.load(previous['annotation_frame_id'])
            assert {o['kind'] for o in saved['payload']['objects']}=={'box','polygon'}
            assert len(services.media.frames())>=8
            record('Separate EXE process reopens persisted frames, box/polygon and frozen dataset')
            window.grab().save(str(out/'restart.png'));close();record('Restarted EXE exits normally')
            result['status']='PASS';return 0

        assert services.projects.current is None
        window.grab().save(str(out/'blank-start.png'))
        window.create_project(str(out),'Synthetic Lite verification','','')
        wait(lambda:services.projects.current and not window.project_busy and not window.p2.refreshing)
        project = services.projects.current; root = project.root; result['project_root']=root
        assert services.media.list()==[] and services.media.frames()==[] and services.cameras.list()==[]
        assert services.datasets.versions()==[] and services.annotations.labels()==[]
        record('Create a genuinely blank project; no cameras, media, frames, labels or datasets')
        page = window.pages['projects'];page.name.setText('Synthetic Lite saved');page.save_button.click()
        wait(lambda:not window.project_busy and services.projects.current.name=='Synthetic Lite saved')
        window.close_project();wait(lambda:services.projects.current is None and not window.project_busy)
        window.open_project(root);wait(lambda:services.projects.current and not window.project_busy)
        record('GUI save, close and reopen project')

        camera = services.cameras.save('Synthetic camera',root=root,mode='CREATE')
        camera = services.cameras.save('Synthetic camera edited',camera['id'],camera['revision'],root,mode='EDIT')
        assert services.cameras.list(root)[0]['id']==camera['id']
        record('Camera service create/edit preserves UUID')
        window.show_page('media'); m=window.p2.media
        sources=[out/'cfr-h264.mp4',out/'vfr-h264.mp4'];assert all(p.is_file() for p in sources)
        QFileDialog.getOpenFileNames=lambda *a,**k:([str(p) for p in sources],'')
        QMessageBox.question=lambda *a,**k:(QMessageBox.StandardButton.Discard if len(a)>1 and a[1]=='数据集草稿未保存' else QMessageBox.StandardButton.Yes)
        click(m,'import_media');wait(lambda:len(m.media_rows)==2 and not window.p2.tracked)
        assert all(row['state']=='READY' for row in m.media_rows)
        from ivad_app.video.reader import FileVideoSource
        for source in sources:
            frames=list(FileVideoSource(source).iter_frames());assert len(frames)==40
            expected=[i*40000+(12345 if i%2 and source.name.startswith('vfr') else 0) for i in range(40)]
            assert [f.pts_us for f in frames]==expected
        record('Actual linked LGPL FFmpeg reads CFR/VFR H264 with exact real PTS')
        import av
        playlist=out/'network-reference.m3u8'
        playlist.write_text('#EXTM3U\n#EXT-X-TARGETDURATION:1\n#EXT-X-MEDIA-SEQUENCE:0\n#EXTINF:1,\nhttp://127.0.0.1:9/synthetic.ts\n#EXT-X-ENDLIST\n',encoding='utf8')
        previous_log_level=av.logging.get_level()
        av.logging.set_level(av.logging.DEBUG)
        try:
            with av.logging.Capture(local=False) as protocol_logs:
                try:FileVideoSource(playlist)
                except AppError:pass
                else:raise AssertionError('Native FFmpeg accepted an online media reference')
        finally:av.logging.set_level(previous_log_level)
        assert 'whitelist' in str(protocol_logs).lower(), protocol_logs
        result['native_protocol_denial']=[list(row) for row in protocol_logs]
        record('Native FFmpeg rejects network references before opening a network protocol')
        for row in m.media_rows:services.cameras.associate(row['id'],camera['id'],None,root)
        m.table.selectRow(next(i for i,r in enumerate(m.media_rows) if r['name']=='vfr-h264.mp4'))
        wait(lambda:m.player.last_image is not None)
        click(m.player,'video_play');wait(lambda:m.player.position_us>100000);click(m.player,'video_play')
        assert not m.player.playing;record('Native video display, play and pause')
        m.tabs.setCurrentIndex(1);m.start.setValue(0);m.end.setValue(1.5);m.interval.setValue(.1);m.maximum.setValue(12)
        click(m,'extract_frames');wait(lambda:len(services.media.frames(root))>=8 and not window.p2.tracked)
        record('GUI extracts actual image files from VFR video')
        assert not m.tabs.isTabEnabled(3)
        window.show_page('annotation');a=window.p2.annotation;wait(lambda:a.frame_id and not a.loading)
        from ivad_app.gui.label_dialog import LabelDialog
        dialog=LabelDialog(services.annotations,window.runner,root,window.p2.refresh,window);dialog.show()
        dialog.name.setText('Synthetic anomaly');click(dialog,'save_label')
        wait(lambda:any(r['name']=='Synthetic anomaly' for r in dialog.records))
        label=next(r['id'] for r in dialog.records if r['name']=='Synthetic anomaly');dialog.accept()
        wait(lambda:a.classes.findData(label)>=0);a.classes.setCurrentIndex(a.classes.findData(label))
        a.tool.setCurrentIndex(1)
        mouse(a.canvas,QEvent.Type.MouseButtonPress,20,20);mouse(a.canvas,QEvent.Type.MouseMove,95,85);mouse(a.canvas,QEvent.Type.MouseButtonRelease,95,85)
        assert any(o['kind']=='box' for o in a.canvas.shapes)
        a.tool.setCurrentIndex(2)
        for x,y in [(140,25),(230,25),(200,120)]:
            mouse(a.canvas,QEvent.Type.MouseButtonPress,x,y);mouse(a.canvas,QEvent.Type.MouseButtonRelease,x,y)
        app.sendEvent(a.canvas,QKeyEvent(QEvent.Type.KeyPress,Qt.Key.Key_Return,Qt.KeyboardModifier.NoModifier))
        assert any(o['kind']=='polygon' for o in a.canvas.shapes)
        a.image_tag.setCurrentIndex(2);click(a,'save_annotation');wait(lambda:not a.saving and not a.dirty)
        fid=a.frame_id;result['annotation_frame_id']=fid
        assert {o['kind'] for o in services.annotations.load(fid,root)['payload']['objects']}=={'box','polygon'}
        window.grab().save(str(out/'annotation.png'));record('Native canvas mouse events draw box/polygon; save persisted annotation')
        other=next(i for i in range(a.frames.count()) if a.frames.item(i).data(Qt.ItemDataRole.UserRole)!=fid)
        a.frames.setCurrentRow(other);wait(lambda:not a.loading and a.frame_id!=fid)
        a.image_tag.setCurrentIndex(1);click(a,'save_annotation');wait(lambda:not a.saving and not a.dirty)
        assert services.annotations.load(a.frame_id,root)['payload']['image_tag']=='NORMAL'
        record('GUI manually marks a normal frame without boxes')
        # Populate remaining synthetic images as normal through the same service,
        # keeping the actual GUI-created abnormal annotation above unchanged.
        for frame in services.media.frames(root):
            if frame['id']!=fid:
                current=services.annotations.load(frame['id'],root)
                services.annotations.save(frame['id'],dict(image_tag='NORMAL',objects=[],image_label_id=None),None,current['revision'],root=root)
        record('Normal negative samples persist without target boxes')
        window.p2.refresh()
        window.show_page('dataset');d=window.p2.dataset
        expected_count=len(services.media.frames(root))
        wait(lambda:len(d.all_rows)==expected_count and sum(r['image_tag']=='NORMAL' for r in d.all_rows)==expected_count-1 and not window.p2.refreshing and not window.p2.refresh_pending)
        d.camera.setCurrentIndex(d.camera.findData('__all__'));d.select_all();d.allow_multi.setChecked(True);d.allow_limited.setChecked(True);d.add_selected()
        assert len(d.draft_frames())>=8
        d.name.setText('Synthetic Lite dataset');d.tabs.setCurrentIndex(1);click(d,'dataset_save_draft')
        wait(lambda:d.active_dataset and not d.draft_saving)
        d.tabs.setCurrentIndex(2);click(d,'dataset_split_preview');wait(lambda:d.active_validated)
        d.tabs.setCurrentIndex(3);click(d,'freeze_dataset');wait(lambda:len(d.version_rows)==1 and not window.p2.tracked)
        d.versions.selectRow(0);record('GUI saves draft, checks split and freezes a dataset version')
        QFileDialog.getExistingDirectory=lambda *args,**kwargs:str(out)
        assert d.format.currentData()=='ivad_native'
        exports=[]
        for fmt in ['ivad_native','coco']:
            d.format.setCurrentIndex(d.format.findData(fmt));click(d,'export_dataset')
            wait(lambda:bool(list(out.glob(f'IVAD-*-{fmt}-*'))) and not window.p2.tracked)
            target=next(out.glob(f'IVAD-*-{fmt}-*'));doc=json.loads((target/'ivad_native.json').read_text(encoding='utf8'))
            assert doc['export_format']==fmt and len(doc['samples'])>=8
            manifest=json.loads((target/'export_manifest.json').read_text(encoding='utf8'))
            assert manifest['state']=='COMPLETE' and all(hashlib.sha256((target/p).read_bytes()).hexdigest()==h for p,h in manifest['files'].items())
            if fmt=='coco':assert list(target.glob('instances_*.json'))
            exports.append(str(target))
        result['exports']=exports;window.grab().save(str(out/'dataset.png'));record('Default Native and explicit COCO exports have valid image/file hashes')
        denied=[]
        for name,call in [('queue train',lambda:services.jobs.submit('p3_train',None,{})),
                          ('queue offline',lambda:services.jobs.submit('p35_offline',None,{})),
                          ('queue clip',lambda:services.jobs.submit('p2_clip',None,{})),
                          ('handler injection',lambda:services.jobs.register('p3_train',lambda *_:None)),
                          ('direct clip',lambda:services.media.save_video_clip(None,{})),
                          ('direct train',lambda:services.training.train(None,{})),
                          ('legacy cache',lambda:services.offline.load('ignored'))]:
            try:call()
            except AppError as exc:assert exc.code=='DEMO_FEATURE_DISABLED';denied.append(name)
            else:raise AssertionError('Disabled operation was accepted: '+name)
        result['backend_denials']=denied
        assert not any(n.split('.')[0] in {'torch','ultralytics','onnxruntime','rfdetr','cv2'} for n in sys.modules)
        from ivad_app.core.demo_policy import RUNTIME_AUDIT
        assert RUNTIME_AUDIT['denied_network']==[]
        for package in ['torch','ultralytics','rfdetr','onnxruntime']:
            try:__import__(package)
            except ImportError:pass
            else:raise AssertionError('Forbidden dynamic import succeeded: '+package)
        result['runtime_audit']=RUNTIME_AUDIT
        record('Backend bypass attempts denied; no AI package loaded or CUDA required')
        result['loaded_modules']=sorted(sys.modules);result['loaded_dlls']=loaded_dlls()
        close();record('Normal EXE window shutdown; workers and databases closed')
        result['status']='PASS';return 0
    except Exception:
        result['status']='FAIL';result['error']=traceback.format_exc()
        if window:
            result['last_notice']=window.notice.text()
            result['dataset_counts']=window.p2.dataset.counts.text()
            result['dataset_action']=window.p2.dataset.action_info.text()
        return 1
    finally:
        if window and not window.may_close:
            try:close()
            except Exception:result['shutdown_error']=traceback.format_exc()
        result_file.write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
