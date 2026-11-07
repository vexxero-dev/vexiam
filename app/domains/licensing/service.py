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
        existing_device = res_dev.scalar_one_or_none()
        if existing_device:
            # Idempotent re-registration / terminal key update
            existing_device.name = req.name
            existing_device.public_key = req.public_key
            existing_device.status = DeviceStatus.ACTIVE
            existing_device.last_heartbeat_at = datetime.now(timezone.utc)
            await db.commit()
            await db.refresh(existing_device)
            return existing_device

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
        stmt_lics = select(DeviceLicense).where(
            and_(
                DeviceLicense.device_id == device.id,
                DeviceLicense.status == LicenseStatus.ACTIVE,
            )
        )
        res_lics = await db.execute(stmt_lics)
        for lic in res_lics.scalars().all():
            lic.status = LicenseStatus.REVOKED

        await db.commit()
        await db.refresh(device)
        return device

    @staticmethod
    async def process_heartbeat(
        db: AsyncSession, device_id: uuid.UUID, fingerprint: str, app_id: uuid.UUID | None = None
    ) -> dict:
        stmt_dev = select(Device).where(Device.id == device_id)
        res_dev = await db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()

        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not registered.",
            )

        # Enforce fingerprint binding
        if device.fingerprint != fingerprint:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Hardware fingerprint mismatch.",
            )

        # If device is revoked
        if device.status == DeviceStatus.REVOKED:
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

        # If application specified, check and renew/extend license
        target_license = None
        if app_id:
            stmt_lic = select(DeviceLicense).where(
                and_(
                    DeviceLicense.device_id == device.id,
                    DeviceLicense.application_id == app_id,
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
            stmt_app = select(Application).where(Application.id == app_id)
            res_app = await db.execute(stmt_app)
            app = res_app.scalar_one_or_none()

            stmt_sub = (
                select(Subscription)
                .join(Plan, Subscription.plan_id == Plan.id)
                .where(
                    and_(
                        Subscription.organization_id == device.organization_id,
                        Plan.application_id == app_id,
                        Subscription.status == SubscriptionStatus.ACTIVE,
                    )
                )
            )
            res_sub = await db.execute(stmt_sub)
            sub = res_sub.scalar_one_or_none()

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
                application_code=app.code if app else "VEX-POS",
                fingerprint=device.fingerprint,
                issued_at=int(now.timestamp()),
                expires_at=int(new_expires_at.timestamp()),
                grace_period_days=settings.OFFLINE_GRACE_PERIOD_DAYS,
            )
            payload_json = json.dumps(payload.model_dump(), sort_keys=True)
            sig_bytes = _private_key.sign(payload_json.encode("utf-8"))
            signature_b64 = base64.b64encode(sig_bytes).decode("utf-8")

            target_license.signed_payload = payload_json
            target_license.signature = signature_b64
            target_license.expires_at = new_expires_at
            target_license.status = LicenseStatus.ACTIVE

            await db.commit()
            await db.refresh(target_license)

            return {
                "device_id": device.id,
                "device_status": device.status,
                "license_status": target_license.status,
                "is_valid": True,
                "message": "License renewed and active.",
                "license": target_license,
            }

        await db.commit()
        return {
            "device_id": device.id,
            "device_status": device.status,
            "license_status": LicenseStatus.ACTIVE,
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
        _public_key.verify(sig_bytes, signed_payload_json.encode("utf-8"))

        data = json.loads(signed_payload_json)
        now_ts = int(datetime.now(timezone.utc).timestamp())
        if now_ts > data["expires_at"]:
            raise ValueError("License has expired and offline grace period has lapsed. Please connect to internet to renew.")

        return data
