"""add_identity_sync_events_and_versioning

Revision ID: b728a41df2a1
Revises: 90bd8e15c23e
Create Date: 2026-11-09 22:05:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b728a41df2a1'
down_revision: Union[str, Sequence[str], None] = '90bd8e15c23e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add identity_version to users table
    op.add_column('users', sa.Column('identity_version', sa.Integer(), nullable=False, server_default='1'))

    # 2. Add status and membership_version to organization_members table
    op.add_column('organization_members', sa.Column('status', sa.String(length=50), nullable=False, server_default='ACTIVE'))
    op.add_column('organization_members', sa.Column('membership_version', sa.Integer(), nullable=False, server_default='1'))

    # 3. Add role_version to application_roles table
    op.add_column('application_roles', sa.Column('role_version', sa.Integer(), nullable=False, server_default='1'))

    # 4. Add assignment_version to application_assignments table
    op.add_column('application_assignments', sa.Column('assignment_version', sa.Integer(), nullable=False, server_default='1'))

    # 5. Create identity_sync_events table
    op.create_table(
        'identity_sync_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('sequence', sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column('event_type', sa.String(length=64), nullable=False),
        sa.Column('organization_id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=True),
        sa.Column('entity_id', sa.String(length=64), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('payload', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sequence')
    )
    op.create_index('ix_identity_sync_events_sequence', 'identity_sync_events', ['sequence'])
    op.create_index('ix_sync_events_org_seq', 'identity_sync_events', ['organization_id', 'sequence'])
    op.create_index('ix_sync_events_org_app_seq', 'identity_sync_events', ['organization_id', 'application_id', 'sequence'])


def downgrade() -> None:
    op.drop_index('ix_sync_events_org_app_seq', table_name='identity_sync_events')
    op.drop_index('ix_sync_events_org_seq', table_name='identity_sync_events')
    op.drop_index('ix_identity_sync_events_sequence', table_name='identity_sync_events')
    op.drop_table('identity_sync_events')

    op.drop_column('application_assignments', 'assignment_version')
    op.drop_column('application_roles', 'role_version')
    op.drop_column('organization_members', 'membership_version')
    op.drop_column('organization_members', 'status')
    op.drop_column('users', 'identity_version')
