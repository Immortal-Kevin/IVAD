import os,json
from pathlib import Path
import pytest
from PySide6.QtCore import QEvent,QPoint
from PySide6.QtGui import QHelpEvent
from PySide6.QtWidgets import QApplication,QToolTip
from tests.test_gui import make_window,close_window
from tests.test_p2_media import sample_videos

def test_real_p3_gui_acceptance(qtbot,services):
    location=os.environ.get('IVAD_P35_COPY')
    if not location:pytest.skip('Explicit independent real-project copy required')
    services.projects.open(location);services.devices.probe()
    w=make_window(qtbot,services);w.update_project_summary();w.show_page('training');t=w.pages['training'];out=Path(os.environ['IVAD_P35_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        qtbot.waitUntil(lambda:not t.busy and bool(t.rows) and bool(t.gpu.count()),timeout=15000);t.timer.stop();w.resize(1920,1080)
        assert any(r['id'].startswith('7a01bcad') for r in t.rows)
        assert any(r['dataset_id']==t.dataset_group.currentData() and r['id']==t.dataset.currentData() for r in t.frozen_versions)
        t.mode.setCurrentIndex(0);assert not t.inputs['epochs'].isEnabled()
        for widget in list(t.inputs.values())+t.action_buttons+[t.initial,t.resume]:
            assert widget.toolTip();QApplication.sendEvent(widget,QHelpEvent(QEvent.Type.ToolTip,QPoint(3,3),widget.mapToGlobal(QPoint(3,3))));qtbot.waitUntil(QToolTip.isVisible,timeout=2000);QToolTip.hideText()
        t.mode.setCurrentIndex(1);assert t.inputs['epochs'].isEnabled();old=t.inputs['epochs'].value();t.inputs['epochs'].setValue(old+1);assert t.configuration()['parameters']['epochs']==old+1;t.inputs['epochs'].setValue(old)
        assert t.inputs['amp'].isEnabled();t.inputs['amp'].setChecked(True);assert t.configuration()['parameters']['amp'];t.inputs['amp'].setChecked(False)
        i=next(i for i,r in enumerate(t.rows) if r['id'].startswith('7a01bcad'));t.runs.selectRow(i);qtbot.wait(60)
        record=json.loads(t.metrics.toPlainText());assert record['metrics']['map50']>0 and record['actual_parameters']
        assert (Path(location)/t.rows[i]['path']/'worker-console.log').is_file()
        assert len({b.y() for b in t.action_buttons})==1
        t.model.setCurrentText('yolo11n');t.preflight();qtbot.waitUntil(lambda:not t.checking,timeout=30000);assert t.checked_configuration,t.info.text()
        assert w.grab().save(str(out/'p3-training-actual.png'))
        w.show_page('logs');qtbot.wait(100);assert w.grab().save(str(out/'diagnostic-logs.png'))
        (out/'p3-gui-results.json').write_text(json.dumps(dict(status='PASS',gpu=t.gpu.currentText(),history_runs=len(t.rows),dataset=t.dataset.currentText(),actual_metrics=record,tooltips=len(t.inputs)+len(t.action_buttons)+2),ensure_ascii=False,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)

def test_real_fault_range_import_empty_and_cancel(qtbot,services,tmp_path,monkeypatch,sample_videos):
    location=os.environ.get('IVAD_P35_COPY')
    if not location:pytest.skip('Explicit independent project copy required')
    from PySide6.QtWidgets import QFileDialog
    services.projects.open(location);services.devices.probe();w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');p=w.pages['offline'];out=Path(os.environ['IVAD_P35_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    def ready():qtbot.waitUntil(lambda:not p.busy and p.start_button.isEnabled() and bool(p.gpu.count()),timeout=15000)
    def finish(old=None):qtbot.waitUntil(lambda:p.run_path!=old and p.run_path is not None or 'FAILED' in p.info.text(),timeout=120000);assert p.run_path!=old,p.info.text();qtbot.waitUntil(lambda:p.player.last_image is not None,timeout=15000)
    try:
        ready();p.model.setCurrentIndex(p.model.findData(next(r['id'] for r in p.model_rows if r['id'].startswith('4a1c7df7'))));p.media.setCurrentIndex(p.media.findData('12a11464-0581-4bf1-8977-47fbcd5364b7'));p.start_time.setValue(7);p.end_time.setValue(9);p.start_button.click();finish()
        m=p.manifest;assert m['frames'][0]['time_us']>=7000000 and m['frames'][-1]['time_us']<9000000
        detections=sum(len(r['boxes']) for r in m['frames']);assert detections>0,'No actual positive predictions; do not fabricate boxes'
        for r in m['frames']:services.offline.validate_boxes(r['boxes'],r['width'],r['height'],len(m['classes']))
        positive=next(i for i,r in enumerate(m['frames']) if r['boxes']);p.results.selectRow(positive);qtbot.waitUntil(lambda:abs(p.player.position_us-m['frames'][positive]['cache_time_us'])<1000,timeout=15000);w.resize(1920,1080);qtbot.wait(100);w.grab().save(str(out/'offline-real-predicted-boxes.png'))
        assert p.grab().toImage().pixelColor(3,3).lightness()>200
        report=dict(fault_range=dict(path=p.run_path,frames=len(m['frames']),detections=detections,seconds=m['seconds'],fps=m['end_to_end_fps'],inference_fps=m['inference_fps'],gpu_peak_bytes=m['gpu_peak_bytes'],source_notice=m['source_notice']))
        ready();monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(sample_videos/'sample.mp4'),''));p.import_button.click();qtbot.waitUntil(lambda:p.job is not None,timeout=10000);qtbot.waitUntil(lambda:p.job is None and not p.busy and any(r['name']=='sample.mp4' for r in p.media_rows),timeout=20000);ready()
        p.media.setCurrentIndex(p.media.findData(next(r['id'] for r in p.media_rows if r['name']=='sample.mp4')));p.confidence.setValue(1);p.end_time.setValue(.5);old=p.run_path;p.start_button.click();finish(old);assert all(not r['boxes'] for r in p.manifest['frames']);report['empty_real_inference_frames']=len(p.manifest['frames'])
        ready();p.media.setCurrentIndex(p.media.findData('12a11464-0581-4bf1-8977-47fbcd5364b7'));p.confidence.setValue(.25);p.start_time.setValue(0);p.end_time.setValue(70);p.start_button.click();qtbot.waitUntil(lambda:p.job is not None,timeout=10000);jid=p.job;qtbot.waitUntil(lambda:services.jobs.get(jid)['progress']>0 and p.cancel_button.isEnabled(),timeout=30000);p.cancel_button.click();qtbot.waitUntil(lambda:p.job is None,timeout=20000);assert services.jobs.get(jid)['state']=='CANCELLED';report['cancel_state']='CANCELLED'
        ready();bad=tmp_path/'invalid-demo.mp4';bad.write_bytes(b'invalid video TEST FIXTURE');monkeypatch.setattr(QFileDialog,'getOpenFileName',lambda *a,**k:(str(bad),''));p.import_button.click();qtbot.waitUntil(lambda:p.job is not None,timeout=10000);qtbot.waitUntil(lambda:p.job is None and not p.busy,timeout=20000);assert 'failed' in p.info.text().lower();report['invalid_import']='failed report, GUI remains responsive'
        (out/'additional-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)

def test_real_offline_demo_gui(qtbot,services,tmp_path,monkeypatch):
    location=os.environ.get('IVAD_P35_COPY')
    if not location:pytest.skip('Independent copy and actual GPU explicitly required')
    from PySide6.QtWidgets import QFileDialog
    services.projects.open(location);services.devices.probe();w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');page=w.pages['offline'];out=Path(os.environ['IVAD_P35_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        qtbot.waitUntil(lambda:not page.busy and page.model.count()>0 and page.media.count()>0 and page.start_button.isEnabled(),timeout=15000);w.resize(1920,1080)
        page.model.setCurrentIndex(page.model.findData(next(r['id'] for r in page.model_rows if r['id'].startswith('4a1c7df7'))));page.media.setCurrentIndex(page.media.findData('12a11464-0581-4bf1-8977-47fbcd5364b7'))
        page.start_time.setValue(0);page.end_time.setValue(2)
        qtbot.mouseClick(page.start_button,__import__('PySide6.QtCore',fromlist=['Qt']).Qt.MouseButton.LeftButton)
        qtbot.waitUntil(lambda:bool(page.run_path) or ('FAILED' in page.info.text()),timeout=120000);assert page.run_path,page.info.text()
        qtbot.waitUntil(lambda:page.player.last_image is not None,timeout=15000);m=page.manifest
        assert m['state']=='SUCCEEDED' and m['frames'] and all(r['cpu_fallback'] is False for r in m['frames'])
        assert m['source_notice'].startswith('训练来源') and m['frames'][0]['time_us']>=0 and m['frames'][-1]['time_us']<2000000
        times=[r['time_us'] for r in m['frames']];assert times==sorted(set(times))
        qtbot.waitUntil(lambda:page.results.rowCount()==len(times),timeout=10000);page.results.selectRow(len(times)//2);target=page.result_rows[len(times)//2][0]['cache_time_us'];qtbot.waitUntil(lambda:abs(page.player.position_us-target)<1000,timeout=15000)
        page.player.toggle();qtbot.wait(200);page.player.toggle();assert not page.player.playing
        page.player.goto.setValue(.4);page.player.goto_button.click();qtbot.waitUntil(lambda:page.player.position_us>=400000,timeout=15000)
        page.player.next.click();qtbot.wait(100);page.player.previous.click();qtbot.wait(100)
        assert w.grab().save(str(out/'offline-real-playback.png'))
        monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(out));page.export();qtbot.waitUntil(lambda:bool(list(out.glob('IVAD-offline-demo-*'))),timeout=15000);page.screenshot();qtbot.waitUntil(lambda:bool(list(out.glob('IVAD-demo-frame-*.png'))),timeout=15000)
        export=next(out.glob('IVAD-offline-demo-*'));assert (export/'manifest.json').is_file() and (export/'detections.csv').is_file() and (export/'annotated.mp4').is_file()
        (out/'demo-test-results.json').write_text(json.dumps(dict(status='PASS',run_path=page.run_path,frames=len(times),detections=sum(len(r['boxes']) for r in m['frames']),seconds=m['seconds'],fps=m['end_to_end_fps'],inference_fps=m['inference_fps'],gpu_peak_bytes=m['gpu_peak_bytes'],source_notice=m['source_notice'],first_pts=m['frames'][0]['raw_pts_us'],last_pts=m['frames'][-1]['raw_pts_us'],export=str(export)),ensure_ascii=False,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)

def test_history_export_and_layout(qtbot,services,monkeypatch):
    location=os.environ.get('IVAD_P35_COPY')
    if not location:pytest.skip('Explicit real copy with completed prediction cache required')
    from PySide6.QtWidgets import QFileDialog
    from PySide6.QtCore import Qt
    services.projects.open(location);w=make_window(qtbot,services);w.update_project_summary();w.show_page('offline');p=w.pages['offline'];out=Path(os.environ['IVAD_P35_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
    try:
        qtbot.waitUntil(lambda:not p.busy and p.history.count()>1,timeout=15000)
        cached=next(f.parent for f in (Path(location)/'demos').glob('*/manifest.json') if (m:=json.loads(f.read_text(encoding='utf8')))['state']=='SUCCEEDED' and m['parameters']['start']==7)
        p.history.setCurrentIndex(p.history.findData(str(cached)));qtbot.waitUntil(lambda:p.run_path is not None and p.player.last_image is not None,timeout=15000)
        p.results.selectRow(next(i for i,r in enumerate(p.manifest['frames']) if r['boxes']));target=p.result_rows[p.results.currentRow()][0]['cache_time_us'];qtbot.waitUntil(lambda:abs(p.player.position_us-target)<1000,timeout=10000)
        monkeypatch.setattr(QFileDialog,'getExistingDirectory',lambda *a,**k:str(out));p.export();p.screenshot();qtbot.waitUntil(lambda:bool(list(out.glob('IVAD-demo-frame-*.png'))) and bool(list(out.glob('IVAD-offline-demo-*'))),timeout=15000)
        exported=next(out.glob('IVAD-offline-demo-*'));data=services.offline.load(exported);assert data['frames']==p.manifest['frames'] and sum(len(r['boxes']) for r in data['frames'])>0
        import csv
        with (exported/'detections.csv').open(encoding='utf-8-sig') as f:records=list(csv.DictReader(f))
        assert any(r['class'] and float(r['confidence'])>0 for r in records)
        sizes=[]
        for width,height in [(1920,1080),(1040,720)]:
            w.resize(width,height);qtbot.wait(80);assert p.grab().toImage().pixelColor(3,3).lightness()>200
            w.grab().save(str(out/f'offline-history-{width}.png'));sizes.append(dict(requested=[width,height],actual=[w.width(),w.height()],dpr=w.devicePixelRatioF()))
        p.player.slider.setValue(1000);p.player.slider.sliderReleased.emit();qtbot.waitUntil(lambda:p.player.position_us>=1000000,timeout=10000)
        (out/'layout.json').write_text(json.dumps(sizes,indent=2),encoding='utf8')
    finally:close_window(qtbot,w)
