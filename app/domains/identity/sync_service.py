import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Optional
import rfc8785
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status

from app.core.security import sign_payload, DEFAULT_KEY_ID
from app.domains.identity.models import User, UserProfile
from app.domains.identity.sync_models import IdentitySyncEvent, SyncEventType
from app.domains.organizations.models import Organization, OrganizationMember, MembershipStatus
from app.domains.applications.models import (
    Application,
    ApplicationRole,
    Permission,
    ApplicationAssignment,
    AssignmentStatus,
    role_permissions,
    assignment_roles,
)
from app.domains.licensing.models import Device, DeviceStatus
from app.domains.identity.sync_schemas import (
    SignedPayloadEnvelope,
    SyncSnapshotData,
    SyncIncrementalData,
    SyncAcknowledgeResponse,
    OfflineLeasePayload,
)


class IdentitySyncService:

    @staticmethod
    async def record_sync_event(
        db: AsyncSession,
        event_type: SyncEventType,
        organization_id: uuid.UUID,
        entity_id: str,
        payload: dict[str, Any],
        application_id: Optional[uuid.UUID] = None,
        user_id: Optional[uuid.UUID] = None,
        version: int = 1,
    ) -> IdentitySyncEvent:
        """Appends a new identity sync event into the monotonically ordered sequence store."""
        # SQLite autoincrement for BigInteger: calculate max sequence + 1 if necessary
        seq_stmt = select(func.coalesce(func.max(IdentitySyncEvent.sequence), 0))
        res = await db.execute(seq_stmt)
        next_seq = (res.scalar() or 0) + 1

        event = IdentitySyncEvent(
            sequence=next_seq,
            event_type=event_type,
            organization_id=organization_id,
            application_id=application_id,
            user_id=user_id,
            entity_id=entity_id,
            version=version,
            payload=payload,
            created_at=datetime.now(timezone.utc),
        )
        db.add(event)
        await db.flush()
        return event

    @staticmethod
    async def verify_device_authorization(
        db: AsyncSession,
        organization_id: uuid.UUID,
        device_id: Optional[uuid.UUID] = None,
    ) -> Optional[Device]:
        if not device_id:
            return None
        stmt = select(Device).where(
            Device.id == device_id,
            Device.organization_id == organization_id,
        )
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device is not registered to this organization.",
            )
        if device.status != DeviceStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Device authorization is {device.status.value}.",
            )
        return device

    @classmethod
    def _create_signed_envelope(
        cls,
        audience: str,
        organization_id: uuid.UUID,
        application_id: uuid.UUID,
        device_id: Optional[uuid.UUID],
        sequence_start: int,
        sequence_end: int,
        data: dict[str, Any],
        lease_duration_minutes: int = 60,
    ) -> SignedPayloadEnvelope:
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=lease_duration_minutes)

        envelope_dict = {
            "issuer": "VEX_IAM",
            "audience": audience,
            "organization_id": str(organization_id),
            "application_id": str(application_id),
            "device_id": str(device_id) if device_id else None,
            "sequence_start": sequence_start,
            "sequence_end": sequence_end,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "payload_version": 1,
            "key_id": DEFAULT_KEY_ID,
            "data": data,
        }

        # Deterministic RFC 8785 JSON canonicalization before Ed25519 signing
        canonical_bytes = rfc8785.dumps(envelope_dict)
        signature = sign_payload(canonical_bytes)

        return SignedPayloadEnvelope(
            **envelope_dict,
            signature=signature,
        )

    @classmethod
    async def get_snapshot(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        application_id: uuid.UUID,
        device_id: Optional[uuid.UUID] = None,
    ) -> SignedPayloadEnvelope:
        """Produces a complete, authorized identity and role snapshot for an app in an org."""
        # 1. Verify app and device
        app_stmt = select(Application).where(Application.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found or inactive")

        org_stmt = select(Organization).where(Organization.id == organization_id)
        org_res = await db.execute(org_stmt)
        org = org_res.scalar_one_or_none()
        if not org:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

        await cls.verify_device_authorization(db, organization_id, device_id)

        # 2. Get all permissions for this application
        perm_stmt = select(Permission).where(Permission.application_id == application_id)
        perm_res = await db.execute(perm_stmt)
        perms = perm_res.scalars().all()
        perm_list = [
            {"id": str(p.id), "code": p.code, "name": p.name, "description": p.description}
            for p in perms
        ]

        # 3. Get all roles for this application with associated permissions
        role_stmt = select(ApplicationRole).where(ApplicationRole.application_id == application_id)
        role_res = await db.execute(role_stmt)
        roles = role_res.scalars().all()
        role_list = []
        for r in roles:
            subq = (
                select(Permission.code)
                .join(role_permissions, Permission.id == role_permissions.c.permission_id)
                .where(role_permissions.c.role_id == r.id)
            )
            r_perms = (await db.execute(subq)).scalars().all()
            role_list.append({
                "id": str(r.id),
                "code": r.code,
                "name": r.name,
                "role_version": r.role_version,
                "permissions": list(r_perms),
            })

        # 4. Get active application assignments for this organization and app
        assign_stmt = (
            select(ApplicationAssignment)
            .where(
                ApplicationAssignment.organization_id == organization_id,
                ApplicationAssignment.application_id == application_id,
            )
        )
        assign_res = await db.execute(assign_stmt)
        assignments = assign_res.scalars().all()

        assignment_list = []
        user_ids_set = set()
        for a in assignments:
            user_ids_set.add(a.user_id)
            # Find roles assigned to this assignment
            roles_subq = (
                select(ApplicationRole.code)
                .join(assignment_roles, ApplicationRole.id == assignment_roles.c.role_id)
                .where(assignment_roles.c.assignment_id == a.id)
            )
            a_roles = (await db.execute(roles_subq)).scalars().all()
            assignment_list.append({
                "id": str(a.id),
                "user_id": str(a.user_id),
                "status": a.status.value,
                "assignment_version": a.assignment_version,
                "roles": list(a_roles),
            })

        # 5. Fetch associated Users & Profiles
        users_list = []
        if user_ids_set:
            user_stmt = select(User).options(selectinload(User.profile)).where(User.id.in_(user_ids_set))
            user_res = await db.execute(user_stmt)
            users = user_res.scalars().all()
            for u in users:
                display_name = f"{u.profile.first_name} {u.profile.last_name}" if u.profile else u.email
                users_list.append({
                    "id": str(u.id),
                    "email": u.email,
                    "display_name": display_name,
                    "status": u.status.value,
                    "identity_version": u.identity_version,
                })

        # 6. Determine latest sequence
        latest_seq_stmt = (
            select(func.coalesce(func.max(IdentitySyncEvent.sequence), 0))
            .where(
                IdentitySyncEvent.organization_id == organization_id,
                (IdentitySyncEvent.application_id == application_id) | (IdentitySyncEvent.application_id.is_(None)),
            )
        )
        latest_seq = (await db.execute(latest_seq_stmt)).scalar() or 0

        snapshot_data = {
            "organization": {
                "id": str(org.id),
                "name": org.name,
                "status": org.status.value,
            },
            "users": users_list,
            "roles": role_list,
            "permissions": perm_list,
            "assignments": assignment_list,
            "latest_sequence": latest_seq,
        }

        return cls._create_signed_envelope(
            audience=app.code,
            organization_id=organization_id,
            application_id=application_id,
            device_id=device_id,
            sequence_start=1,
            sequence_end=latest_seq,
            data=snapshot_data,
        )

    @classmethod
    async def get_changes(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        application_id: uuid.UUID,
        after_sequence: int,
        device_id: Optional[uuid.UUID] = None,
        limit: int = 500,
    ) -> SignedPayloadEnvelope:
        """Returns signed incremental identity changes since after_sequence."""
        app_stmt = select(Application).where(Application.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found or inactive")

        await cls.verify_device_authorization(db, organization_id, device_id)

        # Query events matching organization and (app or global org event) after after_sequence
        query = (
            select(IdentitySyncEvent)
            .where(
                IdentitySyncEvent.organization_id == organization_id,
                (IdentitySyncEvent.application_id == application_id) | (IdentitySyncEvent.application_id.is_(None)),
                IdentitySyncEvent.sequence > after_sequence,
            )
            .order_by(IdentitySyncEvent.sequence.asc())
            .limit(limit)
        )
        events_res = await db.execute(query)
        events = events_res.scalars().all()

        changes = []
        seq_end = after_sequence
        for e in events:
            changes.append({
                "sequence": e.sequence,
                "event_type": e.event_type.value,
                "entity_id": e.entity_id,
                "version": e.version,
                "payload": e.payload,
                "created_at": e.created_at.isoformat(),
            })
            if e.sequence > seq_end:
                seq_end = e.sequence

        data = {
            "changes": changes,
            "latest_sequence": seq_end,
        }

        return cls._create_signed_envelope(
            audience=app.code,
            organization_id=organization_id,
            application_id=application_id,
            device_id=device_id,
            sequence_start=after_sequence + 1 if changes else after_sequence,
            sequence_end=seq_end,
            data=data,
        )

    @classmethod
    async def acknowledge_sync(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        application_id: uuid.UUID,
        acknowledged_sequence: int,
        device_id: Optional[uuid.UUID] = None,
    ) -> SyncAcknowledgeResponse:
        """Records terminal sync acknowledgment and updates device last_sequence."""
        if device_id:
            device = await cls.verify_device_authorization(db, organization_id, device_id)
            if device and acknowledged_sequence > device.last_sequence:
                device.last_sequence = acknowledged_sequence
                device.last_heartbeat_at = datetime.now(timezone.utc)
                await db.commit()

        return SyncAcknowledgeResponse(
            organization_id=organization_id,
            application_id=application_id,
            last_acknowledged_sequence=acknowledged_sequence,
            acknowledged_at=datetime.now(timezone.utc),
        )

    @classmethod
    async def issue_offline_lease(
        cls,
        db: AsyncSession,
        organization_id: uuid.UUID,
        application_id: uuid.UUID,
        device_id: uuid.UUID,
        lease_duration_hours: int = 72,
    ) -> OfflineLeasePayload:
        """Issues an Ed25519-signed offline authorization lease to an authorized device."""
        app_stmt = select(Application).where(Application.id == application_id)
        app_res = await db.execute(app_stmt)
        app = app_res.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found or inactive")

        device = await cls.verify_device_authorization(db, organization_id, device_id)

        # Get latest authorization sequence/version for this organization & application
        seq_stmt = (
            select(func.coalesce(func.max(IdentitySyncEvent.sequence), 1))
            .where(
                IdentitySyncEvent.organization_id == organization_id,
                (IdentitySyncEvent.application_id == application_id) | (IdentitySyncEvent.application_id.is_(None)),
            )
        )
        auth_version = (await db.execute(seq_stmt)).scalar() or 1

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=lease_duration_hours)

        lease_dict = {
            "issuer": "VEX_IAM",
            "audience": app.code,
            "organization_id": str(organization_id),
            "device_id": str(device_id),
            "application_id": str(application_id),
            "authorization_version": auth_version,
            "issued_at": now.isoformat(),
            "expires_at": expires_at.isoformat(),
            "offline_until": expires_at.isoformat(),
            "key_id": DEFAULT_KEY_ID,
        }

        # RFC 8785 canonical representation + Ed25519 signature
        canonical_bytes = rfc8785.dumps(lease_dict)
        signature = sign_payload(canonical_bytes)

        return OfflineLeasePayload(
            **lease_dict,
            signature=signature,
        )
