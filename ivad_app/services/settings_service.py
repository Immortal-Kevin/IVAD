from ivad_app.core.contracts import AppError
from ivad_app.storage.models import SettingRecord

class SettingsService:
    def __init__(self, db): self.db = db

    def get(self, key: str, default=None):
        with self.db.transaction() as session:
            row = session.get(SettingRecord, key)
            return row.value if row else default

    def set(self, key: str, value: dict):
        if not isinstance(value, dict):
            raise AppError('SETTINGS_INVALID', '设置格式错误，应为对象。')
        with self.db.transaction() as session:
            row = session.get(SettingRecord, key)
            if row: row.value = value
            else: session.add(SettingRecord(key=key, value=value))

    def recent_projects(self) -> list[dict]:
        value = self.get('recent_projects', {'items': []})
        if not isinstance(value, dict) or not isinstance(value.get('items'), list):
            raise AppError('SETTINGS_INVALID', '最近项目记录格式错误，请查看诊断日志。')
        return value['items']

    def remember(self, project):
        old = self.recent_projects()
        item = {'id': project.id, 'name': project.name, 'root': project.root}
        self.set('recent_projects', {'items': [item] + [p for p in old if p['id'] != project.id][:19]})

    def preferences(self) -> dict:
        value = self.get('preferences', {'language': 'zh_CN', 'worker_python': '', 'preferred_gpu': ''})
        self.validate_preferences(value)
        return value

    @staticmethod
    def validate_preferences(value):
        if not isinstance(value, dict) or any(not isinstance(value.get(k), str) for k in ['language', 'worker_python', 'preferred_gpu']):
            raise AppError('SETTINGS_INVALID', '应用设置格式错误，请查看诊断日志；不会重建数据库。')

    def save_preferences(self, value: dict):
        self.validate_preferences(value)
        if value.get('language') != 'zh_CN':
            raise AppError('LANGUAGE_UNSUPPORTED', '当前仅提供简体中文，英文语言包尚未实现。')
        self.set('preferences', value)
