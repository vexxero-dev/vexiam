import secrets
import hashlib
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from app.domains.organizations.models import (
    Organization,
    OrganizationMember,
    OrganizationInvitation,
    OrganizationStatus,
    OrganizationRole,
    InvitationStatus,
)
from app.domains.identity.models import User
from app.domains.organizations.schemas import (
    OrganizationCreateRequest,
    InvitationCreateRequest,
    TransferOwnershipRequest,
)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


class OrganizationService:
    @staticmethod
    async def create_organization(
        db: AsyncSession,
        creator_user_id: uuid.UUID,
        req: OrganizationCreateRequest,
    ) -> Organization:
        # 1. Create Organization
        org = Organization(
            name=req.name,
            registration_number=req.registration_number,
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        await db.flush()

        # 2. Automatically make creator the sole initial OWNER
        membership = OrganizationMember(
            organization_id=org.id,
            user_id=creator_user_id,
            role=OrganizationRole.OWNER,
        )
        db.add(membership)
        await db.commit()
        await db.refresh(org)
        return org

    @staticmethod
    async def get_user_organizations(
        db: AsyncSession,
        user_id: uuid.UUID,
    ) -> list[Organization]:
        stmt = (
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(
                and_(
                    OrganizationMember.user_id == user_id,
                    Organization.status != OrganizationStatus.DELETED,
                )
            )
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def get_organization(
        db: AsyncSession,
        org_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Organization:
        stmt = (
            select(Organization)
            .join(OrganizationMember, OrganizationMember.organization_id == Organization.id)
            .where(
                and_(
                    Organization.id == org_id,
                    OrganizationMember.user_id == user_id,
                )
            )
        )
        result = await db.execute(stmt)
        org = result.scalar_one_or_none()
        if not org:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Organization not found or access denied.",
            )
        return org

    @staticmethod
    async def create_invitation(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
        req: InvitationCreateRequest,
    ) -> tuple[OrganizationInvitation, str]:
        # Validate that actor is OWNER or ADMIN
        stmt = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == actor_user_id,
            )
        )
        result = await db.execute(stmt)
        actor_member = result.scalar_one_or_none()
        if not actor_member or actor_member.role not in [OrganizationRole.OWNER, OrganizationRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only organization owners and administrators can invite members.",
            )

        # Check if already an active member
        stmt_user = select(User).where(User.email == req.email.lower())
        res_user = await db.execute(stmt_user)
        existing_user = res_user.scalar_one_or_none()
        if existing_user:
            stmt_mem = select(OrganizationMember).where(
                and_(
                    OrganizationMember.organization_id == org_id,
                    OrganizationMember.user_id == existing_user.id,
                )
            )
            res_mem = await db.execute(stmt_mem)
            if res_mem.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="User is already a member of this organization.",
                )

        raw_token = secrets.token_urlsafe(32)
        token_hash = hash_token(raw_token)
        expires_at = datetime.now(timezone.utc) + timedelta(days=7)

        invitation = OrganizationInvitation(
            organization_id=org_id,
            invited_by_user_id=actor_user_id,
            email=req.email.lower(),
            role=req.role,
            token_hash=token_hash,
            status=InvitationStatus.PENDING,
            expires_at=expires_at,
        )
        db.add(invitation)
        await db.commit()
        await db.refresh(invitation)
        return invitation, raw_token

    @staticmethod
    async def accept_invitation(
        db: AsyncSession,
        raw_token: str,
        user_id: uuid.UUID,
    ) -> OrganizationMember:
        token_h = hash_token(raw_token)
        stmt = (
            select(OrganizationInvitation)
            .options(selectinload(OrganizationInvitation.organization))
            .where(
                and_(
                    OrganizationInvitation.token_hash == token_h,
                    OrganizationInvitation.status == InvitationStatus.PENDING,
                )
            )
        )
        result = await db.execute(stmt)
        invitation = result.scalar_one_or_none()

        if not invitation:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invitation is invalid or has already been accepted/revoked.",
            )

        expires_at = invitation.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at < datetime.now(timezone.utc):
            invitation.status = InvitationStatus.EXPIRED
            await db.commit()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This invitation has expired.",
            )

        # Check user email matches invited email
        stmt_u = select(User).where(User.id == user_id)
        res_u = await db.execute(stmt_u)
        user = res_u.scalar_one_or_none()
        if not user or user.email.lower() != invitation.email.lower():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This invitation was issued to a different email address.",
            )

        # Create Membership
        membership = OrganizationMember(
            organization_id=invitation.organization_id,
            user_id=user_id,
            role=invitation.role,
        )
        invitation.status = InvitationStatus.ACCEPTED
        db.add(membership)
        await db.commit()

        # Re-fetch membership with eager loaded user and user.profile
        stmt_mem = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user).selectinload(User.profile))
            .where(OrganizationMember.id == membership.id)
        )
        res_mem = await db.execute(stmt_mem)
        return res_mem.scalar_one()

    @staticmethod
    async def get_members(
        db: AsyncSession,
        org_id: uuid.UUID,
        actor_user_id: uuid.UUID,
    ) -> list[OrganizationMember]:
        # Ensure actor is a member of the organization
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
                detail="Access denied.",
            )

        stmt = (
            select(OrganizationMember)
            .options(
                selectinload(OrganizationMember.user).selectinload(User.profile)
            )
            .where(OrganizationMember.organization_id == org_id)
        )
        result = await db.execute(stmt)
        return list(result.scalars().all())

    @staticmethod
    async def transfer_ownership(
        db: AsyncSession,
        org_id: uuid.UUID,
        current_owner_id: uuid.UUID,
        req: TransferOwnershipRequest,
    ) -> OrganizationMember:
        if current_owner_id == req.new_owner_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You are already the owner of this organization.",
            )

        # Verify current owner
        stmt_curr = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == current_owner_id,
            )
        )
        res_curr = await db.execute(stmt_curr)
        curr_member = res_curr.scalar_one_or_none()
        if not curr_member or curr_member.role != OrganizationRole.OWNER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the primary owner can transfer organization ownership.",
            )

        # Verify new owner is an existing active member
        stmt_new = select(OrganizationMember).where(
            and_(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == req.new_owner_user_id,
            )
        )
        res_new = await db.execute(stmt_new)
        new_member = res_new.scalar_one_or_none()
        if not new_member:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Target user is not a member of this organization.",
            )

        # Atomically transition roles: Current Owner -> ADMIN, Target -> OWNER
        curr_member.role = OrganizationRole.ADMIN
        new_member.role = OrganizationRole.OWNER
        await db.commit()

        # Re-fetch with eager loaded user & profile
        stmt_mem = (
            select(OrganizationMember)
            .options(selectinload(OrganizationMember.user).selectinload(User.profile))
            .where(OrganizationMember.id == new_member.id)
        )
        res_mem = await db.execute(stmt_mem)
        return res_mem.scalar_one()
