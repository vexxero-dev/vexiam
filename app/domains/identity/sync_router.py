import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.domains.identity.sync_schemas import (
    SignedPayloadEnvelope,
    SyncAcknowledgeRequest,
    SyncAcknowledgeResponse,
    OfflineLeaseRequest,
    OfflineLeasePayload,
)
from app.domains.identity.sync_service import IdentitySyncService

router = APIRouter(prefix="/identity/sync", tags=["Identity Synchronization"])


@router.get(
    "/bootstrap",
    response_model=SignedPayloadEnvelope,
    summary="Bootstrap local identity replica with initial full snapshot and schema authority",
)
async def sync_bootstrap(
    organization_id: uuid.UUID = Query(..., description="Organization identifier"),
    application_id: uuid.UUID = Query(..., description="Application identifier (e.g. VEX-POS)"),
    device_id: Optional[uuid.UUID] = Query(None, description="Registered device identifier"),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns a signed Ed25519 bootstrap payload containing the complete set of
    users, roles, permissions, and active application assignments for the terminal.
    """
    return await IdentitySyncService.get_snapshot(
        db=db,
        organization_id=organization_id,
        application_id=application_id,
        device_id=device_id,
    )


@router.get(
    "/snapshot",
    response_model=SignedPayloadEnvelope,
    summary="Get full authorized snapshot of identities, roles, and assignments",
)
async def sync_snapshot(
    organization_id: uuid.UUID = Query(...),
    application_id: uuid.UUID = Query(...),
    device_id: Optional[uuid.UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Used for initial synchronization or when sequence continuity is broken.
    """
    return await IdentitySyncService.get_snapshot(
        db=db,
        organization_id=organization_id,
        application_id=application_id,
        device_id=device_id,
    )


@router.get(
    "/changes",
    response_model=SignedPayloadEnvelope,
    summary="Get incremental identity and authorization changes since sequence",
)
async def sync_changes(
    organization_id: uuid.UUID = Query(...),
    application_id: uuid.UUID = Query(...),
    after_sequence: int = Query(0, ge=0, description="Last sequence known to the client"),
    device_id: Optional[uuid.UUID] = Query(None),
    limit: int = Query(500, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns signed incremental change events (created, updated, suspended, revoked).
    Client applies changes atomically and monotonically increments local sequence.
    """
    return await IdentitySyncService.get_changes(
        db=db,
        organization_id=organization_id,
        application_id=application_id,
        after_sequence=after_sequence,
        device_id=device_id,
        limit=limit,
    )


@router.post(
    "/acknowledge",
    response_model=SyncAcknowledgeResponse,
    status_code=status.HTTP_200_OK,
    summary="Acknowledge receipt and application of synchronization changes",
)
async def sync_acknowledge(
    body: SyncAcknowledgeRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Informs VEX IAM of the terminal's processed sequence number.
    """
    return await IdentitySyncService.acknowledge_sync(
        db=db,
        organization_id=body.organization_id,
        application_id=body.application_id,
        acknowledged_sequence=body.acknowledged_sequence,
        device_id=body.device_id,
    )


@router.post(
    "/leases/issue",
    response_model=OfflineLeasePayload,
    status_code=status.HTTP_200_OK,
    summary="Issue an Ed25519-signed Offline Authorization Lease to a registered terminal",
)
async def issue_offline_lease(
    body: OfflineLeaseRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Issues a cryptographically signed offline authorization lease (e.g. 72 hours)
    binding the device to the organization and application under the current authorization sequence.
    """
    return await IdentitySyncService.issue_offline_lease(
        db=db,
        organization_id=body.organization_id,
        application_id=body.application_id,
        device_id=body.device_id,
    )
