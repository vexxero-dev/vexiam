import uuid
from datetime import datetime, timezone
import enum
from sqlalchemy import String, Text, DateTime, ForeignKey, ForeignKeyConstraint, Enum as SQLEnum, UniqueConstraint, Boolean, Index, Integer, text
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


class AllocationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"


class AllocationReleaseReason(str, enum.Enum):
    SUBSCRIPTION_EXPIRED = "SUBSCRIPTION_EXPIRED"
    SUBSCRIPTION_CANCELLED = "SUBSCRIPTION_CANCELLED"
    DEVICE_REVOKED = "DEVICE_REVOKED"
    MANUAL_REASSIGNMENT = "MANUAL_REASSIGNMENT"
    QUOTA_REBALANCED = "QUOTA_REBALANCED"


class CredentialStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"


class Device(Base):
    __tablename__ = "devices"
    __table_args__ = (
        UniqueConstraint("organization_id", "fingerprint", name="uq_org_device_fingerprint"),
        UniqueConstraint("organization_id", "terminal_id", name="uq_org_terminal_id"),
        ForeignKeyConstraint(
            ["location_id", "organization_id"],
            ["locations.id", "locations.organization_id"],
            name="fk_device_location_org",
            ondelete="RESTRICT",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., "Terminal 01 - Cashier Counter"
    terminal_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)  # Canonical logical terminal ID
    fingerprint: Mapped[str] = mapped_column(String(128), nullable=False)  # Hardware machine-id/hash
    public_key: Mapped[str] = mapped_column(Text, nullable=False)  # Device's Ed25519 public key (Base64)
    status: Mapped[DeviceStatus] = mapped_column(
        SQLEnum(DeviceStatus, native_enum=False), default=DeviceStatus.ACTIVE, nullable=False
    )
    last_sequence: Mapped[int] = mapped_column(default=0, nullable=False)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    menu_mode: Mapped[str | None] = mapped_column(String(16), nullable=True)  # Terminal override: LOCAL, CLOUD, or None (inherits location default)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    licenses: Mapped[list["DeviceLicense"]] = relationship(
        "DeviceLicense", back_populates="device", cascade="all, delete-orphan", lazy="selectin"
    )
    credentials: Mapped[list["DeviceCredential"]] = relationship(
        "DeviceCredential", back_populates="device", cascade="all, delete-orphan", lazy="selectin"
    )
    location: Mapped["app.domains.locations.models.Location | None"] = relationship(
        "Location", foreign_keys=[location_id], lazy="selectin"
    )


class DeviceCredential(Base):
    __tablename__ = "device_credentials"
    __table_args__ = (
        UniqueConstraint("device_id", "credential_version", name="uq_device_credential_version"),
        Index(
            "uq_device_active_credential",
            "device_id",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
        Index(
            "uq_active_credential_fingerprint",
            "key_fingerprint",
            unique=True,
            postgresql_where=text("status = 'ACTIVE'"),
            sqlite_where=text("status = 'ACTIVE'"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    public_key: Mapped[str] = mapped_column(Text, nullable=False)
    key_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    credential_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[CredentialStatus] = mapped_column(
        SQLEnum(CredentialStatus, native_enum=False), default=CredentialStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    device: Mapped["Device"] = relationship("Device", back_populates="credentials")


class DeviceChallenge(Base):
    __tablename__ = "device_challenges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    challenge_id: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    nonce: Mapped[str] = mapped_column(String(128), nullable=False)
    organization_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    actor_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    operation: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ROTATE | RECOVER
    expected_public_key_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    consumed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )


class TerminalSecurityAudit(Base):
    __tablename__ = "terminal_security_audits"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    terminal_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(64), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False)
    actor_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    previous_credential_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    new_credential_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    previous_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    installation_replacement_authorized: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
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
    installation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("application_installations.id", ondelete="SET NULL"), nullable=True, index=True
    )
    organization_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=True, index=True
    )
    current_subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="SET NULL"), nullable=True, index=True
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
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    device: Mapped["Device"] = relationship("Device", back_populates="licenses")
    application: Mapped["app.domains.applications.models.Application"] = relationship("Application")
    installation: Mapped["app.domains.applications.models.ApplicationInstallation | None"] = relationship("ApplicationInstallation")
    organization: Mapped["app.domains.organizations.models.Organization | None"] = relationship("Organization")
    current_subscription: Mapped["app.domains.subscriptions.models.Subscription | None"] = relationship("Subscription")
    allocations: Mapped[list["DeviceLicenseAllocation"]] = relationship(
        "DeviceLicenseAllocation", back_populates="device_license", cascade="all, delete-orphan", lazy="selectin"
    )


class DeviceLicenseAllocation(Base):
    __tablename__ = "device_license_allocations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    device_license_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("device_licenses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("subscriptions.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    allocation_status: Mapped[AllocationStatus] = mapped_column(
        SQLEnum(AllocationStatus, native_enum=False), default=AllocationStatus.ACTIVE, nullable=False, index=True
    )
    allocated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    release_reason: Mapped[AllocationReleaseReason | None] = mapped_column(
        SQLEnum(AllocationReleaseReason, native_enum=False), nullable=True
    )

    device_license: Mapped["DeviceLicense"] = relationship("DeviceLicense", back_populates="allocations")
    subscription: Mapped["app.domains.subscriptions.models.Subscription"] = relationship("Subscription")
