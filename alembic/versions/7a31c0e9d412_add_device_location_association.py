"""add_device_location_association

Revision ID: 7a31c0e9d412
Revises: 489d150b0f71
Create Date: 2026-11-13 00:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '7a31c0e9d412'
down_revision: Union[str, Sequence[str], None] = '489d150b0f71'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Use batch_alter_table for universal compatibility across PostgreSQL and SQLite
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.add_column(sa.Column('location_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            'fk_device_location_org',
            'locations',
            ['location_id', 'organization_id'],
            ['id', 'organization_id'],
            ondelete='RESTRICT',
        )
        batch_op.create_index('ix_devices_location_id', ['location_id'])


def downgrade() -> None:
    with op.batch_alter_table('devices', schema=None) as batch_op:
        batch_op.drop_index('ix_devices_location_id')
        batch_op.drop_constraint('fk_device_location_org', type_='foreignkey')
        batch_op.drop_column('location_id')
