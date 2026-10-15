"""Capability contract for model-specific adapters, independent of GUI and GPU environment."""
from dataclasses import dataclass
from typing import Protocol
from ivad_app.core.contracts import AppError

class ModelAdapter(Protocol):
    name: str
    task: str
    capabilities: frozenset[str]
    output_contract: str

@dataclass(frozen=True)
class YoloDetectionAdapter:
    name: str
    task: str='detect'
    capabilities: frozenset[str]=frozenset({'train','validate','export','import'})
    output_contract: str='raw_xywh_class_scores_non_end2end_then_nms'

ADAPTERS={name:YoloDetectionAdapter(name) for name in ['yolo26n','yolo11n']}
def adapter(name,capability):
    value=ADAPTERS.get(name)
    if not value or capability not in value.capabilities:raise AppError('MODEL_CAPABILITY','该模型适配器尚不支持所选能力。')
    return value
