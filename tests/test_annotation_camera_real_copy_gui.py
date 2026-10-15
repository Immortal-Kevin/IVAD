import json,sqlite3,shutil,subprocess
from pathlib import Path
from tests.test_gui import make_window,close_window
from ivad_app.storage.project_store import safe_path


def test_real_project_readonly_display_via_isolated_copy(qtbot,services,tmp_path):
    output=Path('artifacts/annotation-camera-hotfix-20261015');metadata=output/'real-readonly-before.json'
    if not metadata.exists():
        import pytest;pytest.skip('本机真实项目只读证据缺失')
    data=json.loads(metadata.read_text(encoding='utf-8'));original=Path(data['database']).parent;copy=tmp_path/'real-project-display-copy';copy.mkdir()
    shutil.copyfile(original/'project.json',copy/'project.json');shutil.copyfile(output/'real-project-readonly-backup.sqlite',copy/'project.sqlite')
    with sqlite3.connect(copy/'project.sqlite') as c:
        selected=[];seen=set()
        for fid,mid,path in c.execute('select id,media_id,path from frames order by created_at'):
            if mid in seen:continue
            seen.add(mid);selected.append(fid);source=safe_path(original,path);destination=safe_path(copy,path);destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,destination)
        annotated=[r[0] for r in c.execute("select frame_id from annotations where json_array_length(json_extract(payload,'$.objects'))>0 or status in ('REVIEWED','APPROVED')")]
    project=services.projects.open(str(copy));w=make_window(qtbot,services);w.show_page('annotation');a=w.p2.annotation
    try:
        qtbot.waitUntil(lambda:bool(a.frame_id) and not a.loading and a.camera_filter.count()>=len(data['cameras'])+2,timeout=10000)
        assert {a.camera_filter.itemData(i) for i in range(2,a.camera_filter.count())}=={r['id'] for r in data['cameras']}
        assert not a.roi_scope.isVisible()
        old_source=subprocess.run(['git','show','c79d50d:ivad_app/services/annotation_service.py'],capture_output=True,check=True).stdout.decode('utf-8');ns={};exec(compile(old_source,'historical_annotation_service.py','exec'),ns)
        old=ns['AnnotationService'](services.store,services.media,services.logs)
        preview=old.batch_preview(annotated,'exclude',project.root)
        (output/'real-copy-old-exclusion-preview.json').write_text(json.dumps(preview,ensure_ascii=False,indent=2),encoding='utf-8')
        assert preview['selected'] and not preview['eligible']
        w.resize(1920,1080);qtbot.wait(80);assert w.grab().save(str(output/'real-copy-source-display.png'))
        # Inspect current-source camera lookup without writing annotations.
        report={'source_project_uuid':project.id,'copy_root':str(copy),'copied_frame_ids':selected,'cameras':[{k:r[k] for k in ['id','name']} for r in services.cameras.list()], 'old_rejected_selected':preview['selected'],'old_skipped':len(preview['skipped']),'frame_loaded':a.frame_id,'source_camera_id':a.camera_id,'roi_scope_hidden':not a.roi_scope.isVisible()}
        (output/'real-copy-gui-validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    finally:close_window(qtbot,w)
