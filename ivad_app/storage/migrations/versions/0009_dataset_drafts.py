"""Persist lifecycle metadata and draft in the existing Dataset row."""
from alembic import op
import sqlalchemy as sa
revision='0009'
down_revision='0008'
branch_labels=depends_on=None

def upgrade():
    op.add_column('datasets',sa.Column('details',sa.JSON(),nullable=False,server_default='{}'))
    op.add_column('datasets',sa.Column('revision',sa.Integer(),nullable=False,server_default='0'))

def downgrade():raise RuntimeError('禁止自动降级。')
