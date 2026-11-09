import uuid
from datetime import datetime, timezone
import enum
from typing import Any
from sqlalchemy import BigInteger, DateTime, ForeignKey, String, Enum as SQLEnum, Index, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class SyncEventType(str, enum.Enum):
    IDENTITY_CREATED = "IDENTITY_CREATED"
    IDENTITY_UPDATED = "IDENTITY_UPDATED"
    IDENTITY_SUSPENDED = "IDENTITY_SUSPENDED"
    IDENTITY_DELETED = "IDENTITY_DELETED"
    
    MEMBERSHIP_CREATED = "MEMBERSHIP_CREATED"
    MEMBERSHIP_UPDATED = "MEMBERSHIP_UPDATED"
    MEMBERSHIP_REVOKED = "MEMBERSHIP_REVOKED"
    
    APPLICATION_ASSIGNED = "APPLICATION_ASSIGNED"
    APPLICATION_ASSIGNMENT_UPDATED = "APPLICATION_ASSIGNMENT_UPDATED"
    APPLICATION_ACCESS_REVOKED = "APPLICATION_ACCESS_REVOKED"
    
    ROLE_CREATED = "ROLE_CREATED"
    ROLE_UPDATED = "ROLE_UPDATED"
    ROLE_DELETED = "ROLE_DELETED"
    
    PERMISSIONS_CHANGED = "PERMISSIONS_CHANGED"


class IdentitySyncEvent(Base):
    """
    Monotonically sequenced event log for one-way sync (Cloud -> Local replica).
    """
    __tablename__ = "identity_sync_events"
    __table_args__ = (
        Index("ix_sync_events_org_seq", "organization_id", "sequence"),
        Index("ix_sync_events_org_app_seq", "organization_id", "application_id", "sequence"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    sequence: Mapped[int] = mapped_column(
        BigInteger, autoincrement=True, unique=True, index=True, nullable=False
    )
    event_type: Mapped[SyncEventType] = mapped_column(
        SQLEnum(SyncEventType, native_enum=False), nullable=False
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    entity_id: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(default=1, nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True
    )
