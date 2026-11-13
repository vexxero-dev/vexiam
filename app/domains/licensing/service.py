import json
import base64
import uuid
import secrets
import rfc8785
from datetime import datetime, timezone, timedelta
from cryptography.hazmat.primitives.asymmetric import ed25519
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.subscriptions.models import Plan, Subscription, OwnerType, SubscriptionStatus
from app.domains.licensing.models import (
    Device,
    DeviceLicense,
    DeviceLicenseAllocation,
    DeviceChallenge,
    DeviceStatus,
    LicenseStatus,
    AllocationStatus,
    AllocationReleaseReason,
)
from app.domains.applications.models import Application
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.locations.models import Location, LocationStatus, LocationApplication, LocationApplicationStatus
from app.domains.identity.sync_service import IdentitySyncService
from app.domains.identity.sync_models import SyncEventType
from app.domains.licensing.schemas import (
    PlanCreateRequest,
    SubscriptionCreateRequest,
    DeviceRegisterRequest,
    DeviceReassignRequest,
    DeviceReassignResponse,
    LicenseIssueRequest,
    OfflineLicensePayload,
    DeviceChallengeResponse,
    MachineHeartbeatRequest,
    EntitlementsResponse,
    LicensingAdminDashboardResponse,
    SubscriptionAllocationProvenance,
    DeviceLicenseAllocationSummary,
)
from app.core.security import _private_key, _public_key
from app.core.config import settings


class CommercialAndLicensingService:
    @staticmethod
    async def get_entitlements(
        db: AsyncSession,
        actor_user_id: uuid.UUID,
        organization_id: uuid.UUID,
        location_id: uuid.UUID | None = None,
        application_code: str = "VEX-POS",
    ) -> EntitlementsResponse:
        """
        Authoritative PDP inspection endpoint for POS terminal capacity & active feature entitlements.
        """
        # 1. Verify caller has membership in the organization
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of this organization.",
            )

        # 2. Resolve application
        code_norm = application_code.strip().upper().replace("VEXXERO", "VEX")
        stmt_app = select(Application).where(func.upper(Application.code) == code_norm)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application '{application_code}' not found or inactive.",
            )

        # 3. Optional location verification
        if location_id:
            stmt_loc = select(Location).where(
                and_(
                    Location.id == location_id,
                    Location.organization_id == organization_id,
                )
            )
            res_loc = await db.execute(stmt_loc)
            loc = res_loc.scalar_one_or_none()
            if not loc:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Specified location not found in this organization.",
                )
            if loc.status != LocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Location '{loc.name}' is inactive or archived.",
                )

        # 4. Query active subscriptions
        now_utc = datetime.now(timezone.utc)
        stmt_subs = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == organization_id,
                    Plan.application_id == app.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.created_at.desc())
        )
        res_subs = await db.execute(stmt_subs)
        subs = res_subs.scalars().all()

        valid_subs = []
        for s in subs:
            if s.expires_at is None:
                valid_subs.append(s)
            else:
                exp = s.expires_at if s.expires_at.tzinfo is not None else s.expires_at.replace(tzinfo=timezone.utc)
                if exp > now_utc:
                    valid_subs.append(s)

        if not valid_subs:
            return EntitlementsResponse(
                application_code=app.code,
                organization_id=organization_id,
                location_id=location_id,
                plan_tier="NO_ACTIVE_SUBSCRIPTION",
                max_terminals=0,
                active_terminals=0,
                available_terminals=0,
                entitlements=[],
                status="INACTIVE",
                message="Organization does not hold an active subscription for this application.",
            )

        total_device_seats = sum(s.plan.device_seats for s in valid_subs if s.plan)
        primary_plan = valid_subs[0].plan.name if valid_subs[0].plan else "Standard Subscription"

        # 5. Calculate currently active terminal licenses for this application in this org
        stmt_active_licenses = select(func.count(DeviceLicense.id)).where(
            and_(
                DeviceLicense.application_id == app.id,
                DeviceLicense.status == LicenseStatus.ACTIVE,
                DeviceLicense.device_id.in_(
                    select(Device.id).where(Device.organization_id == organization_id)
                ),
            )
        )
        res_active_licenses = await db.execute(stmt_active_licenses)
        active_terminals = res_active_licenses.scalar() or 0
        available_terminals = max(0, total_device_seats - active_terminals)

        # Canonical POS feature entitlements
        pos_features = ["pos.core", "pos.offline", "pos.multi_terminal", "pos.sync", "pos.reporting"]

        return EntitlementsResponse(
            application_code=app.code,
            organization_id=organization_id,
            location_id=location_id,
            plan_tier=primary_plan,
            max_terminals=total_device_seats,
            active_terminals=active_terminals,
            available_terminals=available_terminals,
            entitlements=pos_features,
            status="ACTIVE",
            message="Entitlements verified successfully.",
        )

    # ------------------ Admin Dashboard & Provenance Inspection ------------------
    @staticmethod
    async def get_admin_licensing_dashboard(
        db: AsyncSession,
        organization_id: uuid.UUID,
        application_code: str = "VEX-POS",
    ) -> LicensingAdminDashboardResponse:
        """
        Exposes pooled capacity, subscription allocation provenance, and allocation history
        strictly for authorized IAM administrators (Specification Section 17).
        """
        stmt_org = select(Organization).where(Organization.id == organization_id)
        res_org = await db.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        code_norm = application_code.strip().upper().replace("VEXXERO", "VEX")
        stmt_app = select(Application).where(func.upper(Application.code) == code_norm)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Application '{application_code}' not found.",
            )

        # Query all active subscriptions for this application in the org
        stmt_subs = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == organization_id,
                    Plan.application_id == app.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.expires_at.asc().nulls_last(), Subscription.created_at.asc())
        )
        res_subs = await db.execute(stmt_subs)
        subs = res_subs.scalars().all()

        # Query allocations count per subscription
        sub_ids = [s.id for s in subs]
        stmt_alloc_counts = (
            select(DeviceLicenseAllocation.subscription_id, func.count(DeviceLicenseAllocation.id))
            .join(DeviceLicense, DeviceLicenseAllocation.device_license_id == DeviceLicense.id)
            .where(
                and_(
                    DeviceLicenseAllocation.allocation_status == AllocationStatus.ACTIVE,
                    DeviceLicense.status == LicenseStatus.ACTIVE,
                    DeviceLicenseAllocation.subscription_id.in_(sub_ids) if sub_ids else False,
                )
            )
            .group_by(DeviceLicenseAllocation.subscription_id)
        )
        res_alloc_counts = await db.execute(stmt_alloc_counts)
        alloc_counts_map = dict(res_alloc_counts.all()) if sub_ids else {}

        sub_provenance_list: list[SubscriptionAllocationProvenance] = []
        total_pooled = 0
        total_allocated = 0

        for s in subs:
            capacity = s.plan.device_seats if s.plan else 0
            allocated = alloc_counts_map.get(s.id, 0)
            total_pooled += capacity
            total_allocated += allocated
            sub_provenance_list.append(
                SubscriptionAllocationProvenance(
                    subscription_id=s.id,
                    plan_code=s.plan.code if s.plan else "UNKNOWN",
                    plan_name=s.plan.name if s.plan else "Standard Subscription",
                    allocated_seats=allocated,
                    total_seats=capacity,
                    expires_at=s.expires_at,
                    created_at=s.created_at,
                )
            )

        # Recent allocation ledger records for audit
        stmt_recent_alloc = (
            select(DeviceLicenseAllocation)
            .join(DeviceLicense, DeviceLicenseAllocation.device_license_id == DeviceLicense.id)
            .where(
                and_(
                    DeviceLicense.application_id == app.id,
                    DeviceLicense.organization_id == organization_id,
                )
            )
            .order_by(DeviceLicenseAllocation.allocated_at.desc())
            .limit(20)
        )
        res_recent_alloc = await db.execute(stmt_recent_alloc)
        recent_allocs = res_recent_alloc.scalars().all()

        available_seats = max(0, total_pooled - total_allocated)
        utilization = (total_allocated / total_pooled * 100.0) if total_pooled > 0 else 0.0

        return LicensingAdminDashboardResponse(
            organization_id=org.id,
            organization_name=org.name,
            application_code=app.code,
            total_pooled_capacity=total_pooled,
            active_device_licenses_count=total_allocated,
            available_seats=available_seats,
            utilization_percentage=round(utilization, 2),
            subscriptions=sub_provenance_list,
            recent_allocations=[
                DeviceLicenseAllocationSummary(
                    id=a.id,
                    device_license_id=a.device_license_id,
                    subscription_id=a.subscription_id,
                    allocation_status=a.allocation_status,
                    allocated_at=a.allocated_at,
                    released_at=a.released_at,
                    release_reason=a.release_reason,
                )
                for a in recent_allocs
            ],
        )

    # ------------------ Subscription Operations ------------------
    @staticmethod
    async def list_plans(db: AsyncSession) -> list[Plan]:
        stmt = select(Plan).options(selectinload(Plan.application))
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_organization_subscriptions(
        db: AsyncSession, org_id: uuid.UUID
    ) -> list[Subscription]:
        stmt = (
            select(Subscription)
            .options(selectinload(Subscription.plan).selectinload(Plan.application))
            .where(Subscription.organization_id == org_id)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def list_organization_devices(
        db: AsyncSession, org_id: uuid.UUID
    ) -> list[Device]:
        stmt = (
            select(Device)
            .options(selectinload(Device.licenses))
            .where(Device.organization_id == org_id)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_plan(db: AsyncSession, req: PlanCreateRequest) -> Plan:
        stmt = select(Plan).where(Plan.code == req.code.upper())
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Plan '{req.code.upper()}' already exists.",
            )

        plan = Plan(
            application_id=req.application_id,
            code=req.code.upper(),
            name=req.name,
            description=req.description,
            user_seats=req.user_seats,
            device_seats=req.device_seats,
        )
        db.add(plan)
        await db.commit()
        await db.refresh(plan)
        return plan

    @staticmethod
    async def create_subscription(
        db: AsyncSession, req: SubscriptionCreateRequest
    ) -> Subscription:
        if req.owner_type == OwnerType.ORGANIZATION and not req.organization_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="organization_id is required for ORGANIZATION subscriptions.",
            )
        if req.owner_type == OwnerType.INDIVIDUAL and not req.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id is required for INDIVIDUAL subscriptions.",
            )

        sub = Subscription(
            plan_id=req.plan_id,
            owner_type=req.owner_type,
            organization_id=req.organization_id if req.owner_type == OwnerType.ORGANIZATION else None,
            user_id=req.user_id if req.owner_type == OwnerType.INDIVIDUAL else None,
            status=SubscriptionStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(days=365),
        )
        db.add(sub)
        await db.commit()

        stmt = select(Subscription).options(selectinload(Subscription.plan)).where(Subscription.id == sub.id)
        res = await db.execute(stmt)
        return res.scalar_one()

    # ------------------ Proof of Possession Challenge ------------------
    @staticmethod
    async def create_device_challenge(db: AsyncSession) -> DeviceChallenge:
        challenge = DeviceChallenge(
            challenge_id=f"CHAL-{uuid.uuid4().hex}",
            nonce=secrets.token_hex(32),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
        )
        db.add(challenge)
        await db.commit()
        await db.refresh(challenge)
        return challenge

    # ------------------ Device & Offline Licensing ------------------
    @staticmethod
    async def register_device(
        db: AsyncSession, actor_user_id: uuid.UUID, req: DeviceRegisterRequest
    ) -> Device:
        # If challenge_id is provided, verify one-time proof of possession
        if req.challenge_id:
            if not req.signature_b64:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="signature_b64 is required when challenge_id is provided.",
                )
            stmt_chal = select(DeviceChallenge).where(DeviceChallenge.challenge_id == req.challenge_id)
            res_chal = await db.execute(stmt_chal)
            chal = res_chal.scalar_one_or_none()
            if not chal:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid challenge ID.")
            if chal.consumed_at is not None:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Challenge already consumed.")
            now_utc = datetime.now(timezone.utc)
            chal_expires = chal.expires_at
            if chal_expires.tzinfo is None:
                chal_expires = chal_expires.replace(tzinfo=timezone.utc)
            if now_utc > chal_expires:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Challenge expired.")

            # Verify terminal's Ed25519 signature over canonical challenge data
            try:
                raw_pub = base64.b64decode(req.public_key)
                term_pub = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
                challenge_data = {
                    "challenge_id": chal.challenge_id,
                    "device_id": req.fingerprint,
                    "nonce": chal.nonce,
                    "organization_id": str(req.organization_id),
                }
                canonical_bytes = rfc8785.dumps(challenge_data)
                sig_bytes = base64.b64decode(req.signature_b64)
                term_pub.verify(sig_bytes, canonical_bytes)
            except Exception as exc:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Proof of possession failed: {exc}")

            chal.consumed_at = now_utc

        # Check actor has admin rights in the organization
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == req.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can register devices.",
            )

        # If location_id is provided, validate target location with row-level locking
        if req.location_id:
            stmt_loc = (
                select(Location)
                .where(
                    and_(
                        Location.id == req.location_id,
                        Location.organization_id == req.organization_id,
                    )
                )
                .with_for_update()
            )
            res_loc = await db.execute(stmt_loc)
            target_loc = res_loc.scalar_one_or_none()
            if not target_loc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target location not found in this organization.",
                )
            if target_loc.status != LocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign device to an inactive or archived location.",
                )

        # Check fingerprint uniqueness within org
        stmt_dev = select(Device).where(
            and_(
                Device.organization_id == req.organization_id,
                Device.fingerprint == req.fingerprint,
            )
        )
        res_dev = await db.execute(stmt_dev)
        existing_device = res_dev.scalar_one_or_none()
        if existing_device:
            # Idempotent re-registration / terminal key update & authenticated sequence counter recovery
            existing_device.name = req.name
            existing_device.public_key = req.public_key
            existing_device.status = DeviceStatus.ACTIVE
            existing_device.last_sequence = 0
            existing_device.last_heartbeat_at = datetime.now(timezone.utc)
            if req.location_id is not None:
                existing_device.location_id = req.location_id
            await db.commit()
            await db.refresh(existing_device)
            return existing_device

        device = Device(
            organization_id=req.organization_id,
            location_id=req.location_id,
            name=req.name,
            fingerprint=req.fingerprint,
            public_key=req.public_key,
            status=DeviceStatus.ACTIVE,
            last_heartbeat_at=datetime.now(timezone.utc),
        )
        db.add(device)
        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def issue_device_license(
        db: AsyncSession, actor_user_id: uuid.UUID, req: LicenseIssueRequest
    ) -> DeviceLicense:
        # Load Device
        stmt_dev = select(Device).where(Device.id == req.device_id)
        res_dev = await db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        if not device or device.status != DeviceStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active device not found.",
            )

        # Verify actor permission
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == device.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can activate licenses.",
            )

        # Load Application - supports UUID or application code (e.g. 'VEX-POS' / 'vexxero-pos')
        app = None
        if req.application_id:
            try:
                parsed_uuid = uuid.UUID(str(req.application_id))
                stmt_app = select(Application).where(Application.id == parsed_uuid)
                res_app = await db.execute(stmt_app)
                app = res_app.scalar_one_or_none()
            except ValueError:
                code_norm = str(req.application_id).strip().upper().replace("VEXXERO", "VEX")
                stmt_app = select(Application).where(func.upper(Application.code) == code_norm)
                res_app = await db.execute(stmt_app)
                app = res_app.scalar_one_or_none()

        if not app:
            # Default fallback to POS application
            stmt_default = select(Application).where(Application.code == "VEX-POS")
            res_default = await db.execute(stmt_default)
            app = res_default.scalar_one_or_none()

        if not app or not app.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active application not found.",
            )

        # Verify client authorization if client_code is supplied
        if req.client_code:
            from app.domains.applications.models import ApplicationClient, ClientStatus
            stmt_client = select(ApplicationClient).where(
                and_(
                    ApplicationClient.application_id == app.id,
                    ApplicationClient.client_code == req.client_code.strip().upper(),
                    ApplicationClient.status == ClientStatus.ACTIVE,
                )
            )
            res_client = await db.execute(stmt_client)
            client_record = res_client.scalar_one_or_none()
            if not client_record:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Application client '{req.client_code}' is not authorized for application {app.code}.",
                )

        # Installation tracking: if installation_id supplied, resolve or create ApplicationInstallation
        installation_record = None
        if req.installation_id:
            from app.domains.applications.models import ApplicationInstallation, InstallationStatus
            stmt_inst = select(ApplicationInstallation).where(
                and_(
                    ApplicationInstallation.application_id == app.id,
                    ApplicationInstallation.device_id == device.id,
                    ApplicationInstallation.installation_id == req.installation_id,
                )
            )
            res_inst = await db.execute(stmt_inst)
            installation_record = res_inst.scalar_one_or_none()
            now_utc = datetime.now(timezone.utc)
            if not installation_record:
                installation_record = ApplicationInstallation(
                    application_id=app.id,
                    device_id=device.id,
                    installation_id=req.installation_id,
                    version="1.0.0",
                    platform="WINDOWS",
                    status=InstallationStatus.ACTIVE,
                    registered_at=now_utc,
                    last_seen_at=now_utc,
                )
                db.add(installation_record)
                await db.flush()
            else:
                installation_record.last_seen_at = now_utc

        # Check active subscriptions and calculate total device seat quota across plans
        # Concurrency protection: lock rows for update and sort by earliest expiration first (FIFO)
        stmt_subs = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == device.organization_id,
                    Plan.application_id == app.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            .options(selectinload(Subscription.plan))
            .order_by(Subscription.expires_at.asc().nulls_last(), Subscription.created_at.asc())
            .with_for_update()
        )
        res_subs = await db.execute(stmt_subs)
        active_subs = res_subs.scalars().all()
        if not active_subs:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Organization does not hold an active subscription for {app.name}.",
            )

        # Aggregate total terminal quota across all active subscriptions for this application
        total_device_seats = sum(s.plan.device_seats for s in active_subs if s.plan)

        # Check if device already holds an active license for this application (Idempotent activation)
        stmt_existing_lic = (
            select(DeviceLicense)
            .where(
                and_(
                    DeviceLicense.device_id == device.id,
                    DeviceLicense.application_id == app.id,
                    DeviceLicense.status == LicenseStatus.ACTIVE,
                )
            )
            .options(selectinload(DeviceLicense.allocations))
        )
        res_existing_lic = await db.execute(stmt_existing_lic)
        existing_license = res_existing_lic.scalar_one_or_none()

        # Query existing active allocations count grouped by subscription_id to accurately calculate remaining seats
        stmt_alloc_counts = (
            select(DeviceLicenseAllocation.subscription_id, func.count(DeviceLicenseAllocation.id))
            .join(DeviceLicense, DeviceLicenseAllocation.device_license_id == DeviceLicense.id)
            .where(
                and_(
                    DeviceLicenseAllocation.allocation_status == AllocationStatus.ACTIVE,
                    DeviceLicense.status == LicenseStatus.ACTIVE,
                    DeviceLicenseAllocation.subscription_id.in_([s.id for s in active_subs]),
                )
            )
            .group_by(DeviceLicenseAllocation.subscription_id)
        )
        res_alloc_counts = await db.execute(stmt_alloc_counts)
        allocation_map = dict(res_alloc_counts.all())

        assigned_subscription = None

        if existing_license:
            # Check if current subscription is still active and valid
            curr_sub = next((s for s in active_subs if s.id == existing_license.current_subscription_id), None)
            if curr_sub:
                assigned_subscription = curr_sub
            else:
                # Need to reallocate to an active subscription with available capacity
                for sub in active_subs:
                    used = allocation_map.get(sub.id, 0)
                    capacity = sub.plan.device_seats if sub.plan else 0
                    if used < capacity:
                        assigned_subscription = sub
                        break
                if not assigned_subscription:
                    # Keep under current if within total pool or fallback to primary
                    assigned_subscription = active_subs[0]
        else:
            # New activation: Total seat quota check
            current_active_licenses = sum(allocation_map.values())
            # Fallback if unallocated legacy licenses exist
            stmt_unallocated = select(func.count(DeviceLicense.id)).where(
                and_(
                    DeviceLicense.application_id == app.id,
                    DeviceLicense.status == LicenseStatus.ACTIVE,
                    DeviceLicense.device_id.in_(
                        select(Device.id).where(Device.organization_id == device.organization_id)
                    ),
                )
            )
            res_unallocated = await db.execute(stmt_unallocated)
            total_active_device_licenses = res_unallocated.scalar() or 0

            if total_active_device_licenses >= total_device_seats:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Device seat quota exceeded (Limit: {total_device_seats}, Current: {total_active_device_licenses}). Upgrade subscription to license more terminals.",
                )

            # Atomic FIFO selection: choose earliest-expiring subscription with available capacity
            for sub in active_subs:
                used = allocation_map.get(sub.id, 0)
                capacity = sub.plan.device_seats if sub.plan else 0
                if used < capacity:
                    assigned_subscription = sub
                    break

            if not assigned_subscription:
                assigned_subscription = active_subs[0]

        # Fetch organization for metadata
        stmt_org = select(Organization).where(Organization.id == device.organization_id)
        res_org = await db.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        org_name = org.name if org else None

        # Generate Ed25519-signed offline-verifiable license payload
        license_id = str(existing_license.id) if existing_license else str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.OFFLINE_GRACE_PERIOD_DAYS)

        payload = OfflineLicensePayload(
            license_id=license_id,
            device_id=str(device.id),
            installation_id=req.installation_id,
            organization_id=str(device.organization_id),
            organization_name=org_name,
            application_code=app.code,
            product_name=app.name,
            fingerprint=device.fingerprint,
            issued_at=int(now.timestamp()),
            expires_at=int(expires_at.timestamp()),
            offline_grace_until=int(expires_at.timestamp()),
            grace_period_days=settings.OFFLINE_GRACE_PERIOD_DAYS,
        )

        payload_dict = payload.model_dump()
        payload_bytes = rfc8785.dumps(payload_dict)
        payload_json = payload_bytes.decode("utf-8")
        # Sign canonical bytes with VEX IAM's Ed25519 private key
        sig_bytes = _private_key.sign(payload_bytes)
        signature_b64 = base64.b64encode(sig_bytes).decode("utf-8")

        if existing_license:
            existing_license.signed_payload = payload_json
            existing_license.signature = signature_b64
            existing_license.expires_at = expires_at
            existing_license.issued_at = now
            if installation_record:
                existing_license.installation_id = installation_record.id
            existing_license.organization_id = device.organization_id

            # If subscription assignment changed, release old and create new allocation
            if existing_license.current_subscription_id != assigned_subscription.id:
                for alloc in existing_license.allocations:
                    if alloc.allocation_status == AllocationStatus.ACTIVE:
                        alloc.allocation_status = AllocationStatus.RELEASED
                        alloc.released_at = now
                        alloc.release_reason = AllocationReleaseReason.QUOTA_REBALANCED

                new_alloc = DeviceLicenseAllocation(
                    device_license_id=existing_license.id,
                    subscription_id=assigned_subscription.id,
                    allocation_status=AllocationStatus.ACTIVE,
                    allocated_at=now,
                )
                db.add(new_alloc)
                existing_license.current_subscription_id = assigned_subscription.id
            device_license = existing_license
        else:
            device_license = DeviceLicense(
                id=uuid.UUID(license_id),
                device_id=device.id,
                application_id=app.id,
                installation_id=installation_record.id if installation_record else None,
                organization_id=device.organization_id,
                current_subscription_id=assigned_subscription.id,
                signed_payload=payload_json,
                signature=signature_b64,
                status=LicenseStatus.ACTIVE,
                expires_at=expires_at,
                issued_at=now,
            )
            db.add(device_license)
            await db.flush()

            # Record allocation history ledger entry
            allocation = DeviceLicenseAllocation(
                device_license_id=device_license.id,
                subscription_id=assigned_subscription.id,
                allocation_status=AllocationStatus.ACTIVE,
                allocated_at=now,
            )
            db.add(allocation)

        await db.commit()
        await db.refresh(device_license)

        # Attach transient metadata for LicenseResponse
        device_license.organization_id = device.organization_id
        device_license.organization_name = org_name
        device_license.product_name = app.name
        device_license.subscription_id = assigned_subscription.id

        return device_license

    @staticmethod
    async def revoke_device(
        db: AsyncSession, actor_user_id: uuid.UUID, device_id: uuid.UUID
    ) -> Device:
        stmt = select(Device).where(Device.id == device_id)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found.",
            )

        # Check actor permissions in org
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == device.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can revoke devices.",
            )

        # Mark device revoked
        device.status = DeviceStatus.REVOKED

        # Mark all active device licenses revoked to release seat quota
        stmt_lics = (
            select(DeviceLicense)
            .options(selectinload(DeviceLicense.allocations))
            .where(
                and_(
                    DeviceLicense.device_id == device.id,
                    DeviceLicense.status == LicenseStatus.ACTIVE,
                )
            )
        )
        res_lics = await db.execute(stmt_lics)
        now_revoke = datetime.now(timezone.utc)
        for lic in res_lics.scalars().all():
            lic.status = LicenseStatus.REVOKED
            for alloc in lic.allocations:
                if alloc.allocation_status == AllocationStatus.ACTIVE:
                    alloc.allocation_status = AllocationStatus.RELEASED
                    alloc.released_at = now_revoke
                    alloc.release_reason = AllocationReleaseReason.DEVICE_REVOKED

        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def delete_device(
        db: AsyncSession, actor_user_id: uuid.UUID, device_id: uuid.UUID
    ) -> None:
        stmt = select(Device).where(Device.id == device_id)
        res = await db.execute(stmt)
        device = res.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found.",
            )

        # Check actor permissions in org
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == device.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can delete devices.",
            )

        await db.delete(device)
        await db.commit()

    @staticmethod
    async def reassign_device(
        db: AsyncSession, actor_user_id: uuid.UUID, device_id: uuid.UUID, req: DeviceReassignRequest
    ) -> DeviceReassignResponse:
        # 1. Acquire row-level lock on the device record to serialize with concurrent heartbeats
        stmt_dev = (
            select(Device)
            .options(selectinload(Device.licenses))
            .where(Device.id == device_id)
            .with_for_update()
        )
        res_dev = await db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found.",
            )

        # 2. Check actor has admin permissions in the device's organization
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == device.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can reassign devices.",
            )

        # 3. Idempotency check: if device is already at target location, return immediately as a no-op
        if device.location_id == req.target_location_id:
            return DeviceReassignResponse(
                device_id=device.id,
                organization_id=device.organization_id,
                old_location_id=device.location_id,
                new_location_id=device.location_id,
                revoked_licenses_count=0,
                reassigned_at=datetime.now(timezone.utc),
                message="Device is already assigned to target location. No changes made.",
            )

        # 4. Deterministic location locking: lock source and target locations in ascending UUID order
        loc_ids_to_lock = []
        if device.location_id:
            loc_ids_to_lock.append(device.location_id)
        if req.target_location_id and req.target_location_id != device.location_id:
            loc_ids_to_lock.append(req.target_location_id)

        loc_ids_to_lock.sort()

        locked_locations = {}
        if loc_ids_to_lock:
            stmt_locks = (
                select(Location)
                .where(
                    and_(
                        Location.id.in_(loc_ids_to_lock),
                        Location.organization_id == device.organization_id,
                    )
                )
                .order_by(Location.id.asc())
                .with_for_update()
            )
            res_locks = await db.execute(stmt_locks)
            for loc in res_locks.scalars().all():
                locked_locations[loc.id] = loc

        # Post-lock validation: Target location must exist, belong to org, and be ACTIVE
        if req.target_location_id:
            target_loc = locked_locations.get(req.target_location_id)
            if not target_loc:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Target location not found in this organization.",
                )
            if target_loc.status != LocationStatus.ACTIVE:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot assign device to an inactive or archived location.",
                )

        # 5. Authoritative Active-Only Application Resolution
        # Find applications currently operated by this device (active, non-expired licenses)
        now_utc = datetime.now(timezone.utc)
        active_app_ids = set()
        for lic in device.licenses:
            if lic.status == LicenseStatus.ACTIVE:
                exp = lic.expires_at if lic.expires_at.tzinfo is not None else lic.expires_at.replace(tzinfo=timezone.utc)
                if exp > now_utc:
                    active_app_ids.add(lic.application_id)

        # If moving to a location, verify target location has ACTIVE location_applications for each active app
        if req.target_location_id and active_app_ids:
            stmt_enabled = select(LocationApplication.application_id).where(
                and_(
                    LocationApplication.location_id == req.target_location_id,
                    LocationApplication.application_id.in_(active_app_ids),
                    LocationApplication.status == LocationApplicationStatus.ACTIVE,
                )
            )
            res_enabled = await db.execute(stmt_enabled)
            enabled_apps = set(res_enabled.scalars().all())

            missing_apps = active_app_ids - enabled_apps
            if missing_apps:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Target location lacks active enablement for application(s) currently operated by this device.",
                )

        # 6. Atomic Mutation: Update location_id and revoke active licenses
        old_location_id = device.location_id
        device.location_id = req.target_location_id

        revoked_count = 0
        now_reassign = datetime.now(timezone.utc)
        for lic in device.licenses:
            if lic.status == LicenseStatus.ACTIVE:
                lic.status = LicenseStatus.REVOKED
                revoked_count += 1
                for alloc in lic.allocations:
                    if alloc.allocation_status == AllocationStatus.ACTIVE:
                        alloc.allocation_status = AllocationStatus.RELEASED
                        alloc.released_at = now_reassign
                        alloc.release_reason = AllocationReleaseReason.MANUAL_REASSIGNMENT

        now = datetime.now(timezone.utc)
        await db.flush()

        # 7. Transactional Outbox: Record sync event in the same transaction
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.DEVICE_LOCATION_REASSIGNED,
            organization_id=device.organization_id,
            application_id=None,
            user_id=actor_user_id,
            entity_id=str(device.id),
            version=1,
            payload={
                "device_id": str(device.id),
                "old_location_id": str(old_location_id) if old_location_id else None,
                "new_location_id": str(req.target_location_id) if req.target_location_id else None,
                "fingerprint": device.fingerprint,
                "revoked_licenses_count": revoked_count,
            },
        )

        await db.commit()
        await db.refresh(device)

        return DeviceReassignResponse(
            device_id=device.id,
            organization_id=device.organization_id,
            old_location_id=old_location_id,
            new_location_id=req.target_location_id,
            revoked_licenses_count=revoked_count,
            reassigned_at=now,
            message="Device successfully reassigned. Active licenses revoked; client must refresh license.",
        )

    @staticmethod
    async def process_heartbeat(
        db: AsyncSession, device_id: uuid.UUID, req: MachineHeartbeatRequest
    ) -> dict:
        # Acquire row-level lock on device to serialize with concurrent reassignment
        stmt_dev = select(Device).where(Device.id == device_id).with_for_update()
        res_dev = await db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not registered.",
            )

        payload_dict = req.canonical_request.model_dump()

        # 1. Cryptographic Authentication: Verify terminal's Ed25519 signature over canonical request
        try:
            raw_pub = base64.b64decode(device.public_key)
            term_pub = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
            canonical_bytes = rfc8785.dumps(payload_dict)
            sig_bytes = base64.b64decode(req.signature_b64)
            term_pub.verify(sig_bytes, canonical_bytes)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Cryptographic heartbeat verification failed: {exc}",
            )

        # 2. Hardware and Identifier Binding
        if device.fingerprint != payload_dict.get("fingerprint"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Hardware fingerprint mismatch.",
            )
        if str(device.id) != payload_dict.get("device_id"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Device ID mismatch in canonical request.",
            )

        # 3. Timestamp Freshness & Clock Skew Validation (+/- 300 seconds)
        req_ts = payload_dict.get("timestamp", 0)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if abs(now_ts - req_ts) > 300:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Heartbeat timestamp skew exceeds allowed threshold (+/- 300s). Server UTC: {now_ts}, Received: {req_ts}",
            )

        # 4. Sequence-based Replay Attack Protection
        seq = payload_dict.get("sequence", 0)
        if seq <= device.last_sequence:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Replay attack detected: sequence {seq} must be greater than last sequence {device.last_sequence}.",
            )
        device.last_sequence = seq

        # If device is revoked
        if device.status == DeviceStatus.REVOKED:
            await db.commit()
            return {
                "device_id": device.id,
                "device_status": DeviceStatus.REVOKED,
                "license_status": LicenseStatus.REVOKED,
                "is_valid": False,
                "message": "Device registration has been revoked by an administrator.",
                "license": None,
            }

        # Update last heartbeat timestamp
        now = datetime.now(timezone.utc)
        device.last_heartbeat_at = now

        # Fetch organization info
        stmt_org = select(Organization).where(Organization.id == device.organization_id)
        res_org = await db.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        org_name = org.name if org else None

        # Resolve application if passed as code or UUID
        app_id = payload_dict.get("application_id")
        app = None
        if app_id:
            try:
                parsed_uuid = uuid.UUID(str(app_id))
                stmt_app = select(Application).where(Application.id == parsed_uuid)
                res_app = await db.execute(stmt_app)
                app = res_app.scalar_one_or_none()
            except ValueError:
                code_norm = str(app_id).strip().upper().replace("VEXXERO", "VEX")
                stmt_app = select(Application).where(func.upper(Application.code) == code_norm)
                res_app = await db.execute(stmt_app)
                app = res_app.scalar_one_or_none()

        if not app:
            stmt_default = select(Application).where(Application.code == "VEX-POS")
            res_default = await db.execute(stmt_default)
            app = res_default.scalar_one_or_none()

        # Re-validate location status and application enablement if device is location-bound
        if device.location_id:
            stmt_loc = select(Location).where(
                and_(
                    Location.id == device.location_id,
                    Location.organization_id == device.organization_id,
                )
            ).with_for_update()
            res_loc = await db.execute(stmt_loc)
            loc = res_loc.scalar_one_or_none()
            if not loc or loc.status != LocationStatus.ACTIVE:
                await db.commit()
                return {
                    "device_id": device.id,
                    "device_status": device.status,
                    "license_status": LicenseStatus.REVOKED,
                    "is_valid": False,
                    "message": "Assigned location is inactive or archived.",
                    "license": None,
                }

            if app:
                stmt_loc_app = select(LocationApplication).where(
                    and_(
                        LocationApplication.location_id == device.location_id,
                        LocationApplication.application_id == app.id,
                        LocationApplication.status == LocationApplicationStatus.ACTIVE,
                    )
                )
                res_loc_app = await db.execute(stmt_loc_app)
                if not res_loc_app.scalar_one_or_none():
                    await db.commit()
                    return {
                        "device_id": device.id,
                        "device_status": device.status,
                        "license_status": LicenseStatus.REVOKED,
                        "is_valid": False,
                        "message": f"Application '{app.code}' is not active at assigned location.",
                        "license": None,
                    }

        # Check and renew/extend license
        target_license = None
        if app:
            stmt_lic = select(DeviceLicense).where(
                and_(
                    DeviceLicense.device_id == device.id,
                    DeviceLicense.application_id == app.id,
                )
            ).order_by(DeviceLicense.issued_at.desc())
            res_lic = await db.execute(stmt_lic)
            target_license = res_lic.scalars().first()

        if target_license:
            if target_license.status == LicenseStatus.REVOKED:
                await db.commit()
                return {
                    "device_id": device.id,
                    "device_status": device.status,
                    "license_status": LicenseStatus.REVOKED,
                    "is_valid": False,
                    "message": "Application license has been revoked.",
                    "license": None,
                }

            # Check organization subscription
            stmt_sub = (
                select(Subscription)
                .join(Plan, Subscription.plan_id == Plan.id)
                .where(
                    and_(
                        Subscription.organization_id == device.organization_id,
                        Plan.application_id == app.id,
                        Subscription.status == SubscriptionStatus.ACTIVE,
                    )
                )
            )
            res_sub = await db.execute(stmt_sub)
            sub = res_sub.scalars().first()

            if not sub:
                target_license.status = LicenseStatus.EXPIRED
                await db.commit()
                return {
                    "device_id": device.id,
                    "device_status": device.status,
                    "license_status": LicenseStatus.EXPIRED,
                    "is_valid": False,
                    "message": "Organization subscription is expired or inactive.",
                    "license": None,
                }

            # Automatically renew / extend signed offline license window
            new_expires_at = now + timedelta(days=settings.OFFLINE_GRACE_PERIOD_DAYS)
            payload = OfflineLicensePayload(
                license_id=str(target_license.id),
                device_id=str(device.id),
                organization_id=str(device.organization_id),
                organization_name=org_name,
                application_code=app.code if app else "VEX-POS",
                product_name=app.name if app else None,
                fingerprint=device.fingerprint,
                issued_at=int(now.timestamp()),
                expires_at=int(new_expires_at.timestamp()),
                grace_period_days=settings.OFFLINE_GRACE_PERIOD_DAYS,
            )
            payload_dict = payload.model_dump()
            payload_bytes = rfc8785.dumps(payload_dict)
            payload_json = payload_bytes.decode("utf-8")
            sig_bytes = _private_key.sign(payload_bytes)
            signature_b64 = base64.b64encode(sig_bytes).decode("utf-8")

            target_license.signed_payload = payload_json
            target_license.signature = signature_b64
            target_license.expires_at = new_expires_at
            target_license.status = LicenseStatus.ACTIVE

            await db.commit()
            await db.refresh(target_license)

            # Attach transient metadata for nested LicenseResponse
            target_license.organization_id = device.organization_id
            target_license.organization_name = org_name
            target_license.product_name = app.name if app else None

            return {
                "device_id": device.id,
                "device_status": device.status,
                "license_status": target_license.status,
                "organization_id": device.organization_id,
                "organization_name": org_name,
                "product_name": app.name if app else None,
                "is_valid": True,
                "message": "License renewed and active.",
                "license": target_license,
            }

        await db.commit()
        return {
            "device_id": device.id,
            "device_status": device.status,
            "license_status": LicenseStatus.ACTIVE,
            "organization_id": device.organization_id,
            "organization_name": org_name,
            "product_name": app.name if app else None,
            "is_valid": True,
            "message": "Heartbeat recorded.",
            "license": None,
        }

    @staticmethod
    def verify_offline_license(signed_payload_json: str, signature_b64: str) -> dict:
        """
        Local client verification algorithm executed by POS Terminal Agent without internet.
        """
        sig_bytes = base64.b64decode(signature_b64)
        # Verify signature using VEX IAM's Ed25519 Public Key
        try:
            _public_key.verify(sig_bytes, signed_payload_json.encode("utf-8"))
        except Exception:
            data_dict = json.loads(signed_payload_json)
            can_bytes = rfc8785.dumps(data_dict)
            _public_key.verify(sig_bytes, can_bytes)

        data = json.loads(signed_payload_json)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > data["expires_at"]:
            raise ValueError("License has expired and offline grace period has lapsed. Please connect to internet to renew.")

        return data
