import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_verified_user
from app.domains.identity.models import User
from app.domains.organizations.schemas import (
    OrganizationCreateRequest,
    OrganizationResponse,
    OrganizationMemberResponse,
    InvitationCreateRequest,
    InvitationDetailResponse,
    TransferOwnershipRequest,
)
from app.domains.organizations.service import OrganizationService

router = APIRouter(prefix="/organizations", tags=["Business Entities & User Pool"])


@router.post(
    "",
    response_model=OrganizationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new business entity (caller automatically becomes sole OWNER)",
)
async def create_organization(
    req: OrganizationCreateRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.create_organization(db, current_user.id, req)


@router.get(
    "",
    response_model=list[OrganizationResponse],
    summary="List all organizations the authenticated user belongs to (supports permission filtering)",
)
async def list_organizations(
    permission: str | None = Query(None, description="Optional permission filter (e.g. pos.device.activate)"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.get_user_organizations(
        db, current_user.id, required_permission=permission
    )


@router.get(
    "/{org_id}",
    response_model=OrganizationResponse,
    summary="Get details of a specific organization",
)
async def get_organization(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.get_organization(db, org_id, current_user.id)


@router.get(
    "/{org_id}/members",
    response_model=list[OrganizationMemberResponse],
    summary="List members of the organization user pool",
)
async def get_members(
    org_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.get_members(db, org_id, current_user.id)


@router.post(
    "/{org_id}/invitations",
    response_model=InvitationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Invite an individual VEX IAM identity to the organization",
)
async def invite_member(
    org_id: uuid.UUID,
    req: InvitationCreateRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    invitation, raw_token = await OrganizationService.create_invitation(
        db, org_id, current_user.id, req
    )
    return InvitationDetailResponse(
        id=invitation.id,
        organization_id=invitation.organization_id,
        email=invitation.email,
        role=invitation.role,
        status=invitation.status,
        expires_at=invitation.expires_at,
        created_at=invitation.created_at,
        invitation_token=raw_token,
    )


@router.post(
    "/invitations/{token}/accept",
    response_model=OrganizationMemberResponse,
    summary="Accept an invitation using the secure link token",
)
async def accept_invitation(
    token: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.accept_invitation(db, token, current_user.id)


@router.post(
    "/{org_id}/transfer-ownership",
    response_model=OrganizationMemberResponse,
    summary="Transfer primary OWNER role to another active member",
)
async def transfer_ownership(
    org_id: uuid.UUID,
    req: TransferOwnershipRequest,
    current_user: User = Depends(require_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await OrganizationService.transfer_ownership(db, org_id, current_user.id, req)
