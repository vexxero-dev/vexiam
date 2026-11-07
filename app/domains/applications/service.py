import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.applications.models import (
    Application,
    ApplicationRole,
    Permission,
    ApplicationAssignment,
    AssignmentStatus,
)
from app.domains.organizations.models import OrganizationMember, OrganizationRole
from app.domains.applications.schemas import (
    ApplicationCreateRequest,
    PermissionCreateRequest,
    RoleCreateRequest,
    AssignmentCreateRequest,
    AccessEvaluationRequest,
    AccessEvaluationResponse,
)


class ApplicationService:
    @staticmethod
    async def create_application(db: AsyncSession, req: ApplicationCreateRequest) -> Application:
        stmt = select(Application).where(Application.code == req.code.upper())
        res = await db.execute(stmt)
        if res.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application with code '{req.code.upper()}' already exists.",
            )

        app = Application(
            code=req.code.upper(),
            name=req.name,
            description=req.description,
            type=req.type,
            is_active=True,
        )
        db.add(app)
        await db.commit()
        await db.refresh(app)
        return app

    @staticmethod
    async def list_applications(db: AsyncSession) -> list[Application]:
        stmt = select(Application).where(Application.is_active == True)
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def create_permission(
        db: AsyncSession, app_id: uuid.UUID, req: PermissionCreateRequest
    ) -> Permission:
        perm = Permission(
            application_id=app_id,
            code=req.code.lower(),
            name=req.name,
            description=req.description,
        )
        db.add(perm)
        await db.commit()
        await db.refresh(perm)
        return perm

    @staticmethod
    async def create_role(
        db: AsyncSession, app_id: uuid.UUID, req: RoleCreateRequest
    ) -> ApplicationRole:
        role = ApplicationRole(
            application_id=app_id,
            code=req.code.upper(),
            name=req.name,
            description=req.description,
        )
        if req.permission_ids:
            stmt = select(Permission).where(
                and_(
                    Permission.application_id == app_id,
                    Permission.id.in_(req.permission_ids),
                )
            )
            res = await db.execute(stmt)
            role.permissions = list(res.scalars().all())

        db.add(role)
        await db.commit()
        await db.refresh(role, ["permissions"])
        return role

    @staticmethod
    async def assign_application_access(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        req: AssignmentCreateRequest,
    ) -> ApplicationAssignment:
        # Check actor is OWNER or ADMIN of the org
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can assign application access.",
            )

        # Check target user is a member of the organization
        stmt_target = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == req.user_id,
            )
        )
        res_target = await db.execute(stmt_target)
        if not res_target.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Target user is not a member of this organization.",
            )

        # Fetch roles
        stmt_roles = select(ApplicationRole).options(selectinload(ApplicationRole.permissions)).where(
            and_(
                ApplicationRole.application_id == req.application_id,
                ApplicationRole.id.in_(req.role_ids),
            )
        )
        res_roles = await db.execute(stmt_roles)
        roles = list(res_roles.scalars().all())

        # Check if assignment already exists
        stmt_assign = (
            select(ApplicationAssignment)
            .options(
                selectinload(ApplicationAssignment.roles).selectinload(ApplicationRole.permissions),
                selectinload(ApplicationAssignment.application),
            )
            .where(
                and_(
                    ApplicationAssignment.organization_id == org_id,
                    ApplicationAssignment.user_id == req.user_id,
                    ApplicationAssignment.application_id == req.application_id,
                )
            )
        )
        res_assign = await db.execute(stmt_assign)
        assignment = res_assign.scalar_one_or_none()

        if assignment:
            assignment.roles = roles
            assignment.status = AssignmentStatus.ACTIVE
        else:
            assignment = ApplicationAssignment(
                organization_id=org_id,
                user_id=req.user_id,
                application_id=req.application_id,
                status=AssignmentStatus.ACTIVE,
                roles=roles,
            )
            db.add(assignment)

        await db.commit()

        # Re-fetch with eager loaded relations
        stmt_fresh = (
            select(ApplicationAssignment)
            .options(
                selectinload(ApplicationAssignment.roles).selectinload(ApplicationRole.permissions),
                selectinload(ApplicationAssignment.application),
            )
            .where(
                and_(
                    ApplicationAssignment.organization_id == org_id,
                    ApplicationAssignment.user_id == req.user_id,
                    ApplicationAssignment.application_id == req.application_id,
                )
            )
        )
        res_fresh = await db.execute(stmt_fresh)
        return res_fresh.scalar_one()

    @staticmethod
    async def evaluate_access(
        db: AsyncSession, req: AccessEvaluationRequest
    ) -> AccessEvaluationResponse:
        """Policy Decision Point (PDP) evaluating if a user has access to an app and permission."""
        # 1. Check organization membership
        stmt_member = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == req.organization_id,
                OrganizationMember.user_id == req.user_id,
            )
        )
        res_member = await db.execute(stmt_member)
        member = res_member.scalar_one_or_none()
        if not member:
            return AccessEvaluationResponse(
                authorized=False,
                reason="User is not a member of the organization.",
                application_code=req.application_code,
            )

        # 2. Check application assignment
        stmt_app = select(Application).where(Application.code == req.application_code.upper())
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app or not app.is_active:
            return AccessEvaluationResponse(
                authorized=False,
                reason="Application not found or inactive.",
                application_code=req.application_code,
            )

        stmt_assign = (
            select(ApplicationAssignment)
            .options(
                selectinload(ApplicationAssignment.roles).selectinload(ApplicationRole.permissions)
            )
            .where(
                and_(
                    ApplicationAssignment.organization_id == req.organization_id,
                    ApplicationAssignment.user_id == req.user_id,
                    ApplicationAssignment.application_id == app.id,
                    ApplicationAssignment.status == AssignmentStatus.ACTIVE,
                )
            )
        )
        res_assign = await db.execute(stmt_assign)
        assignment = res_assign.scalar_one_or_none()

        if not assignment:
            return AccessEvaluationResponse(
                authorized=False,
                reason="User has not been granted access to this application in this organization.",
                application_code=req.application_code,
            )

        roles_list: list[str] = []
        perms_set: set[str] = set()

        for role in assignment.roles:
            roles_list.append(role.code)
            for perm in role.permissions:
                perms_set.add(perm.code)

        # If a specific permission was requested, evaluate it
        if req.required_permission and req.required_permission.lower() not in perms_set:
            return AccessEvaluationResponse(
                authorized=False,
                reason=f"Missing required permission '{req.required_permission}'.",
                application_code=req.application_code,
                roles=roles_list,
                permissions=list(perms_set),
            )

        return AccessEvaluationResponse(
            authorized=True,
            application_code=req.application_code,
            roles=roles_list,
            permissions=list(perms_set),
        )
