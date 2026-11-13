import uuid
from datetime import datetime, timezone
import enum
from typing import TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, UniqueConstraint, Table, Column
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

if TYPE_CHECKING:
    from app.domains.identity.models import User


class ApplicationType(str, enum.Enum):
    WEB = "WEB"
    LOCAL_HYBRID = "LOCAL_HYBRID"
    MOBILE = "MOBILE"
    SERVICE = "SERVICE"


class PlatformType(str, enum.Enum):
    WINDOWS_DESKTOP = "WINDOWS_DESKTOP"
    WEB = "WEB"
    MOBILE = "MOBILE"
    SERVICE = "SERVICE"


class ApplicationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    DEPRECATED = "DEPRECATED"


class ClientType(str, enum.Enum):
    DESKTOP = "DESKTOP"
    WEB = "WEB"
    MOBILE = "MOBILE"
    SERVICE = "SERVICE"


class ClientStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"


class InstallationStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    DECOMMISSIONED = "DECOMMISSIONED"


class AssignmentStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


# Association table between ApplicationRole and Permission
role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", UUID(as_uuid=True), ForeignKey("application_roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
)

# Association table between ApplicationAssignment and ApplicationRole
assignment_roles = Table(
    "assignment_roles",
    Base.metadata,
    Column("assignment_id", UUID(as_uuid=True), ForeignKey("application_assignments.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", UUID(as_uuid=True), ForeignKey("application_roles.id", ondelete="CASCADE"), primary_key=True),
)


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True, nullable=False)  # e.g., 'VEX-POS'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    type: Mapped[ApplicationType] = mapped_column(
        SQLEnum(ApplicationType, native_enum=False), default=ApplicationType.WEB, nullable=False
    )
    platform_type: Mapped[PlatformType] = mapped_column(
        SQLEnum(PlatformType, native_enum=False), default=PlatformType.WINDOWS_DESKTOP, nullable=False
    )
    status: Mapped[ApplicationStatus] = mapped_column(
        SQLEnum(ApplicationStatus, native_enum=False), default=ApplicationStatus.ACTIVE, nullable=False
    )
    current_version: Mapped[str] = mapped_column(String(30), default="1.0.0", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roles: Mapped[list["ApplicationRole"]] = relationship(
        "ApplicationRole", back_populates="application", cascade="all, delete-orphan"
    )
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", back_populates="application", cascade="all, delete-orphan"
    )
    clients: Mapped[list["ApplicationClient"]] = relationship(
        "ApplicationClient", back_populates="application", cascade="all, delete-orphan"
    )
    installations: Mapped[list["ApplicationInstallation"]] = relationship(
        "ApplicationInstallation", back_populates="application", cascade="all, delete-orphan"
    )


class ApplicationRole(Base):
    __tablename__ = "application_roles"
    __table_args__ = (
        UniqueConstraint("application_id", "code", name="uq_app_role_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(50), nullable=False)  # e.g., 'CASHIER'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_version: Mapped[int] = mapped_column(default=1, nullable=False)

    application: Mapped["Application"] = relationship("Application", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        "Permission", secondary=role_permissions, backref="roles", lazy="selectin"
    )


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (
        UniqueConstraint("application_id", "code", name="uq_app_permission_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    code: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g., 'pos:orders:create'
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)

    application: Mapped["Application"] = relationship("Application", back_populates="permissions")


class ApplicationAssignment(Base):
    """
    Grants a user within a specific organization access to a specific application,
    with one or more assigned application roles.
    """
    __tablename__ = "application_assignments"
    __table_args__ = (
        UniqueConstraint("organization_id", "user_id", "application_id", name="uq_org_user_app"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    organization_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    status: Mapped[AssignmentStatus] = mapped_column(
        SQLEnum(AssignmentStatus, native_enum=False), default=AssignmentStatus.ACTIVE, nullable=False
    )
    assignment_version: Mapped[int] = mapped_column(default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roles: Mapped[list["ApplicationRole"]] = relationship(
        "ApplicationRole", secondary=assignment_roles
    )
    application: Mapped["Application"] = relationship("Application")
    user: Mapped["User"] = relationship("User")


class ApplicationClient(Base):
    __tablename__ = "application_clients"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    client_code: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    client_name: Mapped[str] = mapped_column(String(150), nullable=False)
    client_type: Mapped[ClientType] = mapped_column(
        SQLEnum(ClientType, native_enum=False), default=ClientType.DESKTOP, nullable=False
    )
    status: Mapped[ClientStatus] = mapped_column(
        SQLEnum(ClientStatus, native_enum=False), default=ClientStatus.ACTIVE, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    application: Mapped["Application"] = relationship("Application", back_populates="clients")


class ApplicationInstallation(Base):
    __tablename__ = "application_installations"
    __table_args__ = (
        UniqueConstraint("application_id", "device_id", "installation_id", name="uq_app_device_installation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    application_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    device_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    installation_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(30), default="1.0.0", nullable=False)
    platform: Mapped[str] = mapped_column(String(30), default="WINDOWS", nullable=False)
    status: Mapped[InstallationStatus] = mapped_column(
        SQLEnum(InstallationStatus, native_enum=False), default=InstallationStatus.ACTIVE, nullable=False
    )
    registered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    application: Mapped["Application"] = relationship("Application", back_populates="installations")
    device: Mapped["app.domains.licensing.models.Device"] = relationship("Device", backref="installations")

