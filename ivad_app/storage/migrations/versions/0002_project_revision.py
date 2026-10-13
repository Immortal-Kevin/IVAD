from alembic import op
import sqlalchemy as sa
revision = '0002'
down_revision = '0001'
branch_labels = depends_on = None

def upgrade():
    op.add_column('projects', sa.Column('revision', sa.Integer(), nullable=False, server_default='1'))

def downgrade():
    raise RuntimeError('禁止自动降级或删除用户数据。')
