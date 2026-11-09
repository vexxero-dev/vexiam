import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional
from app.domains.applications.models import ApplicationType, AssignmentStatus
from app.domains.identity.schemas import UserResponse


class PermissionCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None


class RoleCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    permission_ids: list[uuid.UUID] = []


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    permissions: list[PermissionResponse] = []


class ApplicationCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    type: ApplicationType = ApplicationType.WEB


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    type: ApplicationType
    is_active: bool
    created_at: datetime


class AssignmentCreateRequest(BaseModel):
    user_id: uuid.UUID
    application_id: uuid.UUID
    role_ids: list[uuid.UUID] = []


class AssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID
    application_id: uuid.UUID
    status: AssignmentStatus
    created_at: datetime
    roles: list[RoleResponse] = []
    application: Optional[ApplicationResponse] = None
    user: Optional[UserResponse] = None


class AccessEvaluationRequest(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    application_code: str
    required_permission: Optional[str] = None


class AccessEvaluationResponse(BaseModel):
    authorized: bool
    reason: Optional[str] = None
    application_code: str
    roles: list[str] = []
    permissions: list[str] = []
