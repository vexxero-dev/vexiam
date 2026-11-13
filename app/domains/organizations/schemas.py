import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from typing import Optional
from app.domains.organizations.models import OrganizationStatus, OrganizationRole, InvitationStatus
from app.domains.identity.schemas import UserResponse


class OrganizationCreateRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    registration_number: Optional[str] = Field(None, max_length=100)


class OrganizationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    registration_number: Optional[str] = None
    status: OrganizationStatus
    created_at: datetime
    role: Optional[OrganizationRole] = None
    permissions: list[str] = Field(default_factory=list)


class OrganizationMemberResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    role: OrganizationRole
    created_at: datetime
    user: Optional[UserResponse] = None


class InvitationCreateRequest(BaseModel):
    email: EmailStr
    role: OrganizationRole = OrganizationRole.MEMBER

    @field_validator("role")
    @classmethod
    def disallow_owner_role(cls, v: OrganizationRole) -> OrganizationRole:
        if v == OrganizationRole.OWNER:
            raise ValueError(
                "Cannot invite a member as OWNER. Organizations enforce atomic single-ownership; use ownership transfer instead."
            )
        return v


class InvitationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    email: EmailStr
    role: OrganizationRole
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime


class InvitationDetailResponse(InvitationResponse):
    invitation_token: Optional[str] = None  # Included only upon creation for dispatch


class TransferOwnershipRequest(BaseModel):
    new_owner_user_id: uuid.UUID
