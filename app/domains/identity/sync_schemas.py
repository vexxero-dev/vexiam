import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class SyncAcknowledgeRequest(BaseModel):
    organization_id: uuid.UUID
    application_id: uuid.UUID
    device_id: Optional[uuid.UUID] = None
    acknowledged_sequence: int


class SyncAcknowledgeResponse(BaseModel):
    status: str = "success"
    organization_id: uuid.UUID
    application_id: uuid.UUID
    last_acknowledged_sequence: int
    acknowledged_at: datetime


class SignedPayloadEnvelope(BaseModel):
    issuer: str = "VEX_IAM"
    audience: str
    organization_id: str
    application_id: str
    device_id: Optional[str] = None
    sequence_start: int
    sequence_end: int
    issued_at: str
    expires_at: str
    payload_version: int = 1
    key_id: str = "vex-iam-ed25519-v1"
    data: Any
    signature: str


class SyncSnapshotData(BaseModel):
    organization: dict[str, Any]
    users: list[dict[str, Any]]
    roles: list[dict[str, Any]]
    permissions: list[dict[str, Any]]
    assignments: list[dict[str, Any]]
    latest_sequence: int


class SyncIncrementalData(BaseModel):
    changes: list[dict[str, Any]]
    latest_sequence: int


class OfflineLeaseRequest(BaseModel):
    organization_id: uuid.UUID
    application_id: uuid.UUID
    device_id: uuid.UUID


class OfflineLeasePayload(BaseModel):
    issuer: str = "VEX_IAM"
    audience: str
    organization_id: str
    device_id: str
    application_id: str
    authorization_version: int
    issued_at: str
    expires_at: str
    offline_until: str
    key_id: str = "vex-iam-ed25519-v1"
    signature: str

