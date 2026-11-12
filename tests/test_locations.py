import pytest
import uuid
from httpx import AsyncClient
from app.core.security import create_email_verification_token
from app.core.seeds import seed_vexxero_defaults
from app.domains.identity.sync_models import SyncEventType, IdentitySyncEvent
from sqlalchemy import select


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


@pytest.mark.asyncio
async def test_location_domain_and_tenant_isolation(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # 1. Create two separate organizations with their owners
    owner1_id, owner1_token = await create_verified_user_and_token(
        client, "owner1@apex.com", "Owner", "One"
    )
    headers1 = {"Authorization": f"Bearer {owner1_token}"}

    owner2_id, owner2_token = await create_verified_user_and_token(
        client, "owner2@othercorp.com", "Owner", "Two"
    )
    headers2 = {"Authorization": f"Bearer {owner2_token}"}

    org1_res = await client.post("/api/v1/organizations", json={"name": "Apex Group"}, headers=headers1)
    assert org1_res.status_code == 201
    org1_id = org1_res.json()["id"]

    org2_res = await client.post("/api/v1/organizations", json={"name": "Other Corp"}, headers=headers2)
    assert org2_res.status_code == 201
    org2_id = org2_res.json()["id"]

    # 2. Org 1 creates location
    loc_payload = {
        "code": "COL-01",
        "name": "Colombo Flagship",
        "description": "Main retail showroom",
        "city": "Colombo",
        "country_code": "LKA",
        "timezone": "Asia/Colombo",
        "metadata": {"floors": 3},
    }
    loc1_res = await client.post(f"/api/v1/organizations/{org1_id}/locations", json=loc_payload, headers=headers1)
    assert loc1_res.status_code == 201
    loc1_data = loc1_res.json()
    assert loc1_data["code"] == "COL-01"
    assert loc1_data["name"] == "Colombo Flagship"
    assert loc1_data["status"] == "ACTIVE"
    assert loc1_data["metadata"]["floors"] == 3
    loc1_id = loc1_data["id"]

    # 3. Duplicate code in same org is rejected (409)
    loc_dup_res = await client.post(f"/api/v1/organizations/{org1_id}/locations", json=loc_payload, headers=headers1)
    assert loc_dup_res.status_code == 409

    # 4. Same code in different org is permitted (independent namespaces)
    loc_org2_res = await client.post(f"/api/v1/organizations/{org2_id}/locations", json=loc_payload, headers=headers2)
    assert loc_org2_res.status_code == 201
    assert loc_org2_res.json()["id"] != loc1_id

    # 5. Cross-tenant access: Owner 2 cannot view or update Org 1's location
    view_cross = await client.get(f"/api/v1/locations/{loc1_id}", headers=headers2)
    assert view_cross.status_code == 403

    update_cross = await client.put(
        f"/api/v1/locations/{loc1_id}",
        json={"name": "Hacked Name"},
        headers=headers2,
    )
    assert update_cross.status_code == 403

    # 6. Org 1 member (non-admin) cannot update or create locations
    member_id, member_token = await create_verified_user_and_token(
        client, "staff@apex.com", "Staff", "User"
    )
    member_headers = {"Authorization": f"Bearer {member_token}"}

    # Invite member to org 1
    inv = await client.post(
        f"/api/v1/organizations/{org1_id}/invitations",
        json={"email": "staff@apex.com", "role": "MEMBER"},
        headers=headers1,
    )
    inv_token = inv.json()["invitation_token"]
    await client.post(f"/api/v1/organizations/invitations/{inv_token}/accept", headers=member_headers)

    create_forbidden = await client.post(
        f"/api/v1/organizations/{org1_id}/locations",
        json={"code": "KANDY-01", "name": "Kandy Branch"},
        headers=member_headers,
    )
    assert create_forbidden.status_code == 403

    # But member can read locations of their own org
    list_res = await client.get(f"/api/v1/organizations/{org1_id}/locations", headers=member_headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1


@pytest.mark.asyncio
async def test_location_applications_and_archival_safeguard(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # 1. Setup Org & Owner
    owner_id, owner_token = await create_verified_user_and_token(
        client, "ceo@hospitality.com", "Ceo", "Hotel"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Resort Group"}, headers=headers)
    org_id = org_res.json()["id"]

    # 2. Get App IDs for VEX-POS and VEX-PMS and subscribe org to both
    app_res = await client.get("/api/v1/applications")
    apps = {a["code"]: a["id"] for a in app_res.json()}
    pos_id = apps["VEX-POS"]
    pms_id = apps["VEX-PMS"]

    # Subscribe org to VEX-POS and create/subscribe to a VEX-PMS plan
    plans_res = await client.get("/api/v1/plans")
    pos_plan = [p for p in plans_res.json() if p["application_id"] == pos_id][0]

    from app.core.config import settings
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    # Create PMS plan
    pms_plan_res = await client.post(
        "/api/v1/plans",
        json={
            "application_id": pms_id,
            "code": "PMS-STANDARD",
            "name": "PMS Standard Plan",
            "description": "Standard PMS subscription",
            "user_seats": 10,
            "device_seats": 5,
        },
        headers=admin_headers,
    )
    assert pms_plan_res.status_code == 201
    pms_plan_id = pms_plan_res.json()["id"]

    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": pos_plan["id"], "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )
    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": pms_plan_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )

    # 3. Create Location
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "HOTEL-GALLE", "name": "Galle Fort Hotel & Restaurant"},
        headers=headers,
    )
    loc_id = loc_res.json()["id"]

    # 4. Enable VEX-POS (Restaurant)
    pos_enable = await client.post(
        f"/api/v1/locations/{loc_id}/applications",
        json={"application_id": pos_id},
        headers=headers,
    )
    assert pos_enable.status_code == 201
    assert pos_enable.json()["application_code"] == "VEX-POS"
    assert pos_enable.json()["status"] == "ACTIVE"

    # 5. Enable VEX-PMS (Hotel rooms)
    pms_enable = await client.post(
        f"/api/v1/locations/{loc_id}/applications",
        json={"application_id": pms_id},
        headers=headers,
    )
    assert pms_enable.status_code == 201
    assert pms_enable.json()["application_code"] == "VEX-PMS"

    # 6. Verify location details report both applications
    get_loc = await client.get(f"/api/v1/locations/{loc_id}", headers=headers)
    assert get_loc.status_code == 200
    apps_active = get_loc.json()["applications"]
    assert len(apps_active) == 2
    active_codes = {a["application_code"] for a in apps_active if a["status"] == "ACTIVE"}
    assert active_codes == {"VEX-POS", "VEX-PMS"}

    # 7. Safeguard: Attempting to archive location with active applications is BLOCKED (409 Conflict)
    archive_blocked = await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)
    assert archive_blocked.status_code == 409
    assert "Deactivate applications before archiving" in archive_blocked.json()["detail"]

    # 8. Deactivate applications
    deact_pos = await client.delete(f"/api/v1/locations/{loc_id}/applications/{pos_id}", headers=headers)
    assert deact_pos.status_code == 200
    assert deact_pos.json()["status"] == "DEACTIVATED"

    # Still blocked because PMS is active
    archive_blocked_pms = await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)
    assert archive_blocked_pms.status_code == 409

    deact_pms = await client.delete(f"/api/v1/locations/{loc_id}/applications/{pms_id}", headers=headers)
    assert deact_pms.status_code == 200

    # 9. Now archival succeeds
    archive_ok = await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)
    assert archive_ok.status_code == 200
    assert archive_ok.json()["status"] == "ARCHIVED"

    # 10. Archived location cannot be modified or re-activated
    update_archived = await client.put(
        f"/api/v1/locations/{loc_id}",
        json={"name": "Attempt Update"},
        headers=headers,
    )
    assert update_archived.status_code == 400


@pytest.mark.asyncio
async def test_location_sync_event_outbox_integration(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    owner_id, owner_token = await create_verified_user_and_token(
        client, "syncadmin@apex.com", "Sync", "Admin"
    )
    headers = {"Authorization": f"Bearer {owner_token}"}

    org_res = await client.post("/api/v1/organizations", json={"name": "Sync Org"}, headers=headers)
    org_id = org_res.json()["id"]

    # 1. Create Location
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "SYNC-01", "name": "Sync Warehouse"},
        headers=headers,
    )
    loc_id = loc_res.json()["id"]

    # 2. Update Location
    await client.put(
        f"/api/v1/locations/{loc_id}",
        json={"description": "Updated warehouse description"},
        headers=headers,
    )

    # 3. Enable application (requires active subscription)
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

    await client.post(f"/api/v1/locations/{loc_id}/applications", json={"application_id": pos_id}, headers=headers)

    # 4. Deactivate application
    await client.delete(f"/api/v1/locations/{loc_id}/applications/{pos_id}", headers=headers)

    # 5. Archive location
    await client.post(f"/api/v1/locations/{loc_id}/archive", headers=headers)

    # Query IdentitySyncEvents from database
    org_uuid = uuid.UUID(org_id) if isinstance(org_id, str) else org_id
    stmt = (
        select(IdentitySyncEvent)
        .where(IdentitySyncEvent.organization_id == org_uuid)
        .order_by(IdentitySyncEvent.sequence.asc())
    )
    res = await db_session.execute(stmt)
    events = list(res.scalars().all())

    event_types = [e.event_type for e in events]
    assert SyncEventType.LOCATION_CREATED in event_types
    assert SyncEventType.LOCATION_UPDATED in event_types
    assert SyncEventType.LOCATION_APPLICATION_ACTIVATED in event_types
    assert SyncEventType.LOCATION_APPLICATION_DEACTIVATED in event_types
    assert SyncEventType.LOCATION_ARCHIVED in event_types
