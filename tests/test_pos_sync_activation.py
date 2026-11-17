import pytest
import base64
import rfc8785
from datetime import datetime, timezone
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

    # Enable VEX-POS at this store location
    await client.post(
        f"/api/v1/locations/{disabled_loc_id}/applications",
        json={"application_id": app_id},
        headers=owner_headers,
    )

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

    # 13. Verify sync_enabled flag & Deactivation endpoint
    dev_info = await client.get(f"/api/v1/organizations/{org_id}/devices", headers=owner_headers)
    assert dev_info.status_code == 200
    target_dev = next(d for d in dev_info.json() if d["id"] == device_id)
    assert target_dev["sync_enabled"] is True

    # 14. Verify Authoritative PDP Heartbeat Response when device has sync_enabled=True but reassigned to offline store (sync_entitled=False)
    now_ts = int(datetime.now(timezone.utc).timestamp())
    hb_canonical = {
        "device_id": device_id,
        "fingerprint": terminal_fingerprint,
        "sequence": 1,
        "timestamp": now_ts,
        "application_id": "VEX-POS",
    }
    hb_sig = dev_priv_key.sign(rfc8785.dumps(hb_canonical))
    hb_sig_b64 = base64.b64encode(hb_sig).decode("utf-8")

    hb_res = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={"canonical_request": hb_canonical, "signature_b64": hb_sig_b64},
    )
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert hb_data["device_status"] == "ACTIVE"
    assert hb_data["is_valid"] is True
    assert hb_data["sync_enabled"] is True
    assert hb_data["sync_entitled"] is False

    # Also verify internal PDP endpoint directly reflects this exact policy state
    pdp_res = await client.get(
        f"/api/v1/devices/internal/verify?organization_id={org_id}&terminal_identifier={device_id}",
        headers={"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY},
    )
    assert pdp_res.status_code == 200
    pdp_data = pdp_res.json()
    assert pdp_data["sync_enabled"] is True
    assert pdp_data["sync_entitled"] is False

    # 15. Test deactivate sync and check updated heartbeat + PDP policy state
    deact_res = await client.post(f"/api/v1/devices/{device_id}/sync-deactivate", headers=owner_headers)
    assert deact_res.status_code == 200
    assert deact_res.json()["sync_enabled"] is False

    dev_info_after = await client.get(f"/api/v1/organizations/{org_id}/devices", headers=owner_headers)
    target_dev_after = next(d for d in dev_info_after.json() if d["id"] == device_id)
    assert target_dev_after["sync_enabled"] is False

    hb2_canonical = {
        "device_id": device_id,
        "fingerprint": terminal_fingerprint,
        "sequence": 2,
        "timestamp": now_ts,
        "application_id": "VEX-POS",
    }
    hb2_sig = dev_priv_key.sign(rfc8785.dumps(hb2_canonical))
    hb2_sig_b64 = base64.b64encode(hb2_sig).decode("utf-8")

    hb2_res = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={"canonical_request": hb2_canonical, "signature_b64": hb2_sig_b64},
    )
    assert hb2_res.status_code == 200
    hb2_data = hb2_res.json()
    assert hb2_data["sync_enabled"] is False
    assert hb2_data["sync_entitled"] is False

    pdp2_res = await client.get(
        f"/api/v1/devices/internal/verify?organization_id={org_id}&terminal_identifier={device_id}",
        headers={"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY},
    )
    assert pdp2_res.status_code == 200
    assert pdp2_res.json()["sync_enabled"] is False
    assert pdp2_res.json()["sync_entitled"] is False
