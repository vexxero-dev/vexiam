"""Phase 2: Add terminal_installations, producer_epochs, and credential installation_id.

Revision ID: p2_1_installations_epochs
Revises: m2_2_credential_lifecycle
Create Date: 2026-11-28 13:18:30.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "p2_1_installations_epochs"
down_revision: Union[str, Sequence[str], None] = "m2_2_credential_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "terminal_installations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("terminal_id", sa.String(length=128), nullable=False),
        sa.Column("installation_id", sa.UUID(), nullable=False),
        sa.Column("database_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("current_epoch", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("fenced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fenced_reason", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "installation_id", name="uq_org_installation_id"),
    )
    op.create_index("ix_terminal_installations_organization_id", "terminal_installations", ["organization_id"], unique=False)
    op.create_index("ix_terminal_installations_device_id", "terminal_installations", ["device_id"], unique=False)
    op.create_index("ix_terminal_installations_terminal_id", "terminal_installations", ["terminal_id"], unique=False)
    op.create_index("ix_terminal_installations_installation_id", "terminal_installations", ["installation_id"], unique=True)

    op.create_table(
        "producer_epochs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("installation_id", sa.UUID(), nullable=False),
        sa.Column("epoch", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("allocated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("fenced_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["installation_id"], ["terminal_installations.installation_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "epoch", name="uq_device_producer_epoch"),
    )
    op.create_index("ix_producer_epochs_organization_id", "producer_epochs", ["organization_id"], unique=False)
    op.create_index("ix_producer_epochs_device_id", "producer_epochs", ["device_id"], unique=False)
    op.create_index("ix_producer_epochs_installation_id", "producer_epochs", ["installation_id"], unique=False)

    op.add_column("device_credentials", sa.Column("installation_id", sa.UUID(), nullable=True))
    op.create_index("ix_device_credentials_installation_id", "device_credentials", ["installation_id"], unique=False)
    op.create_foreign_key(
        "fk_device_credentials_installation_id",
        "device_credentials",
        "terminal_installations",
        ["installation_id"],
        ["installation_id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_device_credentials_installation_id", "device_credentials", type_="foreignkey")
    op.drop_index("ix_device_credentials_installation_id", table_name="device_credentials")
    op.drop_column("device_credentials", "installation_id")

    op.drop_index("ix_producer_epochs_installation_id", table_name="producer_epochs")
    op.drop_index("ix_producer_epochs_device_id", table_name="producer_epochs")
    op.drop_index("ix_producer_epochs_organization_id", table_name="producer_epochs")
    op.drop_table("producer_epochs")

    op.drop_index("ix_terminal_installations_installation_id", table_name="terminal_installations")
    op.drop_index("ix_terminal_installations_terminal_id", table_name="terminal_installations")
    op.drop_index("ix_terminal_installations_device_id", table_name="terminal_installations")
    op.drop_index("ix_terminal_installations_organization_id", table_name="terminal_installations")
    op.drop_table("terminal_installations")
