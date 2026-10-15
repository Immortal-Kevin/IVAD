"""Append camera details and reversible media lifecycle, no P3 record rewrites."""
from alembic import op
import sqlalchemy as sa
revision='0007'
down_revision='0006'
branch_labels=depends_on=None
def upgrade():
    op.add_column('cameras',sa.Column('details',sa.JSON(),nullable=False,server_default='{}'))
    op.add_column('media_assets',sa.Column('lifecycle',sa.JSON(),nullable=False,server_default='{}'))
def downgrade():raise RuntimeError('禁止自动删除资料或降级。')
