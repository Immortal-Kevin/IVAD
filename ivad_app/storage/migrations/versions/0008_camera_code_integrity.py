"""Enforce nonempty camera codes per project database; reject legacy conflicts."""
from alembic import op
revision='0008'
down_revision='0007'
branch_labels=depends_on=None
def upgrade():
    connection=op.get_bind()
    duplicates=connection.exec_driver_sql("SELECT trim(json_extract(details, '$.code')), count(*) FROM cameras WHERE coalesce(trim(json_extract(details, '$.code')), '') != '' GROUP BY trim(json_extract(details, '$.code')) HAVING count(*) > 1").fetchall()
    if duplicates:
        raise RuntimeError('摄像头编号存在历史重复，停止迁移，请人工核对；不修改原记录。')
    op.execute("CREATE UNIQUE INDEX uq_camera_code ON cameras(trim(json_extract(details, '$.code'))) WHERE coalesce(trim(json_extract(details, '$.code')), '') != ''")
def downgrade():
    raise RuntimeError('禁止自动降级。')
