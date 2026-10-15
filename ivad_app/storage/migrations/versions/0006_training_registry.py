"""P3 append-only training and model registry, preserving P2 data."""
from alembic import op
import sqlalchemy as sa
revision='0006'
down_revision='0005'
branch_labels=depends_on=None
def upgrade():
    for name in ['training_runs','model_versions']:
        op.create_table(name,sa.Column('id',sa.String(36),primary_key=True),sa.Column('details',sa.JSON(),nullable=False),sa.Column('revision',sa.Integer(),nullable=False))
def downgrade():raise RuntimeError('禁止删除用户模型/训练历史。')
