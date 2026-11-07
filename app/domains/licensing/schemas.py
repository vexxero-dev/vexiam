import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from app.domains.subscriptions.models import OwnerType, SubscriptionStatus
from app.domains.licensing.models import DeviceStatus, LicenseStatus


# Subscription Schemas
class PlanCreateRequest(BaseModel):
    application_id: uuid.UUID
    code: str = Field(..., min_length=2, max_length=50)
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    user_seats: int = Field(default=1, ge=1)
    device_seats: int = Field(default=0, ge=0)


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    application_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    user_seats: int
    device_seats: int
    created_at: datetime


class SubscriptionCreateRequest(BaseModel):
    plan_id: uuid.UUID
    owner_type: OwnerType
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    owner_type: OwnerType
    organization_id: Optional[uuid.UUID] = None
    user_id: Optional[uuid.UUID] = None
    status: SubscriptionStatus
    expires_at: Optional[datetime] = None
    created_at: datetime
    plan: Optional[PlanResponse] = None


# Device & Licensing Schemas
class DeviceRegisterRequest(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=100)
    fingerprint: str = Field(..., min_length=8, max_length=128)
    public_key: str = Field(..., min_length=10, description="Device's Ed25519 public key")


class DeviceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: Optional[uuid.UUID] = None  # Alias for backward-compatible client SDKs
    organization_id: uuid.UUID
    name: str
    fingerprint: str
    status: DeviceStatus
    last_heartbeat_at: Optional[datetime] = None
    created_at: datetime

    def model_post_init(self, __context: Any) -> None:
        if self.device_id is None:
            self.device_id = self.id


class LicenseIssueRequest(BaseModel):
    device_id: uuid.UUID
    application_id: Optional[str] = None  # Accepts UUID string or application code (e.g., 'VEX-POS' / 'vexxero-pos')


class DeviceHeartbeatRequest(BaseModel):
    fingerprint: str = Field(..., min_length=8, max_length=128)
    application_id: Optional[str] = None


class DeviceHeartbeatResponse(BaseModel):
    device_id: uuid.UUID
    device_status: DeviceStatus
    license_status: LicenseStatus
    is_valid: bool
    message: str
    license: Optional["LicenseResponse"] = None


class LicenseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    device_id: uuid.UUID
    application_id: uuid.UUID
    signed_payload: str
    signature: str
    status: LicenseStatus
    expires_at: datetime
    issued_at: datetime

    # Backward-compatible envelope fields for POS clients expecting IAMLicenseActivationResponse
    is_valid: bool = True
    device_status: str = "ACTIVE"
    license_status: str = "ACTIVE"
    license: Optional[dict] = None

    def model_post_init(self, __context: Any) -> None:
        if self.license is None:
            self.license = {
                "signed_payload": self.signed_payload,
                "signature": self.signature,
            }


class OfflineLicensePayload(BaseModel):
    license_id: str
    device_id: str
    organization_id: str
    application_code: str
    fingerprint: str
    issued_at: int
    expires_at: int
    grace_period_days: int
