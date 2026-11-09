import pytest
import rfc8785
import base64
from httpx import AsyncClient
from sqlalchemy import select
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

from app.core.security import verify_payload_signature
from app.core.seeds import seed_vexxero_defaults
from app.domains.applications.models import Application, ApplicationRole, Permission


@pytest.mark.asyncio
async def test_identity_sync_engine_lifecycle(client: AsyncClient, db_session):
    await seed_vexxero_defaults(db_session)

    # 1. Register Owner & Org
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "boss@syncpos.com", "password": "Password123!", "first_name": "Boss", "last_name": "Man"},
    )
    assert owner_reg.status_code == 201
    owner_id = owner_reg.json()["id"]

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "boss@syncpos.com", "password": "Password123!"},
    )
    owner_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Verify email
    from app.core.security import create_email_verification_token
    token = create_email_verification_token(owner_id, "boss@syncpos.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    # Create Organization
    org_res = await client.post("/api/v1/organizations", json={"name": "Sync Café Pvt Ltd"}, headers=headers)
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 2. Get VEX-POS app ID
    app_res = await client.get("/api/v1/applications")
    pos_apps = [a for a in app_res.json() if a["code"] == "VEX-POS"]
    assert len(pos_apps) > 0
    pos_app_id = pos_apps[0]["id"]

    # 3. Create Subscription for VEX-POS (Starter plan)
    from app.core.config import settings
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    plans_res = await client.get("/api/v1/plans")
    starter_plan = [p for p in plans_res.json() if p["code"] == "POS-STARTER"][0]

    sub_res = await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": starter_plan["id"], "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )
    assert sub_res.status_code == 201

    # 4. Register Cashier user & invite to org
    cashier_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "kamal@syncpos.com", "password": "Password123!", "first_name": "Kamal", "last_name": "Perera"},
    )
    cashier_id = cashier_reg.json()["id"]

    invite_res = await client.post(
        f"/api/v1/organizations/{org_id}/invitations",
        json={"email": "kamal@syncpos.com", "role": "MEMBER"},
        headers=headers,
    )
    invite_token = invite_res.json()["invitation_token"]

    cashier_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "kamal@syncpos.com", "password": "Password123!"},
    )
    cashier_token = cashier_login.json()["access_token"]
    await client.post(
        f"/api/v1/organizations/invitations/{invite_token}/accept",
        headers={"Authorization": f"Bearer {cashier_token}"},
    )

    # 5. Assign Kamal to VEX-POS with CASHIER role
    roles_res = await client.get(f"/api/v1/applications/{pos_app_id}/roles")
    cashier_role = [r for r in roles_res.json() if r["code"] == "CASHIER"][0]

    assign_res = await client.post(
        f"/api/v1/organizations/{org_id}/assignments",
        json={
            "user_id": cashier_id,
            "application_id": pos_app_id,
            "role_ids": [cashier_role["id"]],
        },
        headers=headers,
    )
    assert assign_res.status_code == 201

    # 6. Test GET /identity/sync/bootstrap
    boot_res = await client.get(
        "/api/v1/identity/sync/bootstrap",
        params={"organization_id": org_id, "application_id": pos_app_id},
    )
    assert boot_res.status_code == 200
    boot_payload = boot_res.json()

    # Validate signature on envelope
    sig = boot_payload.pop("signature")
    canonical_bytes = rfc8785.dumps(boot_payload)
    assert verify_payload_signature(canonical_bytes, sig) is True

    boot_data = boot_payload["data"]
    assert boot_payload["audience"] == "VEX-POS"
    assert boot_payload["organization_id"] == org_id
    assert boot_payload["application_id"] == pos_app_id
    assert len(boot_data["users"]) == 1
    assert boot_data["users"][0]["email"] == "kamal@syncpos.com"
    assert boot_data["users"][0]["display_name"] == "Kamal Perera"
    assert len(boot_data["roles"]) >= 3
    assert len(boot_data["permissions"]) >= 14
    assert len(boot_data["assignments"]) == 1
    assert "CASHIER" in boot_data["assignments"][0]["roles"]
    latest_seq = boot_data["latest_sequence"]
    assert latest_seq >= 1

    # 7. Test GET /identity/sync/changes (after_sequence = 0 should return the assignment event)
    changes_res = await client.get(
        "/api/v1/identity/sync/changes",
        params={
            "organization_id": org_id,
            "application_id": pos_app_id,
            "after_sequence": 0,
        },
    )
    assert changes_res.status_code == 200
    changes_payload = changes_res.json()
    changes_sig = changes_payload.pop("signature")
    assert verify_payload_signature(rfc8785.dumps(changes_payload), changes_sig) is True

    changes_data = changes_payload["data"]
    assert len(changes_data["changes"]) >= 2
    event_types = [c["event_type"] for c in changes_data["changes"]]
    assert "MEMBERSHIP_CREATED" in event_types
    assert "APPLICATION_ASSIGNED" in event_types

    assign_event = [c for c in changes_data["changes"] if c["event_type"] == "APPLICATION_ASSIGNED"][0]
    assert assign_event["payload"]["user_id"] == cashier_id

    # 8. Test POST /identity/sync/acknowledge
    ack_res = await client.post(
        "/api/v1/identity/sync/acknowledge",
        json={
            "organization_id": org_id,
            "application_id": pos_app_id,
            "acknowledged_sequence": latest_seq,
        },
    )
    assert ack_res.status_code == 200
    assert ack_res.json()["last_acknowledged_sequence"] == latest_seq

    # 9. Register a device to the organization
    chal_res = await client.post("/api/v1/devices/challenge")
    chal = chal_res.json()

    dev_priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = dev_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    device_fingerprint = "hw-fp-test-12345"

    challenge_payload = {
        "challenge_id": chal["challenge_id"],
        "device_id": device_fingerprint,
        "nonce": chal["nonce"],
        "organization_id": org_id,
    }
    canonical_bytes = rfc8785.dumps(challenge_payload)
    pop_sig = base64.b64encode(dev_priv.sign(canonical_bytes)).decode("utf-8")

    dev_reg_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "POS Terminal 01",
            "fingerprint": device_fingerprint,
            "public_key": pub_b64,
            "challenge_id": chal["challenge_id"],
            "signature_b64": pop_sig,
        },
        headers=headers,
    )
    assert dev_reg_res.status_code == 201
    device_id = dev_reg_res.json()["id"]

    # 10. Test POST /identity/sync/leases/issue (Section 11: Offline Authorization Lease)
    lease_res = await client.post(
        "/api/v1/identity/sync/leases/issue",
        json={
            "organization_id": org_id,
            "application_id": pos_app_id,
            "device_id": device_id,
        },
    )
    assert lease_res.status_code == 200
    lease = lease_res.json()

    lease_sig = lease.pop("signature")
    assert verify_payload_signature(rfc8785.dumps(lease), lease_sig) is True
    assert lease["issuer"] == "VEX_IAM"
    assert lease["audience"] == "VEX-POS"
    assert lease["organization_id"] == org_id
    assert lease["application_id"] == pos_app_id
    assert lease["device_id"] == device_id
    assert "offline_until" in lease
    assert lease["authorization_version"] >= 1
