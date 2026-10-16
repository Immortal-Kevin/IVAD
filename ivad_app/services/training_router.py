"""Neutral training facade. Legacy implementation is imported only on an explicit legacy job."""
from sqlalchemy import select
from ivad_app.storage.models import TrainingRun
from ivad_app.services.rfdetr_training_service import RFDETRTrainingService
from ivad_app.compute.rfdetr_contract import MODEL

class TrainingService:
    def __init__(self,*args):
        self.args=args;self.rf=RFDETRTrainingService(*args);self._old=None
    def legacy(self):
        if self._old is None:
            from ivad_app.services.training_service import TrainingService as Legacy
            self._old=Legacy(*self.args)
        return self._old
    def runs(self,root=None):
        with self.rf.store.open(root) as (_,db,_),db.transaction() as s:return [dict(id=r.id,**r.details) for r in s.scalars(select(TrainingRun))]
    def configuration_preflight(self,payload):return (self.rf if payload.get('model')==MODEL else self.legacy()).configuration_preflight(payload)
    def train(self,context,payload):return (self.rf if payload.get('model')==MODEL else self.legacy()).train(context,payload)
    def validate(self,context,payload):return self.train(context,dict(payload,operation='validate',resume_run_id=None))
    def preflight(self,*a,**kw):return self.legacy().preflight(*a,**kw)
    def rf_devices(self):return self.rf.devices_snapshot()
