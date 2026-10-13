"""P2必要实体与Job负载；迁移只新增，不删除P1数据。"""
from alembic import op
import sqlalchemy as sa
revision = '0003'
down_revision = '0002'
branch_labels = depends_on = None

def table(name, fields, constraints=()):
    op.create_table(name, sa.Column('id', sa.String(36), primary_key=True),
                    *[sa.Column(key, datatype, *([sa.ForeignKey(foreign)] if foreign else []), nullable=nullable, unique=unique) for key, datatype, foreign, nullable, unique in fields], *constraints)
def f(name, datatype=sa.Text(), foreign=None, nullable=False, unique=False): return name, datatype, foreign, nullable, unique
def upgrade():
    op.add_column('jobs', sa.Column('payload', sa.JSON(), nullable=False, server_default='{}'))
    op.add_column('jobs', sa.Column('result', sa.JSON(), nullable=False, server_default='{}'))
    table('media_assets', [f('project_id',sa.String(36)),f('name'),f('original_path'),f('path'),f('mode',sa.String(10)),f('sha256',sa.String(64)),f('size',sa.Integer()),f('video',sa.JSON()),f('camera'),f('equipment'),f('site'),f('state',sa.String(20)),f('error'),f('job_id',sa.String(36)),f('imported_at',sa.String(40))])
    table('frames', [f('media_id',sa.String(36),'media_assets.id'),f('pts_us',sa.Integer()),f('time_us',sa.Integer()),f('frame_index',sa.Integer(),nullable=True),f('width',sa.Integer()),f('height',sa.Integer()),f('path'),f('sha256',sa.String(64)),f('perceptual_hash',sa.String(16)),f('method',sa.String(30)),f('parameters',sa.JSON()),f('parameters_hash',sa.String(64)),f('job_id',sa.String(36)),f('created_at',sa.String(40))], [sa.UniqueConstraint('media_id','pts_us','parameters_hash')])
    table('label_categories', [f('name',sa.String(120)),f('description'),f('device_type'),f('parent_id',sa.String(36),'label_categories.id',nullable=True),f('annotation_type',sa.String(20)),f('enabled',sa.Integer()),f('revision',sa.Integer())])
    table('annotations', [f('frame_id',sa.String(36),'frames.id',unique=True),f('payload',sa.JSON()),f('status',sa.String(20)),f('revision',sa.Integer()),f('source',sa.String(30)),f('updated_at',sa.String(40))])
    table('annotation_revisions', [f('annotation_id',sa.String(36),'annotations.id'),f('revision',sa.Integer()),f('payload',sa.JSON()),f('status',sa.String(20)),f('source',sa.String(30)),f('created_at',sa.String(40))], [sa.UniqueConstraint('annotation_id','revision')])
    table('rois', [f('scope',sa.String(250),unique=True),f('media_id',sa.String(36),'media_assets.id'),f('camera'),f('payload',sa.JSON()),f('revision',sa.Integer()),f('updated_at',sa.String(40))])
    table('clip_labels', [f('media_id',sa.String(36),'media_assets.id'),f('start_us',sa.Integer()),f('end_us',sa.Integer()),f('tag',sa.String(20)),f('label_id',sa.String(36),'label_categories.id',nullable=True),f('status',sa.String(20)),f('revision',sa.Integer()),f('source',sa.String(30)),f('updated_at',sa.String(40)),f('history',sa.JSON()),f('deleted',sa.Integer())])
    table('datasets', [f('name',sa.String(120)),f('created_at',sa.String(40))])
    table('dataset_versions', [f('dataset_id',sa.String(36),'datasets.id'),f('number',sa.Integer()),f('path'),f('sha256',sa.String(64)),f('summary',sa.JSON()),f('created_at',sa.String(40))], [sa.UniqueConstraint('dataset_id','number')])
    table('dataset_samples', [f('version_id',sa.String(36),'dataset_versions.id'),f('frame_id',sa.String(36),'frames.id'),f('split',sa.String(10)),f('sha256',sa.String(64)),f('annotation',sa.JSON())], [sa.UniqueConstraint('version_id','frame_id')])
    table('exports', [f('version_id',sa.String(36),'dataset_versions.id'),f('format',sa.String(30)),f('path'),f('sha256',sa.String(64)),f('created_at',sa.String(40))])
def downgrade(): raise RuntimeError('禁止自动降级/删除用户数据。')
