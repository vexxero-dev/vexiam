import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_verified_user
from app.domains.identity.models import User
from app.domains.locations.models import LocationStatus
from app.domains.locations.schemas import (
    LocationCreateRequest,
    LocationUpdateRequest,
    LocationResponse,
    LocationApplicationResponse,
    LocationApplicationEnableRequest,
)
from app.domains.locations.service import LocationService

router = APIRouter(tags=["Locations & Operational Scopes"])


@router.post(
    "/organizations/{org_id}/locations",
    response_model=LocationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new location under an organization",
)
async def create_location(
    org_id: uuid.UUID,
    req: LocationCreateRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    loc = await LocationService.create_location(db, org_id, current_user.id, req)
    return loc


@router.get(
    "/organizations/{org_id}/locations",
    response_model=list[LocationResponse],
    summary="List locations belonging to an organization",
)
async def list_locations(
    org_id: uuid.UUID,
    status_filter: Optional[LocationStatus] = Query(None, alias="status"),
    application_id: Optional[uuid.UUID] = Query(None, alias="application_id"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LocationService.list_locations(
        db, org_id, current_user.id, status_filter=status_filter, application_id=application_id
    )


@router.get(
    "/locations/{location_id}",
    response_model=LocationResponse,
    summary="Get details of a specific location",
)
async def get_location(
    location_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await LocationService.get_location(db, location_id, current_user.id)


@router.put(
    "/locations/{location_id}",
    response_model=LocationResponse,
    summary="Update location details or metadata",
)
async def update_location(
    location_id: uuid.UUID,
    req: LocationUpdateRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await LocationService.update_location(db, location_id, current_user.id, req)


@router.post(
    "/locations/{location_id}/archive",
    response_model=LocationResponse,
    summary="Archive a location safely (blocks if active applications remain)",
)
async def archive_location(
    location_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await LocationService.archive_location(db, location_id, current_user.id)


@router.post(
    "/locations/{location_id}/applications",
    response_model=LocationApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enable a VEX application at a specific location",
)
async def enable_application_at_location(
    location_id: uuid.UUID,
    req: LocationApplicationEnableRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    loc_app = await LocationService.enable_application_at_location(
        db, location_id, current_user.id, req
    )
    return LocationApplicationResponse(
        id=loc_app.id,
        organization_id=loc_app.organization_id,
        location_id=loc_app.location_id,
        application_id=loc_app.application_id,
        application_code=loc_app.application.code if loc_app.application else None,
        application_name=loc_app.application.name if loc_app.application else None,
        status=loc_app.status,
        activated_at=loc_app.activated_at,
        deactivated_at=loc_app.deactivated_at,
    )


@router.delete(
    "/locations/{location_id}/applications/{application_id}",
    response_model=LocationApplicationResponse,
    summary="Deactivate a VEX application at a specific location",
)
async def deactivate_application_at_location(
    location_id: uuid.UUID,
    application_id: uuid.UUID,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    loc_app = await LocationService.deactivate_application_at_location(
        db, location_id, application_id, current_user.id
    )
    return LocationApplicationResponse(
        id=loc_app.id,
        organization_id=loc_app.organization_id,
        location_id=loc_app.location_id,
        application_id=loc_app.application_id,
        application_code=loc_app.application.code if loc_app.application else None,
        application_name=loc_app.application.name if loc_app.application else None,
        status=loc_app.status,
        activated_at=loc_app.activated_at,
        deactivated_at=loc_app.deactivated_at,
    )
