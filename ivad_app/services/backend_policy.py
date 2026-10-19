"""Read-only classification; never rewrite historical backend facts."""
from ivad_app.core.contracts import AppError

MIGRATION_PENDING = 'TEMPORARILY UNAVAILABLE — RF-DETR MIGRATION PENDING'

def classification(details):
    backend, model = details.get('backend'), details.get('model')
    if backend == 'rfdetr' and model == 'rfdetr-nano':
        return 'ACTIVE_RFDETR'
    if backend in {None, 'ultralytics', 'yolo'} and model in {'yolo11n', 'yolo26n'}:
        return 'LEGACY_READ_ONLY'
    return 'UNKNOWN'

def require_active(details):
    if classification(details) != 'ACTIVE_RFDETR':
        raise AppError('LEGACY_READ_ONLY', '历史或未知后端仅供只读审计；禁止新训练、验证、候选或发布。')

def require_rf_request(payload):
    if payload.get('model') != 'rfdetr-nano' or payload.get('backend', 'rfdetr') != 'rfdetr':
        raise AppError('LEGACY_READ_ONLY', '新训练仅支持 RF-DETR Nano；旧后端已归档。')
