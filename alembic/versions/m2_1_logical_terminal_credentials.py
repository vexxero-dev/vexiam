"""Milestone 2.1: Add logical terminal_id and DeviceCredential table.

Revision ID: m2_1_logical_terminal
Revises: 8c45d0f1e29a
Create Date: 2026-11-27 22:42:00.000000
"""
import base64
import hashlib
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "m2_1_logical_terminal"
down_revision: Union[str, Sequence[str], None] = "8c45d0f1e29a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add terminal_id to devices (nullable initially for safe backfill)
    op.add_column("devices", sa.Column("terminal_id", sa.String(length=128), nullable=True))
    op.create_unique_constraint("uq_org_terminal_id", "devices", ["organization_id", "terminal_id"])

    # 2. Create device_credentials table
    op.create_table(
        "device_credentials",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("device_id", sa.UUID(), nullable=False),
        sa.Column("public_key", sa.Text(), nullable=False),
        sa.Column("key_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("credential_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False, server_default="ACTIVE"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["device_id"], ["devices.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("device_id", "credential_version", name="uq_device_credential_version"),
    )
    op.create_index("ix_device_credentials_device_id", "device_credentials", ["device_id"], unique=False)
    op.create_index("ix_device_credentials_key_fingerprint", "device_credentials", ["key_fingerprint"], unique=False)
    op.create_index(
        "uq_device_active_credential",
        "device_credentials",
        ["device_id"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )
    op.create_index(
        "uq_active_credential_fingerprint",
        "device_credentials",
        ["key_fingerprint"],
        unique=True,
        postgresql_where=sa.text("status = 'ACTIVE'"),
        sqlite_where=sa.text("status = 'ACTIVE'"),
    )

    # 3. Backfill terminal_id and DeviceCredential 1:1
    conn = op.get_bind()
    devices = conn.execute(
        sa.text("SELECT id, organization_id, fingerprint, public_key, created_at FROM devices")
    ).fetchall()

    seen_org_term: set[tuple[str, str]] = set()
    for dev_id, org_id, fp, pub_key, created_at in devices:
        term_id = fp if fp and str(fp).strip() else str(dev_id)
        key_pair = (str(org_id), term_id)
        if key_pair in seen_org_term:
            raise RuntimeError(
                f"Ambiguous legacy terminal_id '{term_id}' in organization '{org_id}'. Manual resolution required."
            )
        seen_org_term.add(key_pair)

        conn.execute(
            sa.text("UPDATE devices SET terminal_id = :tid WHERE id = :did"),
            {"tid": term_id, "did": dev_id},
        )

        try:
            raw_pub = base64.b64decode(pub_key.strip(), validate=True)
            if len(raw_pub) != 32:
                raise ValueError(f"Expected 32-byte Ed25519 key, got {len(raw_pub)} bytes")
            from cryptography.hazmat.primitives.asymmetric import ed25519
            ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
        except Exception as exc:
            raise RuntimeError(
                f"Invalid Ed25519 public_key on device '{dev_id}': {exc}"
            ) from exc

        key_fp = hashlib.sha256(raw_pub).hexdigest()
        conn.execute(
            sa.text(
                "INSERT INTO device_credentials (id, device_id, public_key, key_fingerprint, credential_version, status, created_at) "
                "VALUES (:cid, :did, :pk, :kfp, 1, 'ACTIVE', :cat)"
            ),
            {
                "cid": str(uuid.uuid4()),
                "did": dev_id,
                "pk": pub_key,
                "kfp": key_fp,
                "cat": created_at,
            },
        )


    # 4. Enforce NOT NULL on terminal_id after backfill verification
    null_count = conn.execute(sa.text("SELECT COUNT(*) FROM devices WHERE terminal_id IS NULL")).scalar_one()
    if null_count:
        raise RuntimeError(f"Backfill incomplete: {null_count} devices still have NULL terminal_id.")
    op.alter_column("devices", "terminal_id", existing_type=sa.String(length=128), nullable=False)


def downgrade() -> None:
    """DESTRUCTIVE: Drops device_credentials and removes credential history. Do not run in production to roll back app code."""
    op.drop_index("uq_active_credential_fingerprint", table_name="device_credentials")
    op.drop_index("uq_device_active_credential", table_name="device_credentials")
    op.drop_index("ix_device_credentials_key_fingerprint", table_name="device_credentials")
    op.drop_index("ix_device_credentials_device_id", table_name="device_credentials")
    op.drop_table("device_credentials")
    op.drop_constraint("uq_org_terminal_id", "devices", type_="unique")
    op.drop_column("devices", "terminal_id")
