"""Add reversible exclusion metadata and UUID cameras; no table rebuild."""
import json
from uuid import uuid4
from alembic import op
import sqlalchemy as sa
revision='0005'
down_revision='0004'
branch_labels=depends_on=None
def upgrade():
    op.create_table('cameras',sa.Column('id',sa.String(36),primary_key=True),sa.Column('name',sa.String(200),nullable=False),sa.Column('legacy_key',sa.String(200),unique=True,nullable=True),sa.Column('revision',sa.Integer(),nullable=False),sa.Column('history',sa.JSON(),nullable=False))
    op.add_column('media_assets',sa.Column('camera_id',sa.String(36),nullable=True))
    op.add_column('rois',sa.Column('camera_id',sa.String(36),nullable=True))
    op.add_column('frames',sa.Column('handling',sa.JSON(),nullable=False,server_default='{}'))
    db=op.get_bind()
    keys={r[0] for r in db.execute(sa.text("SELECT camera FROM media_assets UNION SELECT camera FROM rois")) if r[0]}
    for key in sorted(keys):
        camera_id=str(uuid4())
        db.execute(sa.text('INSERT INTO cameras(id,name,legacy_key,revision,history) VALUES(:id,:name,:name,1,:history)'),{'id':camera_id,'name':key,'history':json.dumps([{'action':'MIGRATE_LEGACY','old_key':key}],ensure_ascii=False)})
        db.execute(sa.text('UPDATE media_assets SET camera_id=:id WHERE camera=:key'),{'id':camera_id,'key':key})
        db.execute(sa.text('UPDATE rois SET camera_id=:id,scope=:scope WHERE scope=:old'),{'id':camera_id,'scope':'camera:'+camera_id,'old':'camera:'+key})
def downgrade():raise RuntimeError('禁止自动降级或删除用户数据。')
