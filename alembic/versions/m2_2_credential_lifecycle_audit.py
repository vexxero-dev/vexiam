"""Milestone 2.2: Extend DeviceChallenge for bound PoP and add TerminalSecurityAudit.

Revision ID: m2_2_credential_lifecycle
Revises: m2_1_logical_terminal
Create Date: 2026-11-27 22:52:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m2_2_credential_lifecycle"
down_revision: Union[str, Sequence[str], None] = "m2_1_logical_terminal"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("device_challenges", sa.Column("organization_id", sa.UUID(), nullable=True))
    op.add_column("device_challenges", sa.Column("device_id", sa.UUID(), nullable=True))
    op.add_column("device_challenges", sa.Column("actor_user_id", sa.UUID(), nullable=True))
    op.add_column("device_challenges", sa.Column("operation", sa.String(length=32), nullable=True))
    op.add_column("device_challenges", sa.Column("expected_public_key_hash", sa.String(length=64), nullable=True))
    op.create_index("ix_device_challenges_organization_id", "device_challenges", ["organization_id"], unique=False)
    op.create_index("ix_device_challenges_device_id", "device_challenges", ["device_id"], unique=False)

    op.create_table(
        "terminal_security_audits",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("organization_id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("terminal_id", sa.String(length=128), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("operation", sa.String(length=32), nullable=False),
        sa.Column("actor_user_id", sa.UUID(), nullable=False),
        sa.Column("previous_credential_id", sa.UUID(), nullable=True),
        sa.Column("new_credential_id", sa.UUID(), nullable=True),
        sa.Column("previous_status", sa.String(length=32), nullable=True),
        sa.Column("new_status", sa.String(length=32), nullable=True),
        sa.Column("reason", sa.String(length=256), nullable=True),
        sa.Column("installation_replacement_authorized", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organizations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_terminal_security_audits_organization_id", "terminal_security_audits", ["organization_id"], unique=False)
    op.create_index("ix_terminal_security_audits_device_id", "terminal_security_audits", ["device_id"], unique=False)
    op.create_index("ix_terminal_security_audits_terminal_id", "terminal_security_audits", ["terminal_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_terminal_security_audits_terminal_id", table_name="terminal_security_audits")
    op.drop_index("ix_terminal_security_audits_device_id", table_name="terminal_security_audits")
    op.drop_index("ix_terminal_security_audits_organization_id", table_name="terminal_security_audits")
    op.drop_table("terminal_security_audits")
    op.drop_index("ix_device_challenges_device_id", table_name="device_challenges")
    op.drop_index("ix_device_challenges_organization_id", table_name="device_challenges")
    op.drop_column("device_challenges", "expected_public_key_hash")
    op.drop_column("device_challenges", "operation")
    op.drop_column("device_challenges", "actor_user_id")
    op.drop_column("device_challenges", "device_id")
    op.drop_column("device_challenges", "organization_id")
