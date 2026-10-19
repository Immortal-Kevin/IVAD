"""RF-only training facade with explicit read-only historical classification."""
from sqlalchemy import select
from ivad_app.storage.models import TrainingRun
from ivad_app.services.rfdetr_training_service import RFDETRTrainingService
from ivad_app.services.backend_policy import classification,require_rf_request

class TrainingService:
    def __init__(self,*args):
        self.args=args;self.rf=RFDETRTrainingService(*args);self._old=None
    def legacy(self):
        from ivad_app.core.contracts import AppError
        raise AppError('LEGACY_READ_ONLY','旧训练后端已归档，不能启动。')
    def runs(self,root=None,*,include_archived=False):
        with self.rf.store.open(root) as (_,db,_),db.transaction() as s:
            rows=[dict(r.details,id=r.id,archive_classification=classification(r.details)) for r in s.scalars(select(TrainingRun))]
        if hasattr(self,'jobs'):
            from pathlib import Path
            with self.rf.store.open(root) as (folder,_,_):project_root=str(folder.resolve())
            known={r.get('job_id') for r in rows}
            with self.jobs.db.transaction() as s:
                from ivad_app.storage.models import JobRecord
                for job in s.scalars(select(JobRecord).where(JobRecord.kind.in_(['p3_train','p3_validate']))):
                    p=job.payload
                    if job.id in known or classification(p)!='ACTIVE_RFDETR' or not p.get('root') or str(Path(p['root']).resolve())!=project_root:continue
                    rows.append(dict(p,id=job.id,job_id=job.id,backend='rfdetr',archive_classification='ACTIVE_RFDETR',state=job.state,path='',error=job.error,created_at=job.created_at,record_source='JobRecord'))
        return rows if include_archived else [r for r in rows if r['archive_classification']=='ACTIVE_RFDETR']
    def configuration_preflight(self,payload):
        require_rf_request(payload)
        return self.rf.configuration_preflight(payload)
    def train(self,context,payload):
        require_rf_request(payload)
        return self.rf.train(context,payload)
    def validate(self,context,payload):return self.train(context,dict(payload,operation='validate',resume_run_id=None))
    def preflight(self,version_id,root=None):return self.rf.snapshot(version_id,root)
    def rf_devices(self):return self.rf.devices_snapshot()
