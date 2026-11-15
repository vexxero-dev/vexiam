import pytest
import base64
import rfc8785
from httpx import AsyncClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.core.security import create_email_verification_token
from app.core.config import settings
from app.domains.licensing.service import _public_key


@pytest.mark.asyncio
async def test_pos_sync_activation_flow(client: AsyncClient):
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    # 1. Register & verify Organization Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "sync_owner@cafe.com", "password": "Password123!", "first_name": "Sync", "last_name": "Owner"},
    )
    assert owner_reg.status_code == 201
    owner_id = owner_reg.json()["id"]

    token = create_email_verification_token(owner_id, "sync_owner@cafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "sync_owner@cafe.com", "password": "Password123!"},
    )
    owner_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 2. Create Organization
    org_res = await client.post("/api/v1/organizations", json={"name": "Sync Ready Cafe"}, headers=owner_headers)
    org_id = org_res.json()["id"]

    # 3. Create Location (Store)
    loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "STORE-001", "name": "Downtown Store"},
        headers=owner_headers,
    )
    assert loc_res.status_code == 201
    loc_id = loc_res.json()["id"]

    # 4. Create App with code 'VEX-POS'
    app_res = await client.post(
        "/api/v1/applications",
        json={"code": "VEX-POS", "name": "VEX Point of Sale", "type": "LOCAL_HYBRID"},
        headers=admin_headers,
    )
    app_id = app_res.json()["id"]

    # Create plan and subscription
    plan_res = await client.post(
        "/api/v1/plans",
        json={"application_id": app_id, "code": "POS-SYNC-PLAN", "name": "POS Sync Plan", "user_seats": 5, "device_seats": 5},
        headers=admin_headers,
    )
    plan_id = plan_res.json()["id"]

    sub_res = await client.post(
        "/api/v1/subscriptions",
        json={"organization_id": org_id, "plan_id": plan_id, "owner_type": "ORGANIZATION"},
        headers=admin_headers,
    )
    assert sub_res.status_code == 201

    # 5. Generate Terminal Ed25519 Keypair
    dev_priv_key = ed25519.Ed25519PrivateKey.generate()
    dev_pub_key = dev_priv_key.public_key()
    dev_pub_bytes = dev_pub_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    dev_pub_b64 = base64.b64encode(dev_pub_bytes).decode("utf-8")
    terminal_fingerprint = "hw-fingerprint-term-001"

    # 6. Register Device in IAM assigned to Downtown Store
    dev_reg_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "location_id": loc_id,
            "name": "Register 1",
            "fingerprint": terminal_fingerprint,
            "public_key": dev_pub_b64,
        },
        headers=owner_headers,
    )
    assert dev_reg_res.status_code == 201
    device_id = dev_reg_res.json()["id"]

    # 7. Check Internal Verify endpoint returns location_id
    verify_res = await client.get(
        f"/api/v1/devices/internal/verify?organization_id={org_id}&terminal_identifier={terminal_fingerprint}",
        headers=admin_headers,
    )
    assert verify_res.status_code == 200
    vdata = verify_res.json()
    assert vdata["device_id"] == device_id
    assert vdata["location_id"] == loc_id
    assert vdata["is_valid"] is True
    assert vdata["sync_entitled"] is True

    # 8. Request Challenge for Proof of Possession before Sync Activation
    chal_res = await client.post("/api/v1/devices/challenge")
    assert chal_res.status_code == 201
    challenge_id = chal_res.json()["challenge_id"]
    nonce = chal_res.json()["nonce"]

    # 9. Sign Challenge Proof Payload with Terminal's Ed25519 Private Key
    proof_payload = {
        "challenge_id": challenge_id,
        "device_id": device_id,
        "fingerprint": terminal_fingerprint,
        "nonce": nonce,
        "purpose": "POS_SYNC_ACTIVATION",
    }
    canonical_proof = rfc8785.dumps(proof_payload)
    client_sig = dev_priv_key.sign(canonical_proof)
    client_sig_b64 = base64.b64encode(client_sig).decode("utf-8")

    # 10. Activate Sync via VEX IAM
    activate_res = await client.post(
        f"/api/v1/devices/{device_id}/sync-activate",
        json={
            "challenge_id": challenge_id,
            "signature_b64": client_sig_b64,
            "application_code": "VEX-POS",
        },
    )
    assert activate_res.status_code == 200
    act_data = activate_res.json()
    assert act_data["device_id"] == device_id
    assert act_data["location_id"] == loc_id
    assert act_data["sync_endpoint"] == "https://vexcloudapi.vexxero.com"
    assert act_data["signature_b64"] is not None
    assert act_data["ticket_payload"]["terminal_identifier"] == terminal_fingerprint
    assert act_data["ticket_payload"]["sync_endpoint"] == "https://vexcloudapi.vexxero.com"

    # 11. Verify IAM Signature on the Ticket Payload using IAM's Public Key
    ticket_canonical_bytes = act_data["signed_ticket"].encode("utf-8")
    iam_sig_bytes = base64.b64decode(act_data["signature_b64"])
    
    # Verify using VEX IAM's Ed25519 public key
    _public_key.verify(iam_sig_bytes, ticket_canonical_bytes)

    # 12. Negative Test: When cloud sync (pos.sync) is disabled for a store, activation must return 403 Forbidden
    disabled_loc_res = await client.post(
        f"/api/v1/organizations/{org_id}/locations",
        json={"code": "STORE-OFFLINE", "name": "Offline Store", "metadata": {"pos.sync": False}},
        headers=owner_headers,
    )
    disabled_loc_id = disabled_loc_res.json()["id"]

    # Reassign device to disabled location
    reassign_res = await client.post(
        f"/api/v1/devices/{device_id}/reassign",
        json={"target_location_id": disabled_loc_id},
        headers=owner_headers,
    )
    assert reassign_res.status_code == 200

    # Request new challenge for disabled store activation attempt
    chal2_res = await client.post("/api/v1/devices/challenge")
    chal2_id = chal2_res.json()["challenge_id"]
    proof2_payload = {
        "challenge_id": chal2_id,
        "device_id": device_id,
        "fingerprint": terminal_fingerprint,
        "nonce": chal2_res.json()["nonce"],
        "purpose": "POS_SYNC_ACTIVATION",
    }
    client_sig2 = dev_priv_key.sign(rfc8785.dumps(proof2_payload))
    client_sig2_b64 = base64.b64encode(client_sig2).decode("utf-8")

    disabled_act_res = await client.post(
        f"/api/v1/devices/{device_id}/sync-activate",
        json={
            "challenge_id": chal2_id,
            "signature_b64": client_sig2_b64,
            "application_code": "VEX-POS",
        },
    )
    assert disabled_act_res.status_code == 403
    assert "pos.sync" in disabled_act_res.json()["detail"]
