import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_organization_lifecycle(client: AsyncClient):
    # 1. Register Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "owner@bbcafe.com",
            "password": "Password123!",
            "first_name": "Bob",
            "last_name": "Builder",
        },
    )
    assert owner_reg.status_code == 201
    owner_token_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "owner@bbcafe.com", "password": "Password123!"},
    )
    owner_token = owner_token_res.json()["access_token"]
    owner_id = owner_token_res.json()["user"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Register Employee (Global individual identity)
    emp_reg = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "alice@bbcafe.com",
            "password": "Password123!",
            "first_name": "Alice",
            "last_name": "Wonder",
        },
    )
    assert emp_reg.status_code == 201
    emp_token_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "alice@bbcafe.com", "password": "Password123!"},
    )
    emp_token = emp_token_res.json()["access_token"]
    emp_id = emp_token_res.json()["user"]["id"]
    emp_headers = {"Authorization": f"Bearer {emp_token}"}

    # 3. Create Business Entity (B & B Cafe)
    create_org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "B & B Cafe", "registration_number": "REG-12345"},
        headers=owner_headers,
    )
    assert create_org_res.status_code == 201
    org = create_org_res.json()
    org_id = org["id"]
    assert org["name"] == "B & B Cafe"

    # 4. Check Owner Membership is automatically OWNER
    members_res = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=owner_headers,
    )
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == owner_id
    assert members[0]["role"] == "OWNER"

    # 5. Invite Alice as MEMBER
    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "alice@bbcafe.com", "role": "MEMBER"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    raw_token = invite_data["invitation_token"]
    assert raw_token is not None

    # 6. Alice Accepts Invitation
    accept_res = await client.post(
        f"/api/v1/organizations/invitations/{raw_token}/accept",
        headers=emp_headers,
    )
    assert accept_res.status_code == 200
    membership = accept_res.json()
    assert membership["organization_id"] == org_id
    assert membership["user_id"] == emp_id
    assert membership["role"] == "MEMBER"

    # 7. Verify Organization Member list now has 2 members
    updated_members_res = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=owner_headers,
    )
    assert updated_members_res.status_code == 200
    updated_members = updated_members_res.json()
    assert len(updated_members) == 2

    # 8. Transfer Ownership from Bob to Alice
    transfer_res = await client.post(
        f"/api/v1/organizations/{org_id}/transfer-ownership",
        json={"new_owner_user_id": emp_id},
        headers=owner_headers,
    )
    assert transfer_res.status_code == 200

    # 9. Verify Roles updated: Alice is now OWNER, Bob is ADMIN
    post_transfer_members = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=emp_headers,
    )
    roles_map = {m["user_id"]: m["role"] for m in post_transfer_members.json()}
    assert roles_map[emp_id] == "OWNER"
    assert roles_map[owner_id] == "ADMIN"
