import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.domains.licensing.models import (
    DeviceLicense,
    DeviceLicenseAllocation,
    AllocationStatus,
    AllocationReleaseReason,
    LicenseStatus,
)
from app.domains.subscriptions.models import Subscription, Plan, OwnerType


@pytest.mark.asyncio
async def test_pooled_subscription_provenance_and_allocation_history(client: AsyncClient, db_session):
    # 1. Register Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "poolowner@vexpos.com", "password": "Password123!", "first_name": "Pool", "last_name": "Owner"},
    )
    assert owner_reg.status_code == 201

    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "poolowner@vexpos.com", "password": "Password123!"},
    )
    owner_token = owner_login.json()["access_token"]
    owner_id = owner_login.json()["user"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    from app.core.security import create_email_verification_token
    token = create_email_verification_token(owner_id, "poolowner@vexpos.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    # 2. Create Organization
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Multi-Subscription Retail Corp"},
        headers=owner_headers,
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 3. Create Application
    admin_headers = {"X-Platform-Admin-Key": "dev-platform-admin-key-change-in-production"}
    app_res = await client.post(
        "/api/v1/applications",
        json={"code": "VEX-POS-MULTI", "name": "Vexxero Point of Sale Multi", "type": "LOCAL_HYBRID"},
        headers=admin_headers,
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 4. Create Plan with 2 seats
    plan_res = await client.post(
        "/api/v1/plans",
        json={
            "application_id": app_id,
            "code": "POS-MULTI-DUAL",
            "name": "Enterprise POS Dual Seat",
            "user_seats": 5,
            "device_seats": 2,
        },
        headers=admin_headers,
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # 5. Create TWO subscriptions for this org:
    # Sub A expires in 30 days (earliest)
    # Sub B expires in 90 days (later)
    now = datetime.now(timezone.utc)
    sub_a_res = await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": plan_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )
    assert sub_a_res.status_code == 201
    sub_a_id = sub_a_res.json()["id"]

    sub_b_res = await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": plan_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )
    assert sub_b_res.status_code == 201
    sub_b_id = sub_b_res.json()["id"]

    # Explicitly configure expiration dates via db_session to test FIFO allocation
    from uuid import UUID
    stmt_a = select(Subscription).where(Subscription.id == UUID(sub_a_id))
    sa_inst = (await db_session.execute(stmt_a)).scalar_one()
    sa_inst.expires_at = now + timedelta(days=30)

    stmt_b = select(Subscription).where(Subscription.id == UUID(sub_b_id))
    sb_inst = (await db_session.execute(stmt_b)).scalar_one()
    sb_inst.expires_at = now + timedelta(days=90)
    await db_session.commit()

    # 6. Register 3 devices (Total capacity across 2 subs is 2 + 2 = 4 seats)
    import base64
    from cryptography.hazmat.primitives.asymmetric import ed25519
    from cryptography.hazmat.primitives import serialization

    device_ids = []
    for i in range(1, 4):
        priv = ed25519.Ed25519PrivateKey.generate()
        pub_b64 = base64.b64encode(
            priv.public_key().public_bytes(
                encoding=serialization.Encoding.Raw,
                format=serialization.PublicFormat.Raw,
            )
        ).decode("utf-8")
        dev_res = await client.post(
            "/api/v1/devices/register",
            json={
                "organization_id": org_id,
                "name": f"Terminal 0{i}",
                "fingerprint": f"fp-terminal-00{i}-hardware-id",
                "public_key": pub_b64,
            },
            headers=owner_headers,
        )
        assert dev_res.status_code == 201
        device_ids.append(dev_res.json()["id"])

    # 7. Activate Terminal 1: Should consume Sub A (FIFO: earliest expiration)
    act1 = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": device_ids[0], "application_id": app_id},
        headers=owner_headers,
    )
    assert act1.status_code == 201
    assert act1.json()["subscription_id"] == sub_a_id
    lic1_id = act1.json()["id"]

    # 8. Activate Terminal 2: Should consume Sub A (2nd seat fills Sub A's capacity of 2)
    act2 = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": device_ids[1], "application_id": app_id},
        headers=owner_headers,
    )
    assert act2.status_code == 201
    assert act2.json()["subscription_id"] == sub_a_id

    # 9. Activate Terminal 3: Sub A is full (2/2). Should automatically roll over to Sub B (FIFO next available)
    act3 = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": device_ids[2], "application_id": app_id},
        headers=owner_headers,
    )
    assert act3.status_code == 201
    assert act3.json()["subscription_id"] == sub_b_id

    # 10. Verify allocation history ledger in database
    stmt_allocs = (
        select(DeviceLicenseAllocation)
        .where(DeviceLicenseAllocation.device_license_id == UUID(lic1_id))
        .order_by(DeviceLicenseAllocation.allocated_at.asc())
    )
    allocs = (await db_session.execute(stmt_allocs)).scalars().all()
    assert len(allocs) == 1
    assert allocs[0].subscription_id == UUID(sub_a_id)
    assert allocs[0].allocation_status == AllocationStatus.ACTIVE
    assert allocs[0].released_at is None

    # 11. Test Device Revocation releases seat and updates allocation history
    revoke_res = await client.post(
        f"/api/v1/devices/{device_ids[0]}/revoke",
        headers=owner_headers,
    )
    assert revoke_res.status_code == 200

    # Verify allocation record marked RELEASED with reason DEVICE_REVOKED
    await db_session.refresh(allocs[0])
    assert allocs[0].allocation_status == AllocationStatus.RELEASED
    assert allocs[0].released_at is not None
    assert allocs[0].release_reason == AllocationReleaseReason.DEVICE_REVOKED
