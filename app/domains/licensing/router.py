import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.domains.identity.models import User
from app.domains.licensing.schemas import (
    PlanCreateRequest,
    PlanResponse,
    SubscriptionCreateRequest,
    SubscriptionResponse,
    DeviceRegisterRequest,
    DeviceResponse,
    LicenseIssueRequest,
    LicenseResponse,
)
from app.domains.licensing.service import CommercialAndLicensingService

router = APIRouter(tags=["Subscriptions & Device Licensing"])


# Plans & Subscriptions
@router.post(
    "/plans",
    response_model=PlanResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription tier plan",
)
async def create_plan(
    req: PlanCreateRequest,
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
    current_user: User = Depends(get_current_user),
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
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await CommercialAndLicensingService.issue_device_license(
        db, current_user.id, req
    )
