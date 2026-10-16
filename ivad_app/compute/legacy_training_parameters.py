"""Existing IVAD parameter validation, separated from legacy worker orchestration."""
import math
from ivad_app.core.contracts import AppError
DEFAULTS={'epochs':20,'imgsz':640,'batch':4,'lr0':0.01,'optimizer':'SGD','weight_decay':0.0005,'augment':True,'patience':10,'seed':123,'amp':False}

def validate_parameters(values):
    p=dict(DEFAULTS,**values)
    for key,lo,hi in [('epochs',1,10000),('imgsz',64,2048),('batch',1,64),('patience',0,10000),('seed',0,2147483647)]:
        if isinstance(p[key],bool) or not isinstance(p[key],int) or not lo<=p[key]<=hi:raise AppError('TRAIN_PARAMETER',f'{key}数值超出范围。')
    if p['imgsz']%32:raise AppError('TRAIN_PARAMETER','图像尺寸须为32的整数倍。')
    for key,lo,hi in [('lr0',0.000001,1),('weight_decay',0,1)]:
        if isinstance(p[key],bool) or not isinstance(p[key],(int,float)) or not math.isfinite(p[key]) or not lo<=p[key]<=hi:raise AppError('TRAIN_PARAMETER',f'{key}数值无效。')
    if p['optimizer'] not in {'SGD','Adam','AdamW','auto'} or type(p['amp']) is not bool or type(p['augment']) is not bool:raise AppError('TRAIN_PARAMETER','优化器/增强/精度设置无效。')
    if set(p)-set(DEFAULTS):raise AppError('TRAIN_PARAMETER','不支持的训练参数。')
    return p
