import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DeviceStatus(str, enum.Enum):
    PENDING_ACTIVATION = "PENDING_ACTIVATION"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    DECOMMISSIONED = "DECOMMISSIONED"


class LicenseStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("organization_id", "fingerprint", name="uq_org_device_fingerprint"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Terminal 01 - Cashier Counter"
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)  # Hardware machine-id/hash
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # Device's Ed25519 public key (Base64)
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, native_enum=False), default=DeviceStatus.ACTIVE, nullable=False
    )
    last_sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    licenses: Mapped[list["DeviceLicense"]] = relationship(
        "DeviceLicense", back_populates="device", cascade="all, delete-orphan"
    )


class DeviceChallenge(Base):
    __tablename__ = "device_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class DeviceLicense(Base):
    __tablename__ = "device_licenses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    signed_payload: Mapped[str] = mapped_column(Text, nullable=False)
    signature: Mapped[str] = mapped_column(Text, nullable=False)  # VEX IAM Ed25519 Signature
    status: Mapped[LicenseStatus] = mapped_column(
        SQLEnum(LicenseStatus, native_enum=False), default=LicenseStatus.ACTIVE, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    device: Mapped["Device"] = relationship("Device", back_populates="licenses")
    application: Mapped["app.domains.applications.models.Application"] = relationship("Application")
