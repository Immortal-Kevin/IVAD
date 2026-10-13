"""冻结P1初始Schema，不依赖以后变化的ORM定义。"""
from alembic import op
import sqlalchemy as sa
revision = '0001'
down_revision = None
branch_labels = depends_on = None

def upgrade():
    op.create_table('projects', sa.Column('id', sa.String(36), primary_key=True), sa.Column('name', sa.String(120), nullable=False), sa.Column('description', sa.Text(), nullable=False), sa.Column('site', sa.String(200), nullable=False), sa.Column('created_at', sa.String(40), nullable=False), sa.Column('updated_at', sa.String(40), nullable=False))
    op.create_table('settings', sa.Column('key', sa.String(80), primary_key=True), sa.Column('value', sa.JSON(), nullable=False))
    op.create_table('jobs', sa.Column('id', sa.String(36), primary_key=True), sa.Column('project_id', sa.String(36)), sa.Column('kind', sa.String(50), nullable=False), sa.Column('state', sa.String(20), nullable=False), sa.Column('progress', sa.Integer(), nullable=False), sa.Column('created_at', sa.String(40), nullable=False), sa.Column('updated_at', sa.String(40), nullable=False), sa.Column('error', sa.Text(), nullable=False))
    op.create_table('devices', sa.Column('id', sa.String(120), primary_key=True), sa.Column('payload', sa.JSON(), nullable=False), sa.Column('checked_at', sa.String(40), nullable=False))
    op.create_table('logs', sa.Column('id', sa.String(36), primary_key=True), sa.Column('timestamp', sa.String(40), nullable=False), sa.Column('level', sa.String(10), nullable=False), sa.Column('category', sa.String(40), nullable=False), sa.Column('message', sa.Text(), nullable=False), sa.Column('job_id', sa.String(36)), sa.Column('trace', sa.Text(), nullable=False))
    op.create_index('ix_logs_timestamp', 'logs', ['timestamp'])
    op.create_index('ix_logs_job_id', 'logs', ['job_id'])

def downgrade():
    raise RuntimeError('禁止自动降级或删除用户数据。')
