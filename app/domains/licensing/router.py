import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_platform_admin, require_verified_user
from app.domains.identity.models import User
from app.domains.licensing.schemas import (
    PlanCreateRequest,
    PlanResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    DeviceChallengeResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    DeviceHeartbeatRequest,
    MachineHeartbeatRequest,
    DeviceHeartbeatResponse,
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
