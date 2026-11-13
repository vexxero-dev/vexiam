import pytest
from httpx import AsyncClient
from app.core.security import create_email_verification_token
from app.core.config import settings


@pytest.mark.asyncio
async def test_commercial_seat_aggregation_and_reassignment(client: AsyncClient):
    """
    Test that:
    1. Multiple active plans for the same application aggregate user seats.
    2. Modifying an existing assigned user's roles does not double-count against the user seat quota.
    """
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    # 1. Register and verify Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner_comm@cafe.com", "password": "Password123!", "first_name": "O", "last_name": "Comm"},
    )
    assert owner_reg.status_code == 201
    owner_id = owner_reg.json()["id"]

    token = create_email_verification_token(owner_id, "owner_comm@cafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner_comm@cafe.com", "password": "Password123!"},
    )
    owner_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 2. Create Organization
    org_res = await client.post("/api/v1/organizations", json={"name": "Commercial Test Org"}, headers=owner_headers)
    org_id = org_res.json()["id"]

    # 3. Register Application and Roles
    app_res = await client.post(
        "/api/v1/applications",
        json={"code": "VEX-COMM-APP", "name": "Commercial App", "type": "WEB"},
        headers=admin_headers,
    )
    app_id = app_res.json()["id"]

    role_res = await client.post(
        f"/api/v1/applications/{app_id}/roles",
        json={"code": "GENERAL_STAFF", "name": "General Staff"},
        headers=admin_headers,
    )
    role_id = role_res.json()["id"]

    # 4. Create Plan with 1 user seat and purchase subscription
    plan1_res = await client.post(
        "/api/v1/plans",
        json={"application_id": app_id, "code": "PLAN-SEAT-1", "name": "1 Seat Plan", "user_seats": 1, "device_seats": 0},
        headers=admin_headers,
    )
    plan1_id = plan1_res.json()["id"]

    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": plan1_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )

    # 5. Assign Owner (1/1 seat used)
    assign1 = await client.post(
        f"/api/v1/organizations/{org_id}/assignments",
        json={"user_id": owner_id, "application_id": app_id, "role_ids": [role_id]},
        headers=owner_headers,
    )
    assert assign1.status_code == 201

    # 6. Re-assigning or updating roles for the SAME user MUST NOT fail with quota exceeded
    reassign = await client.post(
        f"/api/v1/organizations/{org_id}/assignments",
        json={"user_id": owner_id, "application_id": app_id, "role_ids": [role_id]},
        headers=owner_headers,
    )
    assert reassign.status_code == 201

    # 7. Add second plan (+2 user seats) -> Total capacity = 3 seats
    plan2_res = await client.post(
        "/api/v1/plans",
        json={"application_id": app_id, "code": "PLAN-SEAT-2", "name": "2 Seat Addon", "user_seats": 2, "device_seats": 0},
        headers=admin_headers,
    )
    plan2_id = plan2_res.json()["id"]

    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": plan2_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )

    # 8. Register Employee 2, invite and accept
    emp2_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "emp2@cafe.com", "password": "Password123!", "first_name": "E2", "last_name": "Cafe"},
    )
    emp2_id = emp2_reg.json()["id"]
    token2 = create_email_verification_token(emp2_id, "emp2@cafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token2})
    login2 = await client.post("/api/v1/auth/login", json={"email": "emp2@cafe.com", "password": "Password123!"})
    headers2 = {"Authorization": f"Bearer {login2.json()['access_token']}"}

    inv = await client.post(f"/api/v1/organizations/{org_id}/invitations", json={"email": "emp2@cafe.com"}, headers=owner_headers)
    await client.post(f"/api/v1/organizations/invitations/{inv.json()['invitation_token']}/accept", headers=headers2)

    # 9. Assign Employee 2 (2/3 seats used) -> succeeds
    assign2 = await client.post(
        f"/api/v1/organizations/{org_id}/assignments",
        json={"user_id": emp2_id, "application_id": app_id, "role_ids": [role_id]},
        headers=owner_headers,
    )
    assert assign2.status_code == 201

    # 10. Authoritative Entitlements Endpoint Verification
    ent_res = await client.get(
        f"/api/v1/licenses/entitlements?organization_id={org_id}&application_code=VEX-COMM-APP",
        headers=owner_headers,
    )
    assert ent_res.status_code == 200
    ent_data = ent_res.json()
    assert ent_data["organization_id"] == org_id
    assert ent_data["application_code"] == "VEX-COMM-APP"
    assert ent_data["status"] == "ACTIVE"
    assert ent_data["max_terminals"] == 0  # plans have device_seats: 0
    assert ent_data["active_terminals"] == 0
    assert ent_data["available_terminals"] == 0
