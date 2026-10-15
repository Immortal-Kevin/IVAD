"""P1实际数据库实体，不提前创建未来业务表。"""
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Integer, JSON, ForeignKey, UniqueConstraint

class Base(DeclarativeBase):
    pass

class ProjectRecord(Base):
    __tablename__ = 'projects'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default='')
    site: Mapped[str] = mapped_column(String(200), default='')
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))
    revision: Mapped[int] = mapped_column(Integer, default=1)

class SettingRecord(Base):
    __tablename__ = 'settings'
    key: Mapped[str] = mapped_column(String(80), primary_key=True)
    value: Mapped[dict] = mapped_column(JSON)

class JobRecord(Base):
    __tablename__ = 'jobs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    kind: Mapped[str] = mapped_column(String(50))
    state: Mapped[str] = mapped_column(String(20))
    progress: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[str] = mapped_column(String(40))
    updated_at: Mapped[str] = mapped_column(String(40))
    error: Mapped[str] = mapped_column(Text, default='')
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    result: Mapped[dict] = mapped_column(JSON, default=dict)

class DeviceRecord(Base):
    __tablename__ = 'devices'
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    payload: Mapped[dict] = mapped_column(JSON)
    checked_at: Mapped[str] = mapped_column(String(40))

class LogRecord(Base):
    __tablename__ = 'logs'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    timestamp: Mapped[str] = mapped_column(String(40), index=True)
    level: Mapped[str] = mapped_column(String(10))
    category: Mapped[str] = mapped_column(String(40))
    message: Mapped[str] = mapped_column(Text)
    job_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    trace: Mapped[str] = mapped_column(Text, default='')

class MediaAsset(Base):
    __tablename__ = 'media_assets'
    kind: Mapped[str] = mapped_column(String(16), default='ORIGINAL')
    parent_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    clip_info: Mapped[dict] = mapped_column(JSON, default=dict)
    lifecycle: Mapped[dict] = mapped_column(JSON, default=dict)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    project_id: Mapped[str] = mapped_column(String(36))
    name: Mapped[str] = mapped_column(Text)
    original_path: Mapped[str] = mapped_column(Text)
    path: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(10))
    sha256: Mapped[str] = mapped_column(String(64))
    size: Mapped[int] = mapped_column(Integer)
    video: Mapped[dict] = mapped_column(JSON, default=dict)
    camera: Mapped[str] = mapped_column(String(200), default='')
    camera_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    equipment: Mapped[str] = mapped_column(String(200), default='')
    site: Mapped[str] = mapped_column(String(200), default='')
    state: Mapped[str] = mapped_column(String(20))
    error: Mapped[str] = mapped_column(Text, default='')
    job_id: Mapped[str] = mapped_column(String(36), default='')
    imported_at: Mapped[str] = mapped_column(String(40))

class ExtractedFrame(Base):
    __tablename__ = 'frames'
    __table_args__ = (UniqueConstraint('media_id', 'pts_us', 'parameters_hash'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    media_id: Mapped[str] = mapped_column(ForeignKey('media_assets.id'))
    pts_us: Mapped[int] = mapped_column(Integer)
    time_us: Mapped[int] = mapped_column(Integer)
    frame_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int] = mapped_column(Integer)
    height: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    perceptual_hash: Mapped[str] = mapped_column(String(16))
    method: Mapped[str] = mapped_column(String(30))
    parameters: Mapped[dict] = mapped_column(JSON)
    parameters_hash: Mapped[str] = mapped_column(String(64))
    job_id: Mapped[str] = mapped_column(String(36))
    created_at: Mapped[str] = mapped_column(String(40))
    handling: Mapped[dict] = mapped_column(JSON, default=dict)

class Camera(Base):
    __tablename__ = 'cameras'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    legacy_key: Mapped[str | None] = mapped_column(String(200), unique=True, nullable=True)
    revision: Mapped[int] = mapped_column(Integer, default=1)
    history: Mapped[list] = mapped_column(JSON, default=list)
    details: Mapped[dict] = mapped_column(JSON, default=dict)

class LabelCategory(Base):
    __tablename__ = 'label_categories'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    description: Mapped[str] = mapped_column(Text, default='')
    device_type: Mapped[str] = mapped_column(String(200), default='')
    parent_id: Mapped[str | None] = mapped_column(ForeignKey('label_categories.id'), nullable=True)
    annotation_type: Mapped[str] = mapped_column(String(20), default='box')
    enabled: Mapped[int] = mapped_column(Integer, default=1)
    revision: Mapped[int] = mapped_column(Integer, default=1)

class Annotation(Base):
    __tablename__ = 'annotations'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    frame_id: Mapped[str] = mapped_column(ForeignKey('frames.id'), unique=True)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[str] = mapped_column(String(40))

class AnnotationRevision(Base):
    __tablename__ = 'annotation_revisions'
    __table_args__ = (UniqueConstraint('annotation_id', 'revision'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    annotation_id: Mapped[str] = mapped_column(ForeignKey('annotations.id'))
    revision: Mapped[int] = mapped_column(Integer)
    payload: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20))
    source: Mapped[str] = mapped_column(String(30))
    created_at: Mapped[str] = mapped_column(String(40))

class RegionOfInterest(Base):
    __tablename__ = 'rois'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    scope: Mapped[str] = mapped_column(String(250), unique=True)
    media_id: Mapped[str] = mapped_column(ForeignKey('media_assets.id'))
    camera: Mapped[str] = mapped_column(String(200))
    camera_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer)
    updated_at: Mapped[str] = mapped_column(String(40))

class VideoClipLabel(Base):
    __tablename__ = 'clip_labels'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    media_id: Mapped[str] = mapped_column(ForeignKey('media_assets.id'))
    start_us: Mapped[int] = mapped_column(Integer)
    end_us: Mapped[int] = mapped_column(Integer)
    tag: Mapped[str] = mapped_column(String(20))
    label_id: Mapped[str | None] = mapped_column(ForeignKey('label_categories.id'), nullable=True)
    status: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String(30))
    updated_at: Mapped[str] = mapped_column(String(40))
    history: Mapped[list] = mapped_column(JSON, default=list)
    deleted: Mapped[int] = mapped_column(Integer, default=0)

class Dataset(Base):
    __tablename__ = 'datasets'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    created_at: Mapped[str] = mapped_column(String(40))

class DatasetVersion(Base):
    __tablename__ = 'dataset_versions'
    __table_args__ = (UniqueConstraint('dataset_id', 'number'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(ForeignKey('datasets.id'))
    number: Mapped[int] = mapped_column(Integer)
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    summary: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[str] = mapped_column(String(40))

class DatasetSample(Base):
    __tablename__ = 'dataset_samples'
    __table_args__ = (UniqueConstraint('version_id', 'frame_id'),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey('dataset_versions.id'))
    frame_id: Mapped[str] = mapped_column(ForeignKey('frames.id'))
    split: Mapped[str] = mapped_column(String(10))
    sha256: Mapped[str] = mapped_column(String(64))
    annotation: Mapped[dict] = mapped_column(JSON)

class ExportRecord(Base):
    __tablename__ = 'exports'
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    version_id: Mapped[str] = mapped_column(ForeignKey('dataset_versions.id'))
    format: Mapped[str] = mapped_column(String(30))
    path: Mapped[str] = mapped_column(Text)
    sha256: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[str] = mapped_column(String(40))

class TrainingRun(Base):
    __tablename__='training_runs'
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    details: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer)

class ModelVersion(Base):
    __tablename__='model_versions'
    id: Mapped[str] = mapped_column(String(36),primary_key=True)
    details: Mapped[dict] = mapped_column(JSON)
    revision: Mapped[int] = mapped_column(Integer)
