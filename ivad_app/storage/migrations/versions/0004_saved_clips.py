"""Add clip provenance without rebuilding media or existing project data."""
from alembic import op
import sqlalchemy as sa
revision='0004'
down_revision='0003'
branch_labels=depends_on=None
def upgrade():
    op.add_column('media_assets',sa.Column('kind',sa.String(16),nullable=False,server_default='ORIGINAL'))
    op.add_column('media_assets',sa.Column('parent_id',sa.String(36),nullable=True))
    op.add_column('media_assets',sa.Column('clip_info',sa.JSON(),nullable=False,server_default='{}'))
def downgrade():raise RuntimeError('禁止自动降级或删除用户数据。')
