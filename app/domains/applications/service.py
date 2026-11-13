import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.subscriptions.models import Subscription, Plan, SubscriptionStatus
from app.domains.applications.models import (
    Application,
    ApplicationStatus,
    PlatformType,
    ApplicationRole,
    Permission,
    ApplicationAssignment,
    AssignmentStatus,
    ApplicationClient,
    ClientStatus,
    ApplicationInstallation,
    InstallationStatus,
)
from app.domains.organizations.models import OrganizationMember, OrganizationRole
from app.domains.identity.models import User
from app.domains.identity.sync_service import IdentitySyncService
from app.domains.identity.sync_models import SyncEventType
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
            platform_type=req.platform_type,
            status=ApplicationStatus.ACTIVE,
            current_version=req.current_version,
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
    async def list_roles(db: AsyncSession, app_id: uuid.UUID) -> list[ApplicationRole]:
        stmt = (
            select(ApplicationRole)
            .options(selectinload(ApplicationRole.permissions))
            .where(ApplicationRole.application_id == app_id)
        )
        res = await db.execute(stmt)
        return list(res.scalars().all())

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

        # Enforce Commercial Entitlements: Verify active organization subscription for this application
        stmt_subs = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == org_id,
                    Plan.application_id == req.application_id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
            .options(selectinload(Subscription.plan))
            .with_for_update()
        )
        res_subs = await db.execute(stmt_subs)
        active_subs = list(res_subs.scalars().all())
        if not active_subs:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Organization does not hold an active subscription for this application. Subscribe to a plan before assigning user seats.",
            )

        total_user_seats = sum(s.plan.user_seats for s in active_subs if s.plan)

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

        # If creating a new active assignment or reactivating, enforce user seat quota
        if not assignment or assignment.status != AssignmentStatus.ACTIVE:
            stmt_active_seats = select(func.count(ApplicationAssignment.id)).where(
                and_(
                    ApplicationAssignment.organization_id == org_id,
                    ApplicationAssignment.application_id == req.application_id,
                    ApplicationAssignment.status == AssignmentStatus.ACTIVE,
                    ApplicationAssignment.user_id != req.user_id,
                )
            )
            res_active_seats = await db.execute(stmt_active_seats)
            current_active_seats = res_active_seats.scalar() or 0

            if current_active_seats >= total_user_seats:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"User seat quota exceeded (Limit: {total_user_seats}, Current: {current_active_seats}). Upgrade subscription plan to assign more user seats.",
                )

        if assignment:
            assignment.roles = roles
            assignment.status = AssignmentStatus.ACTIVE
            assignment.assignment_version += 1
            event_type = SyncEventType.APPLICATION_ASSIGNMENT_UPDATED
        else:
            assignment = ApplicationAssignment(
                organization_id=org_id,
                user_id=req.user_id,
                application_id=req.application_id,
                status=AssignmentStatus.ACTIVE,
                assignment_version=1,
                roles=roles,
            )
            db.add(assignment)
            event_type = SyncEventType.APPLICATION_ASSIGNED

        await db.flush()

        # Emit IdentitySyncEvent
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=event_type,
            organization_id=org_id,
            application_id=req.application_id,
            user_id=req.user_id,
            entity_id=str(assignment.id),
            version=assignment.assignment_version,
            payload={
                "assignment_id": str(assignment.id),
                "user_id": str(req.user_id),
                "application_id": str(req.application_id),
                "status": assignment.status.value,
                "roles": [r.code for r in roles],
            },
        )

        await db.commit()

        # Re-fetch with eager loaded relations
        stmt_fresh = (
            select(ApplicationAssignment)
            .options(
                selectinload(ApplicationAssignment.roles).selectinload(ApplicationRole.permissions),
                selectinload(ApplicationAssignment.application),
                selectinload(ApplicationAssignment.user).selectinload(User.profile),
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
    async def list_assignments(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        app_id: uuid.UUID | None = None,
    ) -> list[ApplicationAssignment]:
        # Check actor is a member of the org
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        if not res_actor.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You must be a member of this organization to view application assignments.",
            )

        stmt = (
            select(ApplicationAssignment)
            .options(
                selectinload(ApplicationAssignment.roles).selectinload(ApplicationRole.permissions),
                selectinload(ApplicationAssignment.application),
                selectinload(ApplicationAssignment.user).selectinload(User.profile),
            )
            .where(
                and_(
                    ApplicationAssignment.organization_id == org_id,
                    ApplicationAssignment.status == AssignmentStatus.ACTIVE,
                )
            )
        )
        if app_id:
            stmt = stmt.where(ApplicationAssignment.application_id == app_id)

        stmt = stmt.order_by(ApplicationAssignment.created_at.desc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def revoke_assignment(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        assignment_id: uuid.UUID,
    ) -> None:
        # Check actor is OWNER or ADMIN
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
                detail="Only organization owners and administrators can revoke application access.",
            )

        stmt_assign = (
            select(ApplicationAssignment)
            .where(
                and_(
                    ApplicationAssignment.id == assignment_id,
                    ApplicationAssignment.organization_id == org_id,
                )
            )
            .with_for_update()
        )
        res_assign = await db.execute(stmt_assign)
        assignment = res_assign.scalar_one_or_none()
        if not assignment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application assignment not found.",
            )

        if assignment.status != AssignmentStatus.REVOKED:
            assignment.status = AssignmentStatus.REVOKED
            assignment.assignment_version += 1
            await db.flush()

            # Emit sync event
            await IdentitySyncService.record_sync_event(
                db=db,
                event_type=SyncEventType.APPLICATION_ACCESS_REVOKED,
                organization_id=org_id,
                application_id=assignment.application_id,
                user_id=assignment.user_id,
                entity_id=str(assignment.id),
                version=assignment.assignment_version,
                payload={
                    "assignment_id": str(assignment.id),
                    "user_id": str(assignment.user_id),
                    "application_id": str(assignment.application_id),
                    "status": assignment.status.value,
                },
            )

            await db.commit()

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

        # 3. Commercial Entitlement Check: Verify active, non-expired organization subscription
        now_utc = datetime.now(timezone.utc)
        stmt_sub = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == req.organization_id,
                    Plan.application_id == app.id,
                    Subscription.status == SubscriptionStatus.ACTIVE,
                )
            )
        )
        res_sub = await db.execute(stmt_sub)
        active_subs = list(res_sub.scalars().all())
        valid_subscription = None
        for sub in active_subs:
            if sub.expires_at is None:
                valid_subscription = sub
                break
            exp = sub.expires_at if sub.expires_at.tzinfo is not None else sub.expires_at.replace(tzinfo=timezone.utc)
            if exp > now_utc:
                valid_subscription = sub
                break

        if not valid_subscription:
            return AccessEvaluationResponse(
                authorized=False,
                reason="Organization does not hold an active subscription for this application or subscription has expired.",
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

    # ------------------ Application Client Management ------------------
    @staticmethod
    async def create_client(
        db: AsyncSession, application_id: uuid.UUID, client_code: str, client_name: str, client_type: str = "DESKTOP"
    ) -> ApplicationClient:
        stmt_app = select(Application).where(Application.id == application_id)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found.",
            )

        code_clean = client_code.strip().upper()
        stmt_existing = select(ApplicationClient).where(ApplicationClient.client_code == code_clean)
        res_existing = await db.execute(stmt_existing)
        if res_existing.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Application client '{code_clean}' already exists.",
            )

        client = ApplicationClient(
            application_id=application_id,
            client_code=code_clean,
            client_name=client_name,
            client_type=client_type,
            status=ClientStatus.ACTIVE,
        )
        db.add(client)
        await db.commit()
        await db.refresh(client)
        return client

    @staticmethod
    async def list_clients(db: AsyncSession, application_id: uuid.UUID) -> list[ApplicationClient]:
        stmt = select(ApplicationClient).where(ApplicationClient.application_id == application_id).order_by(ApplicationClient.created_at.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    # ------------------ Application Installation Management ------------------
    @staticmethod
    async def register_installation(
        db: AsyncSession,
        application_id: uuid.UUID,
        device_id: uuid.UUID,
        installation_id: str,
        version: str = "1.0.0",
        platform: str = "WINDOWS",
    ) -> ApplicationInstallation:
        from app.domains.licensing.models import Device

        stmt_app = select(Application).where(Application.id == application_id)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app or not app.is_active or app.status != ApplicationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found, inactive, or disabled.",
            )

        stmt_dev = select(Device).where(Device.id == device_id)
        res_dev = await db.execute(stmt_dev)
        device = res_dev.scalar_one_or_none()
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found.",
            )

        stmt_inst = select(ApplicationInstallation).where(
            and_(
                ApplicationInstallation.application_id == application_id,
                ApplicationInstallation.device_id == device_id,
                ApplicationInstallation.installation_id == installation_id,
            )
        )
        res_inst = await db.execute(stmt_inst)
        existing = res_inst.scalar_one_or_none()
        now = datetime.now(timezone.utc)

        if existing:
            existing.version = version
            existing.platform = platform
            existing.last_seen_at = now
            existing.status = InstallationStatus.ACTIVE
            await db.commit()
            await db.refresh(existing)
            return existing

        inst = ApplicationInstallation(
            application_id=application_id,
            device_id=device_id,
            installation_id=installation_id,
            version=version,
            platform=platform,
            status=InstallationStatus.ACTIVE,
            registered_at=now,
            last_seen_at=now,
        )
        db.add(inst)
        await db.commit()
        await db.refresh(inst)
        return inst

