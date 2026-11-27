import uuid
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, or_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.locations.models import Location, LocationStatus, LocationApplication, LocationApplicationStatus
from app.domains.locations.schemas import LocationCreateRequest, LocationUpdateRequest, LocationApplicationEnableRequest
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.applications.models import Application
from app.domains.subscriptions.models import Subscription, Plan, SubscriptionStatus
from app.domains.licensing.models import Device, DeviceStatus
from app.domains.identity.sync_service import IdentitySyncService
from app.domains.identity.sync_models import SyncEventType


class LocationService:
    @staticmethod
    async def create_location(
        db: AsyncSession, org_id: uuid.UUID, actor_user_id: uuid.UUID, req: LocationCreateRequest
    ) -> Location:
        # 1. Verify organization exists and is not closed/archived
        stmt_org = select(Organization).where(Organization.id == org_id)
        res_org = await db.execute(stmt_org)
        org = res_org.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found.",
            )

        # 2. Check actor has admin permissions in org
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
                detail="Only organization owners and administrators can create locations.",
            )

        # 3. Code uniqueness check within organization
        stmt_loc = select(Location).where(
            and_(
                Location.organization_id == org_id,
                func.upper(Location.code) == req.code.strip().upper(),
            )
        )
        res_loc = await db.execute(stmt_loc)
        if res_loc.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Location with code '{req.code.strip().upper()}' already exists in this organization.",
            )

        now = datetime.now(timezone.utc)
        location = Location(
            organization_id=org_id,
            code=req.code.strip().upper(),
            name=req.name.strip(),
            description=req.description,
            address_line1=req.address_line1,
            address_line2=req.address_line2,
            city=req.city,
            state_province=req.state_province,
            postal_code=req.postal_code,
            country_code=req.country_code,
            timezone=req.timezone,
            status=LocationStatus.ACTIVE,
            metadata_json=req.metadata,
            created_at=now,
            updated_at=now,
        )
        db.add(location)
        await db.flush()

        # Emit transactional sync event
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.LOCATION_CREATED,
            organization_id=org_id,
            application_id=None,
            user_id=actor_user_id,
            entity_id=str(location.id),
            version=1,
            payload={
                "location_id": str(location.id),
                "code": location.code,
                "name": location.name,
                "status": location.status.value,
                "timezone": location.timezone,
                "metadata": location.metadata_json,
            },
        )

        await db.commit()
        await db.refresh(location, ["applications"])
        return location

    @staticmethod
    async def list_locations(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        status_filter: LocationStatus | None = None,
        application_id: uuid.UUID | None = None,
    ) -> list[Location]:
        # Check actor belongs to org
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
                detail="User is not a member of this organization.",
            )

        stmt = (
            select(Location)
            .options(
                selectinload(Location.applications).selectinload(LocationApplication.application)
            )
            .where(Location.organization_id == org_id)
        )

        if status_filter:
            stmt = stmt.where(Location.status == status_filter)

        if application_id:
            stmt = stmt.join(LocationApplication, Location.id == LocationApplication.location_id).where(
                and_(
                    LocationApplication.application_id == application_id,
                    LocationApplication.status == LocationApplicationStatus.ACTIVE,
                )
            )

        stmt = stmt.order_by(Location.created_at.asc())
        res = await db.execute(stmt)
        return list(res.scalars().all())

    @staticmethod
    async def get_location(
        db: AsyncSession, location_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> Location:
        stmt = (
            select(Location)
            .options(
                selectinload(Location.applications).selectinload(LocationApplication.application)
            )
            .where(Location.id == location_id)
            .with_for_update()
        )
        res = await db.execute(stmt)
        loc = res.scalar_one_or_none()
        if not loc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Location not found.",
            )

        # Check membership
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == loc.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        if not res_actor.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not a member of the organization owning this location.",
            )

        return loc

    @staticmethod
    async def update_location(
        db: AsyncSession, location_id: uuid.UUID, actor_user_id: uuid.UUID, req: LocationUpdateRequest
    ) -> Location:
        loc = await LocationService.get_location(db, location_id, actor_user_id)

        # Admin rights required
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == loc.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can update locations.",
            )

        if loc.status == LocationStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived locations cannot be modified.",
            )

        if req.name is not None:
            loc.name = req.name.strip()
        if req.description is not None:
            loc.description = req.description
        if req.address_line1 is not None:
            loc.address_line1 = req.address_line1
        if req.address_line2 is not None:
            loc.address_line2 = req.address_line2
        if req.city is not None:
            loc.city = req.city
        if req.state_province is not None:
            loc.state_province = req.state_province
        if req.postal_code is not None:
            loc.postal_code = req.postal_code
        if req.country_code is not None:
            loc.country_code = req.country_code
        if req.timezone is not None:
            loc.timezone = req.timezone
        if req.metadata is not None:
            loc.metadata_json = req.metadata
        if req.status is not None and req.status != LocationStatus.ARCHIVED:
            loc.status = req.status

        loc.updated_at = datetime.now(timezone.utc)
        await db.flush()

        # Emit transactional sync event
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.LOCATION_UPDATED,
            organization_id=loc.organization_id,
            application_id=None,
            user_id=actor_user_id,
            entity_id=str(loc.id),
            version=1,
            payload={
                "location_id": str(loc.id),
                "code": loc.code,
                "name": loc.name,
                "status": loc.status.value,
                "timezone": loc.timezone,
                "metadata": loc.metadata_json,
            },
        )

        await db.commit()
        await db.refresh(loc, ["applications"])
        return loc

    @staticmethod
    async def archive_location(
        db: AsyncSession, location_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> Location:
        loc = await LocationService.get_location(db, location_id, actor_user_id)

        # Admin rights required
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == loc.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can archive locations.",
            )

        if loc.status == LocationStatus.ARCHIVED:
            return loc

        # Safeguard: Check if location has active applications enabled
        stmt_active_apps = select(func.count(LocationApplication.id)).where(
            and_(
                LocationApplication.location_id == loc.id,
                LocationApplication.status == LocationApplicationStatus.ACTIVE,
            )
        )
        res_active_apps = await db.execute(stmt_active_apps)
        if (res_active_apps.scalar() or 0) > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot archive location with active applications. Deactivate applications before archiving.",
            )

        # Safeguard: Check if location has registered active or pending devices
        # (devices table will be linked via location_id in Phase 2, but we proactively check attribute or column if present)
        if hasattr(Device, "location_id"):
            stmt_active_devs = select(func.count(Device.id)).where(
                and_(
                    getattr(Device, "location_id") == loc.id,
                    Device.status != DeviceStatus.DECOMMISSIONED,
                )
            )
            res_active_devs = await db.execute(stmt_active_devs)
            if (res_active_devs.scalar() or 0) > 0:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot archive location with active or registered devices. Reassign or decommission devices first.",
                )

        # Transition status
        now = datetime.now(timezone.utc)
        loc.status = LocationStatus.ARCHIVED
        loc.deleted_at = now
        loc.updated_at = now
        await db.flush()

        # Emit transactional sync event
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.LOCATION_ARCHIVED,
            organization_id=loc.organization_id,
            application_id=None,
            user_id=actor_user_id,
            entity_id=str(loc.id),
            version=1,
            payload={
                "location_id": str(loc.id),
                "code": loc.code,
                "status": LocationStatus.ARCHIVED.value,
                "archived_at": int(now.timestamp()),
            },
        )

        await db.commit()
        await db.refresh(loc, ["applications"])
        return loc

    @staticmethod
    async def enable_application_at_location(
        db: AsyncSession, location_id: uuid.UUID, actor_user_id: uuid.UUID, req: LocationApplicationEnableRequest
    ) -> LocationApplication:
        loc = await LocationService.get_location(db, location_id, actor_user_id)

        # Check admin rights
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == loc.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can enable applications.",
            )

        if loc.status == LocationStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot enable applications on an archived location.",
            )

        # Check application exists and is active
        stmt_app = select(Application).where(Application.id == req.application_id)
        res_app = await db.execute(stmt_app)
        app = res_app.scalar_one_or_none()
        if not app or not app.is_active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or inactive.",
            )

        # Commercial & Access Control Check: Verify organization holds an active, non-expired subscription for this application
        now_utc = datetime.now(timezone.utc)
        stmt_sub = (
            select(Subscription)
            .join(Plan, Subscription.plan_id == Plan.id)
            .where(
                and_(
                    Subscription.organization_id == loc.organization_id,
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
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Organization does not hold an active subscription for {app.name}. Subscribe to a plan before enabling this application at a location.",
            )

        # Check if already enabled
        stmt_loc_app = select(LocationApplication).where(
            and_(
                LocationApplication.location_id == loc.id,
                LocationApplication.application_id == req.application_id,
            )
        )
        res_loc_app = await db.execute(stmt_loc_app)
        loc_app = res_loc_app.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        if loc_app:
            loc_app.status = LocationApplicationStatus.ACTIVE
            loc_app.deactivated_at = None
            loc_app.updated_at = now
        else:
            loc_app = LocationApplication(
                organization_id=loc.organization_id,
                location_id=loc.id,
                application_id=req.application_id,
                status=LocationApplicationStatus.ACTIVE,
                activated_at=now,
                created_at=now,
                updated_at=now,
            )
            db.add(loc_app)

        await db.flush()

        # Emit transactional sync event
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.LOCATION_APPLICATION_ACTIVATED,
            organization_id=loc.organization_id,
            application_id=req.application_id,
            user_id=actor_user_id,
            entity_id=str(loc_app.id),
            version=1,
            payload={
                "location_application_id": str(loc_app.id),
                "location_id": str(loc.id),
                "application_id": str(req.application_id),
                "application_code": app.code,
                "status": loc_app.status.value,
            },
        )

        await db.commit()
        await db.refresh(loc_app, ["application"])
        return loc_app

    @staticmethod
    async def deactivate_application_at_location(
        db: AsyncSession, location_id: uuid.UUID, app_id: uuid.UUID, actor_user_id: uuid.UUID
    ) -> LocationApplication:
        loc = await LocationService.get_location(db, location_id, actor_user_id)

        # Check admin rights
        stmt_actor = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == loc.organization_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        res_actor = await db.execute(stmt_actor)
        actor = res_actor.scalar_one_or_none()
        if not actor or actor.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can deactivate applications.",
            )

        stmt_loc_app = select(LocationApplication).options(
            selectinload(LocationApplication.application)
        ).where(
            and_(
                LocationApplication.location_id == loc.id,
                LocationApplication.application_id == app_id,
            )
        )
        res_loc_app = await db.execute(stmt_loc_app)
        loc_app = res_loc_app.scalar_one_or_none()
        if not loc_app or loc_app.status != LocationApplicationStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application is not actively enabled at this location.",
            )

        now = datetime.now(timezone.utc)
        loc_app.status = LocationApplicationStatus.DEACTIVATED
        loc_app.deactivated_at = now
        loc_app.updated_at = now
        await db.flush()

        # Emit transactional sync event
        await IdentitySyncService.record_sync_event(
            db=db,
            event_type=SyncEventType.LOCATION_APPLICATION_DEACTIVATED,
            organization_id=loc.organization_id,
            application_id=app_id,
            user_id=actor_user_id,
            entity_id=str(loc_app.id),
            version=1,
            payload={
                "location_application_id": str(loc_app.id),
                "location_id": str(loc.id),
                "application_id": str(app_id),
                "application_code": loc_app.application.code if loc_app.application else None,
                "status": loc_app.status.value,
            },
        )

        await db.commit()
        await db.refresh(loc_app)
        return loc_app
