import json
import base64
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.subscriptions.models import Plan, Subscription, OwnerType, SubscriptionStatus
from app.domains.licensing.models import Device, DeviceLicense, DeviceStatus, LicenseStatus
from app.domains.applications.models import Application
from app.domains.organizations.models import OrganizationMember, OrganizationRole
from app.domains.licensing.schemas import (
    PlanCreateRequest,
    SubscriptionCreateRequest,
    DeviceRegisterRequest,
    LicenseIssueRequest,
    OfflineLicensePayload,
)
from app.core.security import _private_key, _public_key
from app.core.config import settings


class CommercialAndLicensingService:
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
        stmt = select(Device).where(Device.organization_id == org_id)
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

    # ------------------ Device & Offline Licensing ------------------
    @staticmethod
    async def register_device(
        db: AsyncSession, actor_user_id: uuid.UUID, req: DeviceRegisterRequest
    ) -> Device:
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

        # Check fingerprint uniqueness within org
        stmt_dev = select(Device).where(
            and_(
                Device.organization_id == req.organization_id,
                Device.fingerprint == req.fingerprint,
            )
        )
        res_dev = await db.execute(stmt_dev)
        if res_dev.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="This physical device fingerprint is already registered in this organization.",
            )

        device = Device(
            organization_id=req.organization_id,
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

        # Load Application
        stmt_app = select(Application).where(Application.id == req.application_id)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Active application not found.",
            )

        # Check active subscription and device seat quota
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
            .options(selectinload(Subscription.plan))
        )
        res_sub = await db.execute(stmt_sub)
        sub = res_sub.scalar_one_or_none()
        if not sub:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Organization does not hold an active subscription for {app.name}.",
            )

        # Verify device seats quota
        stmt_licensed = select(func.count(DeviceLicense.id)).where(
            and_(
                DeviceLicense.application_id == app.id,
                DeviceLicense.status == LicenseStatus.ACTIVE,
                DeviceLicense.device_id.in_(
                    select(Device.id).where(Device.organization_id == device.organization_id)
                ),
            )
        )
        res_licensed = await db.execute(stmt_licensed)
        current_active_licenses = res_licensed.scalar() or 0

        if current_active_licenses >= sub.plan.device_seats:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Device seat quota exceeded (Limit: {sub.plan.device_seats}, Current: {current_active_licenses}). Upgrade subscription to license more terminals.",
            )

        # Generate Ed25519-signed offline-verifiable license payload
        license_id = str(uuid.uuid4())
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings.OFFLINE_GRACE_PERIOD_DAYS)

        payload = OfflineLicensePayload(
            license_id=license_id,
            device_id=str(device.id),
            organization_id=str(device.organization_id),
            application_code=app.code,
            fingerprint=device.fingerprint,
            issued_at=int(now.timestamp()),
            expires_at=int(expires_at.timestamp()),
            grace_period_days=settings.OFFLINE_GRACE_PERIOD_DAYS,
        )

        payload_json = json.dumps(payload.model_dump(), sort_keys=True)
        # Sign payload bytes with VEX IAM's Ed25519 private key
        sig_bytes = _private_key.sign(payload_json.encode("utf-8"))
        signature_b64 = base64.b64encode(sig_bytes).decode("utf-8")

        device_license = DeviceLicense(
            id=uuid.UUID(license_id),
            device_id=device.id,
            application_id=app.id,
            signed_payload=payload_json,
            signature=signature_b64,
            status=LicenseStatus.ACTIVE,
            expires_at=expires_at,
            issued_at=now,
        )
        db.add(device_license)
        await db.commit()
        await db.refresh(device_license)
        return device_license

    @staticmethod
    def verify_offline_license(signed_payload_json: str, signature_b64: str) -> dict:
        """
        Local client verification algorithm executed by POS Terminal Agent without internet.
        """
        sig_bytes = base64.b64decode(signature_b64)
        # Verify signature using VEX IAM's Ed25519 Public Key
        _public_key.verify(sig_bytes, signed_payload_json.encode("utf-8"))

        data = json.loads(signed_payload_json)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > data["expires_at"]:
            raise ValueError("License has expired and offline grace period has lapsed. Please connect to internet to renew.")

        return data
