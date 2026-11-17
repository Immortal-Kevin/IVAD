import json, shutil, sqlite3
from pathlib import Path
import pytest
from sqlalchemy import text
from ivad_app.core.contracts import AppError
from ivad_app.storage.database import Database
from ivad_app.storage.database import SCHEMA_HEAD

def test_chinese_project_save_reopen_move(services, tmp_path):
    project = services.projects.create(str(tmp_path), '中文选煤厂', '设备说明', '北厂区')
    assert services.projects.check()['integrity'] == 'ok'
    assert project.name == '中文选煤厂'
    saved = services.projects.save('中文项目修改', '新描述', '南厂区', project.revision)
    assert saved.id == project.id and saved.revision == 2
    services.projects.close()
    reopened = services.projects.open(project.root)
    assert reopened.name == '中文项目修改' and reopened.description == '新描述'
    assert services.settings.recent_projects()[0]['id'] == project.id
    services.projects.close()
    moved = tmp_path / '移动后的中文目录'
    shutil.copytree(project.root, moved)
    copied = services.projects.open(str(moved))
    assert copied.id == project.id and copied.schema == SCHEMA_HEAD
    assert json.loads((moved / 'project.json').read_text())['database'] == 'project.sqlite'

@pytest.mark.parametrize('name', ['', ' ', 'x' * 121])
def test_invalid_names_do_not_create_project(services, tmp_path, name):
    before = set(tmp_path.iterdir())
    with pytest.raises(AppError): services.projects.create(str(tmp_path), name)
    assert set(tmp_path.iterdir()) == before

def test_missing_parent_and_non_directory(services, tmp_path):
    for path in [tmp_path / 'absent', tmp_path / 'plainfile']:
        if path.name == 'plainfile': path.write_text('keep')
        with pytest.raises(AppError): services.projects.create(str(path), '项目')
    assert (tmp_path / 'plainfile').read_text() == 'keep'

def test_create_permission_failure_no_valid_partial(services, tmp_path, monkeypatch):
    original = Path.mkdir
    def deny(path, *args, **kwargs):
        if path.name.startswith('.ivad-staging-'): raise PermissionError('controlled permission denial')
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, 'mkdir', deny)
    with pytest.raises(AppError, match='创建失败'): services.projects.create(str(tmp_path), '权限测试')
    assert not list(tmp_path.glob('IVAD-*'))

def test_create_database_failure_cleans_only_owned_staging(services, tmp_path, monkeypatch):
    protected = tmp_path / 'user-data'; protected.mkdir(); (protected / 'keep.txt').write_text('keep')
    def fail(*args, **kwargs): raise RuntimeError('controlled init failure')
    monkeypatch.setattr('ivad_app.services.project_service.Database', fail)
    with pytest.raises(AppError): services.projects.create(str(tmp_path), '失败测试')
    assert (protected / 'keep.txt').read_text() == 'keep'
    assert not list(tmp_path.glob('IVAD-*')) and not list(tmp_path.glob('.ivad-staging-*'))

def test_revision_conflict(services, tmp_path):
    project = services.projects.create(str(tmp_path), '项目')
    services.projects.save('修改', '', '', project.revision)
    with pytest.raises(AppError, match='其他操作'): services.projects.save('错误覆盖', '', '', project.revision)
    assert services.projects.current.name == '修改'

@pytest.mark.parametrize('mutation', ['bad_json', 'uuid', 'traversal', 'missing_db'])
def test_bad_project_rejected_keeps_current_and_files(services, tmp_path, mutation):
    current = services.projects.create(str(tmp_path), '当前项目')
    other = tmp_path / 'invalid'; shutil.copytree(current.root, other)
    manifest = json.loads((other / 'project.json').read_text())
    if mutation == 'bad_json': (other / 'project.json').write_text('{broken')
    elif mutation == 'uuid':
        manifest['id'] = '11111111-1111-4111-8111-111111111111'; (other / 'project.json').write_text(json.dumps(manifest))
    elif mutation == 'traversal':
        manifest['database'] = '../project.sqlite'; (other / 'project.json').write_text(json.dumps(manifest))
    else: (other / 'project.sqlite').unlink()
    before = {p.name: p.read_bytes() for p in other.iterdir() if p.is_file()}
    with pytest.raises(AppError): services.projects.open(str(other))
    assert services.projects.current.id == current.id
    assert before == {p.name: p.read_bytes() for p in other.iterdir() if p.is_file()}

def test_corrupt_database_unchanged(tmp_path):
    path = tmp_path / 'corrupt.sqlite'; payload = b'not a sqlite database'; path.write_bytes(payload)
    with pytest.raises(AppError): Database(path)
    assert path.read_bytes() == payload

def test_migration_0001_to_0002_preserves_data_and_backup(tmp_path):
    path = tmp_path / 'old.sqlite'
    db = Database(path, create=True, revision='0001')
    with db.engine.begin() as connection:
        connection.execute(text("INSERT INTO projects (id,name,description,site,created_at,updated_at) VALUES ('keep-id','中文旧项目','','','now','now')"))
    db.close()
    migrated = Database(path)
    assert migrated.integrity_check() == 'ok'
    with migrated.engine.connect() as connection:
        row = connection.execute(text('SELECT name,revision FROM projects')).one()
        assert row == ('中文旧项目', 1)
    migrated.close()
    assert len(list(tmp_path.glob('*.backup'))) == 1
    reopened = Database(path); assert reopened.integrity_check() == 'ok'; reopened.close()

def test_unknown_schema_no_modification(tmp_path):
    path = tmp_path / 'future.sqlite'; db = Database(path, create=True); db.close()
    with sqlite3.connect(path) as raw: raw.execute("UPDATE alembic_version SET version_num='9999'")
    before = path.read_bytes()
    with pytest.raises(AppError, match='版本不受支持'): Database(path)
    assert path.read_bytes() == before

def test_settings_persistent_and_format_error(services, tmp_path):
    from ivad_app.services.settings_service import SettingsService
    services.settings.save_preferences({'language': 'zh_CN', 'worker_python': 'chosen', 'preferred_gpu': ''})
    assert SettingsService(services.db).preferences()['worker_python'] == 'chosen'
    with pytest.raises(AppError): services.settings.save_preferences({'language': 'en'})
    services.settings.set('recent_projects', {'items': 'invalid'})
    with pytest.raises(AppError, match='格式错误'): services.settings.recent_projects()

def test_preferences_corruption_is_explicit(services):
    services.settings.set('preferences', {'language': 'zh_CN', 'worker_python': 42, 'preferred_gpu': ''})
    with pytest.raises(AppError, match='格式错误'): services.settings.preferences()

def test_catalog_failure_does_not_close_current_project(services, tmp_path, monkeypatch):
    current = services.projects.create(str(tmp_path), '已有项目')
    other = services.projects.create(str(tmp_path), '另一项目')
    services.projects.open(current.root)
    def fail(_): raise AppError('CATALOG', '可控目录数据库错误')
    monkeypatch.setattr(services.settings, 'remember', fail)
    with pytest.raises(AppError): services.projects.open(other.root)
    assert services.projects.current.id == current.id
