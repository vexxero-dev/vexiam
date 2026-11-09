import uuid
from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.core.dependencies import get_current_user, require_platform_admin
from app.domains.identity.models import User
from app.domains.applications.schemas import (
    ApplicationCreateRequest,
    ApplicationResponse,
    PermissionCreateRequest,
    PermissionResponse,
    RoleCreateRequest,
    RoleResponse,
    AssignmentCreateRequest,
    AssignmentResponse,
    AccessEvaluationRequest,
    AccessEvaluationResponse,
)
from app.domains.applications.service import ApplicationService

router = APIRouter(tags=["Application Registry & Access Control"])


@router.post(
    "/applications",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new application in the Vexxero ecosystem",
)
async def register_application(
    req: ApplicationCreateRequest,
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.create_application(db, req)


@router.get(
    "/applications",
    response_model=list[ApplicationResponse],
    summary="List all registered applications",
)
async def list_applications(
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.list_applications(db)


@router.post(
    "/applications/{app_id}/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define an application-specific permission",
)
async def create_permission(
    app_id: uuid.UUID,
    req: PermissionCreateRequest,
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.create_permission(db, app_id, req)


@router.post(
    "/applications/{app_id}/roles",
    response_model=RoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Define an application-specific role bundled with permissions",
)
async def create_role(
    app_id: uuid.UUID,
    req: RoleCreateRequest,
    _admin: bool = Depends(require_platform_admin),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.create_role(db, app_id, req)


@router.get(
    "/applications/{app_id}/roles",
    response_model=list[RoleResponse],
    summary="List roles for an application",
)
async def list_roles(
    app_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.list_roles(db, app_id)


@router.post(
    "/organizations/{org_id}/assignments",
    response_model=AssignmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Assign an application and specific roles to an organization member",
)
async def assign_application_access(
    org_id: uuid.UUID,
    req: AssignmentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.assign_application_access(
        db, org_id, current_user.id, req
    )


@router.get(
    "/organizations/{org_id}/assignments",
    response_model=list[AssignmentResponse],
    summary="List all application assignments for an organization",
)
async def list_organization_assignments(
    org_id: uuid.UUID,
    app_id: uuid.UUID | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.list_assignments(
        db, org_id, current_user.id, app_id
    )


@router.delete(
    "/organizations/{org_id}/assignments/{assignment_id}",
    status_code=status.HTTP_200_OK,
    summary="Revoke an application assignment from a user, freeing the subscription seat",
)
async def revoke_application_assignment(
    org_id: uuid.UUID,
    assignment_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    await ApplicationService.revoke_assignment(
        db, org_id, current_user.id, assignment_id
    )
    return {"message": "Application assignment revoked successfully."}


@router.post(
    "/access/evaluate",
    response_model=AccessEvaluationResponse,
    summary="Policy Decision Point (PDP) endpoint for downstream apps to verify access and permissions",
)
async def evaluate_access(
    req: AccessEvaluationRequest,
    db: AsyncSession = Depends(get_db),
):
    return await ApplicationService.evaluate_access(db, req)
