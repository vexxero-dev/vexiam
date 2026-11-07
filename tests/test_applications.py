import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_application_access_lifecycle(client: AsyncClient):
    # 1. Register Owner and Cashier
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "owner2@bbcafe.com", "password": "Password123!", "first_name": "Bob", "last_name": "Owner"},
    )
    assert owner_reg.status_code == 201
    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner2@bbcafe.com", "password": "Password123!"},
    )
    owner_token = owner_login.json()["access_token"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    cashier_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "cashier2@bbcafe.com", "password": "Password123!", "first_name": "Charlie", "last_name": "Cash"},
    )
    assert cashier_reg.status_code == 201
    cashier_id = cashier_reg.json()["id"]

    cashier_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "cashier2@bbcafe.com", "password": "Password123!"},
    )
    cashier_token = cashier_login.json()["access_token"]
    cashier_headers = {"Authorization": f"Bearer {cashier_token}"}

    # 2. Create Organization
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Downtown Cafe"},
        headers=owner_headers,
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 3. Invite Cashier to Organization & Accept
    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "cashier2@bbcafe.com", "role": "MEMBER"},
        headers=owner_headers,
    )
    invitation_token = invite_res.json()["invitation_token"]

    accept_res = await client.post(
        f"/api/v1/organizations/invitations/{invitation_token}/accept",
        headers=cashier_headers,
    )
    assert accept_res.status_code == 200

    # 4. Register VEX-POS Application
    app_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-POS",
            "name": "Vexxero Point of Sale",
            "type": "LOCAL_HYBRID",
        },
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 5. Define Permissions for VEX-POS
    perm1_res = await client.post(
        f"/api/v1/applications/{app_id}/permissions",
        json={"code": "pos:order:create", "name": "Create POS Orders"},
    )
    assert perm1_res.status_code == 201
    perm1_id = perm1_res.json()["id"]

    perm2_res = await client.post(
        f"/api/v1/applications/{app_id}/permissions",
        json={"code": "pos:discount:approve", "name": "Approve High-Value Discounts"},
    )
    assert perm2_res.status_code == 201
    perm2_id = perm2_res.json()["id"]

    # 6. Define Roles for VEX-POS
    role_res = await client.post(
        f"/api/v1/applications/{app_id}/roles",
        json={
            "code": "CASHIER",
            "name": "POS Cashier",
            "permission_ids": [perm1_id],  # Can create orders, cannot approve discounts
        },
    )
    assert role_res.status_code == 201
    role_id = role_res.json()["id"]

    # 7. Check PDP before assignment: Access should be denied
    pdp_before = await client.post(
        "/api/v1/access/evaluate",
        json={
            "organization_id": org_id,
            "user_id": cashier_id,
            "application_code": "VEX-POS",
            "required_permission": "pos:order:create",
        },
    )
    assert pdp_before.status_code == 200
    assert pdp_before.json()["authorized"] is False

    # 8. Assign VEX-POS and CASHIER role to Cashier
    assign_res = await client.post(
        f"/api/v1/organizations/{org_id}/assignments",
        json={
            "user_id": cashier_id,
            "application_id": app_id,
            "role_ids": [role_id],
        },
        headers=owner_headers,
    )
    assert assign_res.status_code == 201

    # 9. Evaluate Access via PDP:
    # A. Can create order -> True
    pdp_order = await client.post(
        "/api/v1/access/evaluate",
        json={
            "organization_id": org_id,
            "user_id": cashier_id,
            "application_code": "VEX-POS",
            "required_permission": "pos:order:create",
        },
    )
    assert pdp_order.status_code == 200
    assert pdp_order.json()["authorized"] is True
    assert "CASHIER" in pdp_order.json()["roles"]
    assert "pos:order:create" in pdp_order.json()["permissions"]

    # B. Can approve high-value discounts -> False
    pdp_discount = await client.post(
        "/api/v1/access/evaluate",
        json={
            "organization_id": org_id,
            "user_id": cashier_id,
            "application_code": "VEX-POS",
            "required_permission": "pos:discount:approve",
        },
    )
    assert pdp_discount.status_code == 200
    assert pdp_discount.json()["authorized"] is False
    assert "Missing required permission" in pdp_discount.json()["reason"]
