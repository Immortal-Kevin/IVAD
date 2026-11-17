import copy,json,sqlite3,shutil
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import pytest
from sqlalchemy import text,event
from sqlalchemy.exc import IntegrityError,OperationalError
from ivad_app.core.contracts import AppError
from ivad_app.storage.database import Database
from ivad_app.services.camera_service import CameraService


def test_create_edit_unique_isolation_and_sql_constraint(services,tmp_path):
    a=services.projects.create(str(tmp_path),'A');s=services.cameras
    first=s.save('8525压滤机',details={'code':'8525'},mode='CREATE')
    second=s.save('1202-1204给煤机',details={'code':'12021204'},mode='CREATE')
    assert first['id']!=second['id'] and len(s.list())==2
    changed=s.save('8525压滤机新名称',first['id'],first['revision'],details=first['details'],mode='EDIT')
    assert changed['id']==first['id'] and next(r for r in s.list() if r['id']==second['id'])==second
    before=s.list()
    with pytest.raises(AppError):s.save('重复编号',details={'code':' 8525 '})
    assert s.list()==before
    with pytest.raises(AppError):s.save('错误模式',first['id'],changed['revision'],mode='CREATE')
    with s.store.open() as (_,db,_):
        with pytest.raises(IntegrityError),db.transaction() as session:
            session.execute(text("INSERT INTO cameras(id,name,revision,history,details) VALUES('duplicate','bad',1,'[]',:details)"),{'details':json.dumps({'code':'8525'})})
    assert s.list()==before
    b=services.projects.create(str(tmp_path),'B');s.save('另项目8525',details={'code':'8525'})
    assert len(s.list(b.root))==1 and len(s.list(a.root))==2
    services.projects.open(a.root);assert s.list()==before

@pytest.mark.parametrize('failure',['insert','assertion','other_record','unwritable'])
def test_failure_rolls_back_without_success(services,tmp_path,monkeypatch,failure):
    services.projects.create(str(tmp_path),'故障注入');s=services.cameras
    first=s.save('8525压滤机',details={'code':'8525'});before=s.list();original=s._verify
    if failure=='assertion':
        def reject(*args):raise AppError('INJECTED','测试完整性断言失败')
        monkeypatch.setattr(s,'_verify',reject)
    elif failure=='other_record':
        original_snapshot=s._snapshot;calls=[0]
        def corrupt(session):
            calls[0]+=1
            if calls[0]==2:session.execute(text("UPDATE cameras SET name='CORRUPTED' WHERE id=:id"),{'id':first['id']});session.expire_all()
            return original_snapshot(session)
        monkeypatch.setattr(s,'_snapshot',corrupt)
    else:
        from sqlalchemy.engine import Engine
        def reject(conn,cursor,statement,parameters,context,many):
            if statement.lstrip().upper().startswith('INSERT INTO CAMERAS'):
                raise OperationalError(statement,parameters,sqlite3.OperationalError('readonly database' if failure=='unwritable' else 'injected INSERT failure'))
        event.listen(Engine,'before_cursor_execute',reject)
    try:
        with pytest.raises((AppError,OperationalError)):s.save('第二摄像头',details={'code':'12021204'})
    finally:
        if failure in {'insert','unwritable'}:event.remove(Engine,'before_cursor_execute',reject)
    assert s.list()==before


def test_concurrent_duplicate_create(services,tmp_path):
    p=services.projects.create(str(tmp_path),'并发测试')
    def create(i):
        try:return services.cameras.save(str(i),root=p.root,details={'code':'8525'})
        except (AppError,IntegrityError):return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(create,range(2)))
    assert sum(r is not None for r in results)==1 and len(services.cameras.list())==1


def test_migration_copy_and_conflict_preflight(tmp_path):
    from ivad_app.storage.models import Camera
    db=Database(tmp_path/'old.sqlite',create=True,revision='0007')
    with db.transaction() as session:
        session.add_all([Camera(id='a',name='A',details={'code':'8525'}),Camera(id='b',name='B',details={'code':'8525'})])
    db.close()
    with pytest.raises(AppError):Database(tmp_path/'old.sqlite')
    with sqlite3.connect(tmp_path/'old.sqlite') as c:
        assert c.execute('select version_num from alembic_version').fetchone()[0]=='0007'
        assert c.execute('select count(*) from cameras').fetchone()[0]==2
    assert list(tmp_path.glob('*.backup'))


def test_real_project_backup_migrates_only_copy(tmp_path):
    source=Path('artifacts/camera-integrity-v2-20261015/real-project-consistent.sqlite')
    if not source.exists():pytest.skip('本机真实只读快照不在此环境')
    destination=tmp_path/'copy.sqlite';shutil.copyfile(source,destination)
    with sqlite3.connect(source) as c:before=c.execute('select * from cameras').fetchall()
    db=Database(destination);assert db.integrity_check()=='ok';db.close()
    with sqlite3.connect(destination) as c:assert c.execute('select * from cameras').fetchall()==before


def test_edit_integrity_failure_rolls_back_other_camera(services,tmp_path,monkeypatch):
    services.projects.create(str(tmp_path),'编辑保护');s=services.cameras
    a=s.save('A',details={'code':'A'});b=s.save('B',details={'code':'B'});before=s.list()
    original=s._snapshot;calls=[0]
    def corrupt(session):
        calls[0]+=1
        if calls[0]==2:
            session.execute(text("UPDATE cameras SET name='BAD' WHERE id=:id"),{'id':b['id']});session.expire_all()
        return original(session)
    monkeypatch.setattr(s,'_snapshot',corrupt)
    with pytest.raises(AppError):s.save('A修改',a['id'],a['revision'],mode='EDIT')
    assert s.list()==before


def test_postcommit_log_failure_reports_committed_state(services,tmp_path,monkeypatch):
    services.projects.create(str(tmp_path),'提交后诊断失败');s=services.cameras
    def fail(*a,**k):raise OSError('injected log unavailable')
    monkeypatch.setattr(s.logs,'write',fail)
    row=s.save('已提交',details={'code':'A'})
    assert '已提交' in row['diagnostic_warning']
    assert s.list()[0]['id']==row['id']
