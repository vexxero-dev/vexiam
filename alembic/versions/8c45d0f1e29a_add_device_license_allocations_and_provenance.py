"""add_device_license_allocations_and_provenance

Revision ID: 8c45d0f1e29a
Revises: 7a31c0e9d412
Create Date: 2026-11-13 21:25:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8c45d0f1e29a'
down_revision: Union[str, Sequence[str], None] = '7a31c0e9d412'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add applications table columns
    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.add_column(sa.Column('platform_type', sa.String(length=30), server_default='WINDOWS_DESKTOP', nullable=False))
        batch_op.add_column(sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False))
        batch_op.add_column(sa.Column('current_version', sa.String(length=30), server_default='1.0.0', nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))

    # 2. Create application_clients table
    op.create_table(
        'application_clients',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('client_code', sa.String(length=64), nullable=False),
        sa.Column('client_name', sa.String(length=150), nullable=False),
        sa.Column('client_type', sa.String(length=30), server_default='DESKTOP', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_application_clients_application_id', 'application_clients', ['application_id'])
    op.create_index('ix_application_clients_client_code', 'application_clients', ['client_code'], unique=True)

    # 3. Create application_installations table
    op.create_table(
        'application_installations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('application_id', sa.UUID(), nullable=False),
        sa.Column('device_id', sa.UUID(), nullable=False),
        sa.Column('installation_id', sa.String(length=64), nullable=False),
        sa.Column('version', sa.String(length=30), server_default='1.0.0', nullable=False),
        sa.Column('platform', sa.String(length=30), server_default='WINDOWS', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='ACTIVE', nullable=False),
        sa.Column('registered_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['application_id'], ['applications.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['device_id'], ['devices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('application_id', 'device_id', 'installation_id', name='uq_app_device_installation'),
    )
    op.create_index('ix_application_installations_application_id', 'application_installations', ['application_id'])
    op.create_index('ix_application_installations_device_id', 'application_installations', ['device_id'])
    op.create_index('ix_application_installations_installation_id', 'application_installations', ['installation_id'])

    # 4. Add current_subscription_id, installation_id, organization_id, revoked_at, created_at, updated_at to device_licenses
    with op.batch_alter_table('device_licenses', schema=None) as batch_op:
        batch_op.add_column(sa.Column('current_subscription_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('installation_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('organization_id', sa.UUID(), nullable=True))
        batch_op.add_column(sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.add_column(sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
        batch_op.create_foreign_key(
            'fk_device_license_subscription',
            'subscriptions',
            ['current_subscription_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_foreign_key(
            'fk_device_license_installation',
            'application_installations',
            ['installation_id'],
            ['id'],
            ondelete='SET NULL',
        )
        batch_op.create_foreign_key(
            'fk_device_license_organization',
            'organizations',
            ['organization_id'],
            ['id'],
            ondelete='CASCADE',
        )
        batch_op.create_index('ix_device_licenses_current_subscription_id', ['current_subscription_id'])
        batch_op.create_index('ix_device_licenses_installation_id', ['installation_id'])
        batch_op.create_index('ix_device_licenses_organization_id', ['organization_id'])

    # 5. Create device_license_allocations table
    op.create_table(
        'device_license_allocations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('device_license_id', sa.UUID(), nullable=False),
        sa.Column('subscription_id', sa.UUID(), nullable=False),
        sa.Column('allocation_status', sa.String(length=32), nullable=False),
        sa.Column('allocated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_reason', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['device_license_id'], ['device_licenses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subscription_id'], ['subscriptions.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_device_license_allocations_device_license_id', 'device_license_allocations', ['device_license_id'])
    op.create_index('ix_device_license_allocations_subscription_id', 'device_license_allocations', ['subscription_id'])
    op.create_index('ix_device_license_allocations_allocation_status', 'device_license_allocations', ['allocation_status'])


def downgrade() -> None:
    op.drop_index('ix_device_license_allocations_allocation_status', table_name='device_license_allocations')
    op.drop_index('ix_device_license_allocations_subscription_id', table_name='device_license_allocations')
    op.drop_index('ix_device_license_allocations_device_license_id', table_name='device_license_allocations')
    op.drop_table('device_license_allocations')

    with op.batch_alter_table('device_licenses', schema=None) as batch_op:
        batch_op.drop_index('ix_device_licenses_organization_id')
        batch_op.drop_index('ix_device_licenses_installation_id')
        batch_op.drop_index('ix_device_licenses_current_subscription_id')
        batch_op.drop_constraint('fk_device_license_organization', type_='foreignkey')
        batch_op.drop_constraint('fk_device_license_installation', type_='foreignkey')
        batch_op.drop_constraint('fk_device_license_subscription', type_='foreignkey')
        batch_op.drop_column('updated_at')
        batch_op.drop_column('created_at')
        batch_op.drop_column('revoked_at')
        batch_op.drop_column('organization_id')
        batch_op.drop_column('installation_id')
        batch_op.drop_column('current_subscription_id')

    op.drop_index('ix_application_installations_installation_id', table_name='application_installations')
    op.drop_index('ix_application_installations_device_id', table_name='application_installations')
    op.drop_index('ix_application_installations_application_id', table_name='application_installations')
    op.drop_table('application_installations')

    op.drop_index('ix_application_clients_client_code', table_name='application_clients')
    op.drop_index('ix_application_clients_application_id', table_name='application_clients')
    op.drop_table('application_clients')

    with op.batch_alter_table('applications', schema=None) as batch_op:
        batch_op.drop_column('updated_at')
        batch_op.drop_column('current_version')
        batch_op.drop_column('status')
        batch_op.drop_column('platform_type')
