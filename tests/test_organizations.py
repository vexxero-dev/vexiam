import pytest
from httpx import AsyncClient
from app.core.security import create_email_verification_token


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

    # Verify Alice's email
    emp_verify_token = create_email_verification_token(emp_id, "alice@bbcafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": emp_verify_token})

    # 3. Security Boundary: Unverified owner cannot create an organization
    unverified_org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "B & B Cafe", "registration_number": "REG-12345"},
        headers=owner_headers,
    )
    assert unverified_org_res.status_code == 403
    assert "email address must be verified" in unverified_org_res.json()["detail"].lower()

    # Now verify Owner's email
    owner_verify_token = create_email_verification_token(owner_id, "owner@bbcafe.com")
    verify_res = await client.post("/api/v1/auth/verify-email", json={"token": owner_verify_token})
    assert verify_res.status_code == 200

    # 4. Create Business Entity (B & B Cafe) with verified owner
    create_org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "B & B Cafe", "registration_number": "REG-12345"},
        headers=owner_headers,
    )
    assert create_org_res.status_code == 201
    org = create_org_res.json()
    org_id = org["id"]
    assert org["name"] == "B & B Cafe"

    # 5. Check Owner Membership is automatically OWNER
    members_res = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=owner_headers,
    )
    assert members_res.status_code == 200
    members = members_res.json()
    assert len(members) == 1
    assert members[0]["user_id"] == owner_id
    assert members[0]["role"] == "OWNER"

    # 6. Enforce Single-Owner Invariant: Inviting someone as OWNER must be rejected
    invalid_owner_invite = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "alice@bbcafe.com", "role": "OWNER"},
        headers=owner_headers,
    )
    assert invalid_owner_invite.status_code in [400, 422]

    # 7. Invite Alice as MEMBER
    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "alice@bbcafe.com", "role": "MEMBER"},
        headers=owner_headers,
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    raw_token = invite_data["invitation_token"]
    assert raw_token is not None

    # 8. Alice Accepts Invitation
    accept_res = await client.post(
        f"/api/v1/organizations/invitations/{raw_token}/accept",
        headers=emp_headers,
    )
    assert accept_res.status_code == 200
    membership = accept_res.json()
    assert membership["organization_id"] == org_id
    assert membership["user_id"] == emp_id
    assert membership["role"] == "MEMBER"

    # 9. Accepting again or when already a member MUST fail cleanly with 400
    duplicate_accept = await client.post(
        f"/api/v1/organizations/invitations/{raw_token}/accept",
        headers=emp_headers,
    )
    assert duplicate_accept.status_code in [400, 404]

    # 10. Verify Organization Member list now has 2 members
    updated_members_res = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=owner_headers,
    )
    assert updated_members_res.status_code == 200
    updated_members = updated_members_res.json()
    assert len(updated_members) == 2

    # 11. Transfer Ownership from Bob to Alice
    transfer_res = await client.post(
        f"/api/v1/organizations/{org_id}/transfer-ownership",
        json={"new_owner_user_id": emp_id},
        headers=owner_headers,
    )
    assert transfer_res.status_code == 200

    # 12. Verify Roles updated: Alice is now OWNER, Bob is ADMIN
    post_transfer_members = await client.get(
        f"/api/v1/organizations/{org_id}/members",
        headers=emp_headers,
    )
    roles_map = {m["user_id"]: m["role"] for m in post_transfer_members.json()}
    assert roles_map[emp_id] == "OWNER"
    assert roles_map[owner_id] == "ADMIN"

    # 13. Verify GET /organizations returns authoritative role and permissions
    bob_orgs_res = await client.get("/api/v1/organizations", headers=owner_headers)
    assert bob_orgs_res.status_code == 200
    bob_org = [o for o in bob_orgs_res.json() if o["id"] == org_id][0]
    assert bob_org["role"] == "ADMIN"
    assert "pos.device.activate" in bob_org["permissions"]

    # 14. Verify server-side permission filtering
    filtered_orgs = await client.get("/api/v1/organizations?permission=pos.device.activate", headers=owner_headers)
    assert filtered_orgs.status_code == 200
    assert any(o["id"] == org_id for o in filtered_orgs.json())

    unmatched_orgs = await client.get("/api/v1/organizations?permission=nonexistent.permission", headers=owner_headers)
    assert unmatched_orgs.status_code == 200
    assert not any(o["id"] == org_id for o in unmatched_orgs.json())


@pytest.mark.asyncio
async def test_delete_organization_subscription_guard(client: AsyncClient, db_session):
    import uuid
    from app.domains.applications.models import Application
    from app.domains.subscriptions.models import Plan, Subscription, OwnerType, SubscriptionStatus

    # 1. Register & Verify Owner
    email = "delowner@example.com"
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "Password123!", "first_name": "Del", "last_name": "Owner"},
    )
    login_res = await client.post("/api/v1/auth/login", json={"email": email, "password": "Password123!"})
    user_id = login_res.json()["user"]["id"]
    headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}
    verify_token = create_email_verification_token(user_id, email)
    await client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    # 2. Create two organizations
    org1_res = await client.post("/api/v1/organizations", json={"name": "Deletable Org"}, headers=headers)
    assert org1_res.status_code == 201
    org1_id = org1_res.json()["id"]

    org2_res = await client.post("/api/v1/organizations", json={"name": "Subscribed Org"}, headers=headers)
    assert org2_res.status_code == 201
    org2_id = org2_res.json()["id"]

    # 3. Create an Application, Plan, and an ACTIVE Subscription for org2, and a CANCELED one for org1
    app = Application(code=f"app-{uuid.uuid4().hex[:6]}", name="Test App")
    db_session.add(app)
    await db_session.flush()

    plan = Plan(application_id=app.id, code=f"plan-{uuid.uuid4().hex[:6]}", name="Pro Plan")
    db_session.add(plan)
    await db_session.flush()

    sub_canceled = Subscription(
        plan_id=plan.id,
        owner_type=OwnerType.ORGANIZATION,
        organization_id=uuid.UUID(org1_id),
        status=SubscriptionStatus.CANCELED,
    )
    sub_active = Subscription(
        plan_id=plan.id,
        owner_type=OwnerType.ORGANIZATION,
        organization_id=uuid.UUID(org2_id),
        status=SubscriptionStatus.ACTIVE,
    )
    db_session.add_all([sub_canceled, sub_active])
    await db_session.commit()

    # 4. Deleting org2 (with ACTIVE subscription) must fail with 409 Conflict
    del_org2 = await client.delete(f"/api/v1/organizations/{org2_id}", headers=headers)
    assert del_org2.status_code == 409

    # 5. Deleting org1 (only CANCELED subscription) must succeed with 204 No Content
    del_org1 = await client.delete(f"/api/v1/organizations/{org1_id}", headers=headers)
    assert del_org1.status_code == 204

    # 6. Verify org1 no longer appears in GET /organizations, while org2 still does
    orgs_res = await client.get("/api/v1/organizations", headers=headers)
    assert orgs_res.status_code == 200
    org_ids = [o["id"] for o in orgs_res.json()]
    assert org1_id not in org_ids
    assert org2_id in org_ids
