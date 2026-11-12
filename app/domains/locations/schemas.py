import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Any
from app.domains.locations.models import LocationStatus, LocationApplicationStatus


class LocationCreateRequest(BaseModel):
    code: str = Field(..., min_length=2, max_length=50, description="Unique code for location within organization")
    name: str = Field(..., min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=30)
    country_code: Optional[str] = Field(None, max_length=10)
    timezone: str = Field(default="UTC", max_length=50)
    metadata: Optional[dict[str, Any]] = None


class LocationUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=150)
    description: Optional[str] = Field(None, max_length=255)
    address_line1: Optional[str] = Field(None, max_length=255)
    address_line2: Optional[str] = Field(None, max_length=255)
    city: Optional[str] = Field(None, max_length=100)
    state_province: Optional[str] = Field(None, max_length=100)
    postal_code: Optional[str] = Field(None, max_length=30)
    country_code: Optional[str] = Field(None, max_length=10)
    timezone: Optional[str] = Field(None, max_length=50)
    status: Optional[LocationStatus] = None
    metadata: Optional[dict[str, Any]] = None


class LocationApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    location_id: uuid.UUID
    application_id: uuid.UUID
    application_code: Optional[str] = None
    application_name: Optional[str] = None
    status: LocationApplicationStatus
    activated_at: datetime
    deactivated_at: Optional[datetime] = None

    def model_post_init(self, __context: Any) -> None:
        pass

    @classmethod
    def from_orm_model(cls, loc_app: Any) -> "LocationApplicationResponse":
        return cls(
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


class LocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    code: str
    name: str
    description: Optional[str] = None
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country_code: Optional[str] = None
    timezone: str
    status: LocationStatus
    metadata: Optional[dict[str, Any]] = Field(None, validation_alias="metadata_json")
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    applications: list[LocationApplicationResponse] = Field(default_factory=list)


class LocationApplicationEnableRequest(BaseModel):
    application_id: uuid.UUID
