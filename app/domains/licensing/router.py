import uuid
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_platform_admin, require_verified_user
from app.domains.identity.models import User
from app.domains.licensing.models import Device, DeviceStatus
from app.domains.licensing.schemas import (
    PlanCreateRequest,
    PlanResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    DeviceChallengeResponse,
    DeviceRegisterRequest,
    DeviceReassignRequest,
    DeviceReassignResponse,
    DeviceResponse,
    DeviceHeartbeatRequest,
    MachineHeartbeatRequest,
    DeviceHeartbeatResponse,
    DeviceInternalVerificationResponse,
    LicenseIssueRequest,
    LicenseResponse,
)
from app.domains.licensing.service import CommercialAndLicensingService

router = APIRouter(tags=["Subscriptions & Device Licensing"])


# Proof of Possession Device Challenge
@router.post(
    "/devices/challenge",
    response_model=DeviceChallengeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Issue a one-time cryptographic challenge nonce for proof-of-possession device registration",
)
async def create_device_challenge(
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.create_device_challenge(db)


# Plans & Subscriptions
@router.get(
    "/plans",
    response_model=list[PlanResponse],
    summary="List all available subscription plans",
)
async def list_plans(
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.list_plans(db)


@router.get(
    "/organizations/{org_id}/subscriptions",
    response_model=list[SubscriptionResponse],
    summary="List subscriptions for an organization",
)
async def list_org_subscriptions(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.list_organization_subscriptions(db, org_id)


@router.get(
    "/organizations/{org_id}/devices",
    response_model=list[DeviceResponse],
    summary="List registered devices for an organization",
)
async def list_org_devices(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.list_organization_devices(db, org_id)


@router.post(
    "/plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription tier plan",
)
async def create_plan(
    req: PlanCreateRequest,
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.create_plan(db, req)


@router.post(
    "/subscriptions",
    response_model=SubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create/Purchase an application subscription for an individual or organization",
)
async def create_subscription(
    req: SubscriptionCreateRequest,
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.create_subscription(db, req)


# Devices & Licensing
@router.post(
    "/devices/register",
    response_model=DeviceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a physical hardware device/terminal with its public key and fingerprint",
)
async def register_device(
    req: DeviceRegisterRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.register_device(
        db, current_user.id, req
    )


@router.post(
    "/licenses/activate",
    response_model=LicenseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Activate and issue an Ed25519-signed offline device license for an application",
)
async def activate_device_license(
    req: LicenseIssueRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.issue_device_license(
        db, current_user.id, req
    )


@router.post(
    "/devices/{device_id}/reassign",
    response_model=DeviceReassignResponse,
    summary="Reassign device to a target location or unassign to organization scope",
)
async def reassign_device(
    device_id: uuid.UUID,
    req: DeviceReassignRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.reassign_device(
        db, current_user.id, device_id, req
    )


@router.get(
    "/locations/{location_id}/devices",
    response_model=list[DeviceResponse],
    summary="List devices assigned to a specific location (Admin only)",
)
async def list_location_devices(
    location_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    # Verify location exists and caller has admin privileges in owning organization
    from app.domains.locations.models import Location
    from app.domains.organizations.models import OrganizationMember, OrganizationRole

    stmt_loc = select(Location).where(Location.id == location_id)
    res_loc = await db.execute(stmt_loc)
    loc = res_loc.scalar_one_or_none()
    if not loc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Location not found.",
        )

    stmt_actor = select(OrganizationMember).where(
        and_(
            OrganizationMember.organization_id == loc.organization_id,
            OrganizationMember.user_id == current_user.id,
        )
    )
    res_actor = await db.execute(stmt_actor)
    actor = res_actor.scalar_one_or_none()
    if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only organization owners and administrators can view location device inventory.",
        )

    stmt_devs = (
        select(Device)
        .options(selectinload(Device.licenses))
        .where(
            and_(
                Device.organization_id == loc.organization_id,
                Device.location_id == location_id,
            )
        )
        .order_by(Device.created_at.asc())
    )
    res_devs = await db.execute(stmt_devs)
    return list(res_devs.scalars().all())


@router.post(
    "/devices/{device_id}/revoke",
    response_model=DeviceResponse,
    summary="Revoke a device terminal and all its active licenses",
)
async def revoke_device(
    device_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.revoke_device(
        db, current_user.id, device_id
    )


@router.delete(
    "/devices/{device_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a registered device terminal and free its quota",
)
async def delete_device(
    device_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    await CommercialAndLicensingService.delete_device(
        db, current_user.id, device_id
    )
    return None


@router.post(
    "/devices/{device_id}/heartbeat",
    response_model=DeviceHeartbeatResponse,
    summary="POS terminal heartbeat check-in to verify status and refresh offline license lease",
)
async def device_heartbeat(
    device_id: uuid.UUID,
    req: MachineHeartbeatRequest,
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.process_heartbeat(
        db, device_id, req
    )


# Internal Device Verification for VEX Ecosystem Gateways (e.g. VEXPOSCLOUD)
@router.get(
    "/devices/internal/verify",
    response_model=DeviceInternalVerificationResponse,
    summary="Internal ecosystem endpoint to verify device registration and retrieve public key",
)
async def internal_verify_device(
    organization_id: uuid.UUID = Query(..., description="Organization / tenant identifier"),
    terminal_identifier: str = Query(..., description="Hardware fingerprint or device UUID"),
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Direct Policy Decision Point query for downstream gateways (like Cloud Sync).
    Allows authentication lookup by hardware fingerprint or device UUID without duplicate registration.
    """
    # Try parsing terminal_identifier as UUID if possible
    terminal_uuid = None
    try:
        terminal_uuid = uuid.UUID(terminal_identifier)
    except (ValueError, TypeError):
        pass

    conditions = [Device.fingerprint == terminal_identifier]
    if terminal_uuid is not None:
        conditions.append(Device.id == terminal_uuid)

    stmt = select(Device).where(
        Device.organization_id == organization_id,
        or_(*conditions),
    )
    res = await db.execute(stmt)
    device = res.scalar_one_or_none()

    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Device '{terminal_identifier}' not found in organization '{organization_id}'.",
        )

    return DeviceInternalVerificationResponse(
        device_id=device.id,
        organization_id=device.organization_id,
        fingerprint=device.fingerprint,
        name=device.name,
        public_key=device.public_key,
        status=device.status,
        is_valid=(device.status == DeviceStatus.ACTIVE),
    )

