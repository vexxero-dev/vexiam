import pytest
import uuid
import base64
import rfc8785
from httpx import AsyncClient
from sqlalchemy import select
from cryptography.hazmat.primitives.asymmetric import ed25519
from app.core.security import create_email_verification_token
from app.core.seeds import seed_vexxero_defaults
from app.domains.identity.sync_models import SyncEventType, IdentitySyncEvent
from app.domains.licensing.models import Device, DeviceLicense, DeviceStatus, LicenseStatus


async def create_verified_user_and_token(client: AsyncClient, email: str, first_name: str, last_name: str):
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "first_name": first_name, "last_name": last_name},
    )
    assert reg.status_code == 201
    user_id = reg.json()["id"]

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "Password123!"},
    )
    token = login.json()["access_token"]

    vtoken = create_email_verification_token(user_id, email)
    await client.post("/api/v1/auth/verify-email", json={"token": vtoken})

    return user_id, token


def generate_device_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    pub = priv.public_key()
    pub_bytes = pub.public_bytes_raw()
    pub_b64 = base64.b64encode(pub_bytes).decode("utf-8")
    return priv, pub_b64


@pytest.mark.asyncio
async def test_device_registration_org_level_and_location_scoped(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # 1. Setup Org & Owner
    owner_id, owner_token = await create_verified_user_and_token(
        client, "owner_dev@apex.com", "Dev", "Owner"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Device Retail Org"}, headers=headers)
    org_id = org_res.json()["id"]

    # 2. Register Device at Organization Level (location_id = None)
    _, pub_b64_1 = generate_device_keypair()
    reg_org_dev = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Org Level Terminal 01",
            "fingerprint": "hw-fingerprint-0001",
            "public_key": pub_b64_1,
        },
        headers=headers,
    )
    assert reg_org_dev.status_code == 201
    org_dev = reg_org_dev.json()
    assert org_dev["location_id"] is None
    assert org_dev["status"] == "ACTIVE"

    # 3. Create an active Location
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "LOC-STORE-01", "name": "Downtown Store"},
        headers=headers,
    )
    assert loc_res.status_code == 201
    loc_id = loc_res.json()["id"]

    # 4. Register Device Scoped to Location
    _, pub_b64_2 = generate_device_keypair()
    reg_loc_dev = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "location_id": loc_id,
            "name": "Cashier Counter 01",
            "fingerprint": "hw-fingerprint-0002",
            "public_key": pub_b64_2,
        },
        headers=headers,
    )
    assert reg_loc_dev.status_code == 201
    loc_dev = reg_loc_dev.json()
    assert loc_dev["location_id"] == loc_id


@pytest.mark.asyncio
async def test_cross_tenant_location_registration_rejection(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # Org 1
    owner1_id, owner1_token = await create_verified_user_and_token(
        client, "owner_org1@apex.com", "Owner", "One"
    )
    headers1 = {"Authorization": f"Bearer {owner1_token}"}
    org1_res = await client.post("/api/v1/organizations", json={"name": "Org 1 Corp"}, headers=headers1)
    org1_id = org1_res.json()["id"]

    # Org 2
    owner2_id, owner2_token = await create_verified_user_and_token(
        client, "owner_org2@other.com", "Owner", "Two"
    )
    headers2 = {"Authorization": f"Bearer {owner2_token}"}
    org2_res = await client.post("/api/v1/organizations", json={"name": "Org 2 Corp"}, headers=headers2)
    org2_id = org2_res.json()["id"]

    # Create Location in Org 2
    loc_org2_res = await client.post(
        f"/api/v1/organizations/{org2_id}/locations",
        json={"code": "ORG2-STORE", "name": "Org 2 Location"},
        headers=headers2,
    )
    loc_org2_id = loc_org2_res.json()["id"]

    # Attempt to register device for Org 1 pointing to Org 2's location
    _, pub_b64 = generate_device_keypair()
    reg_cross = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org1_id,
            "location_id": loc_org2_id,
            "name": "Cross Tenant Device",
            "fingerprint": "hw-fingerprint-cross",
            "public_key": pub_b64,
        },
        headers=headers1,
    )
    assert reg_cross.status_code == 400
    assert "not found in this organization" in reg_cross.json()["detail"]


@pytest.mark.asyncio
async def test_device_reassignment_application_activation_and_license_revocation(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # 1. Setup Org & Subscription
    owner_id, owner_token = await create_verified_user_and_token(
        client, "reassign_owner@apex.com", "Reassign", "Owner"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Reassignment Retail"}, headers=headers)
    org_id = org_res.json()["id"]

    app_res = await client.get("/api/v1/applications")
    pos_id = [a["id"] for a in app_res.json() if a["code"] == "VEX-POS"][0]

    plans_res = await client.get("/api/v1/plans")
    pos_plan = [p for p in plans_res.json() if p["application_id"] == pos_id][0]

    from app.core.config import settings
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}
    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": pos_plan["id"], "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )

    # 2. Create Location A (POS active) and Location B (POS inactive)
    loc_a = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "LOC-A", "name": "Location A (POS active)"},
        headers=headers,
    )
    loc_a_id = loc_a.json()["id"]
    await client.post(f"/api/v1/locations/{loc_a_id}/applications", json={"application_id": pos_id}, headers=headers)

    loc_b = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "LOC-B", "name": "Location B (No POS)"},
        headers=headers,
    )
    loc_b_id = loc_b.json()["id"]

    # 3. Register device at Location A and activate a POS license
    _, pub_b64 = generate_device_keypair()
    dev_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "location_id": loc_a_id,
            "name": "POS Terminal 01",
            "fingerprint": "hw-pos-term-01",
            "public_key": pub_b64,
        },
        headers=headers,
    )
    dev_id = dev_res.json()["id"]

    lic_res = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": dev_id, "application_id": pos_id},
        headers=headers,
    )
    assert lic_res.status_code == 201
    assert lic_res.json()["status"] == "ACTIVE"

    # 4. Attempt reassignment to Location B (fails because Location B lacks active VEX-POS)
    reassign_fail = await client.post(
        f"/api/v1/devices/{dev_id}/reassign",
        json={"target_location_id": loc_b_id},
        headers=headers,
    )
    assert reassign_fail.status_code == 409
    assert "Target location lacks active enablement" in reassign_fail.json()["detail"]

    # 5. Enable VEX-POS on Location B
    await client.post(f"/api/v1/locations/{loc_b_id}/applications", json={"application_id": pos_id}, headers=headers)

    # 6. Reassignment to Location B now succeeds and revokes active license
    reassign_ok = await client.post(
        f"/api/v1/devices/{dev_id}/reassign",
        json={"target_location_id": loc_b_id},
        headers=headers,
    )
    assert reassign_ok.status_code == 200
    reassign_data = reassign_ok.json()
    assert reassign_data["new_location_id"] == loc_b_id
    assert reassign_data["revoked_licenses_count"] == 1

    # 7. Check database: license is REVOKED
    stmt_lic = select(DeviceLicense).where(DeviceLicense.device_id == uuid.UUID(dev_id))
    lic_rows = list((await db_session.execute(stmt_lic)).scalars().all())
    assert len(lic_rows) == 1
    assert lic_rows[0].status == LicenseStatus.REVOKED

    # 8. Check sync event emitted
    stmt_sync = select(IdentitySyncEvent).where(
        IdentitySyncEvent.organization_id == uuid.UUID(org_id),
        IdentitySyncEvent.event_type == SyncEventType.DEVICE_LOCATION_REASSIGNED,
    )
    sync_event = (await db_session.execute(stmt_sync)).scalar_one_or_none()
    assert sync_event is not None
    assert sync_event.payload["new_location_id"] == loc_b_id

    # 9. Idempotency test: repeating the reassignment to Location B is a no-op
    reassign_idempotent = await client.post(
        f"/api/v1/devices/{dev_id}/reassign",
        json={"target_location_id": loc_b_id},
        headers=headers,
    )
    assert reassign_idempotent.status_code == 200
    assert reassign_idempotent.json()["revoked_licenses_count"] == 0
    assert "already assigned" in reassign_idempotent.json()["message"]


@pytest.mark.asyncio
async def test_explicit_unassignment_and_archival_guard(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    owner_id, owner_token = await create_verified_user_and_token(
        client, "unassign_owner@apex.com", "Unassign", "Owner"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Unassign Retail Org"}, headers=headers)
    org_id = org_res.json()["id"]

    # Create Location
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "STORE-GUARD", "name": "Guarded Store"},
        headers=headers,
    )
    loc_id = loc_res.json()["id"]

    # Register device assigned to location
    _, pub_b64 = generate_device_keypair()
    dev_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "location_id": loc_id,
            "name": "Bound Terminal",
            "fingerprint": "hw-bound-01",
            "public_key": pub_b64,
        },
        headers=headers,
    )
    dev_id = dev_res.json()["id"]

    # 1. Attempt to archive location while device is assigned -> BLOCKED (409 Conflict)
    archive_fail = await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)
    assert archive_fail.status_code == 409
    assert "registered devices" in archive_fail.json()["detail"]

    # 2. Explicit Unassignment: send target_location_id = None
    unassign_res = await client.post(
        f"/api/v1/devices/{dev_id}/reassign",
        json={"target_location_id": None},
        headers=headers,
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["new_location_id"] is None

    # 3. Now that no active devices remain at location, archive succeeds
    archive_ok = await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)
    assert archive_ok.status_code == 200
    assert archive_ok.json()["status"] == "ARCHIVED"


@pytest.mark.asyncio
async def test_location_device_listing_restricted_to_admin(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # Owner & Org
    owner_id, owner_token = await create_verified_user_and_token(
        client, "list_owner@apex.com", "List", "Owner"
    )
    headers_owner = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Listing Org"}, headers=headers_owner)
    org_id = org_res.json()["id"]

    # Create location & device
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "STORE-LIST", "name": "Listing Store"},
        headers=headers_owner,
    )
    loc_id = loc_res.json()["id"]

    _, pub_b64 = generate_device_keypair()
    await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "location_id": loc_id,
            "name": "Listable Device",
            "fingerprint": "hw-list-01",
            "public_key": pub_b64,
        },
        headers=headers_owner,
    )

    # Member user in same org
    member_id, member_token = await create_verified_user_and_token(
        client, "list_member@apex.com", "Member", "User"
    )
    headers_member = {"Authorization": f"Bearer {member_token}"}

    inv = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "list_member@apex.com", "role": "MEMBER"},
        headers=headers_owner,
    )
    inv_token = inv.json()["invitation_token"]
    await client.post(f"/api/v1/organizations/invitations/{inv_token}/accept", headers=headers_member)

    # Non-admin member cannot list devices at location (403 Forbidden)
    list_forbidden = await client.get(f"/api/v1/locations/{loc_id}/devices", headers=headers_member)
    assert list_forbidden.status_code == 403

    # Admin/Owner lists devices successfully
    list_ok = await client.get(f"/api/v1/locations/{loc_id}/devices", headers=headers_owner)
    assert list_ok.status_code == 200
    devices = list_ok.json()
    assert len(devices) == 1
    assert devices[0]["fingerprint"] == "hw-list-01"
