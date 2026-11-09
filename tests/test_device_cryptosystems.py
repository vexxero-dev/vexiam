import pytest
import base64
import rfc8785
from datetime import datetime, timezone
from httpx import AsyncClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.core.security import create_email_verification_token
from app.core.config import settings


@pytest.mark.asyncio
async def test_device_proof_of_possession_and_signed_heartbeat_security(client: AsyncClient):
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    # 1. Register & verify Organization Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "terminal_admin@cafe.com", "password": "Password123!", "first_name": "T", "last_name": "Admin"},
    )
    assert owner_reg.status_code == 201
    owner_id = owner_reg.json()["id"]

    token = create_email_verification_token(owner_id, "terminal_admin@cafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    login_res = await client.post(
        "/api/v1/auth/login",
        json={"email": "terminal_admin@cafe.com", "password": "Password123!"},
    )
    owner_headers = {"Authorization": f"Bearer {login_res.json()['access_token']}"}

    # 2. Create Org
    org_res = await client.post("/api/v1/organizations", json={"name": "Secure Terminals Branch"}, headers=owner_headers)
    org_id = org_res.json()["id"]

    # 3. Register App, Plan, Subscription
    app_res = await client.post(
        "/api/v1/applications",
        json={"code": "VEX-POS-HARDENED", "name": "Hardened POS", "type": "LOCAL_HYBRID"},
        headers=admin_headers,
    )
    app_id = app_res.json()["id"]

    plan_res = await client.post(
        "/api/v1/plans",
        json={"application_id": app_id, "code": "POS-DEV-1", "name": "POS 1 Terminal", "user_seats": 2, "device_seats": 1},
        headers=admin_headers,
    )
    plan_id = plan_res.json()["id"]

    await client.post(
        "/api/v1/subscriptions",
        json={"plan_id": plan_id, "owner_type": "ORGANIZATION", "organization_id": org_id},
        headers=admin_headers,
    )

    # 4. Mandatory Proof of Possession: Attempting registration with forged signature MUST fail (401)
    priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    device_fp = "HW-HARDENED-TERM-001"

    chal_res = await client.post("/api/v1/devices/challenge")
    chal_data = chal_res.json()

    forged_reg = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Hardened POS 1",
            "fingerprint": device_fp,
            "public_key": pub_b64,
            "challenge_id": chal_data["challenge_id"],
            "signature_b64": base64.b64encode(b"invalid-forged-signature-bytes-here!!").decode("utf-8"),
        },
        headers=owner_headers,
    )
    assert forged_reg.status_code == 401
    assert "proof of possession failed" in forged_reg.json()["detail"].lower()

    # 5. Legitimate PoP Registration succeeds
    chal2_res = await client.post("/api/v1/devices/challenge")
    chal2_data = chal2_res.json()

    valid_payload = {
        "challenge_id": chal2_data["challenge_id"],
        "device_id": device_fp,
        "nonce": chal2_data["nonce"],
        "organization_id": org_id,
    }
    valid_sig = priv.sign(rfc8785.dumps(valid_payload))

    reg_ok = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Hardened POS 1",
            "fingerprint": device_fp,
            "public_key": pub_b64,
            "challenge_id": chal2_data["challenge_id"],
            "signature_b64": base64.b64encode(valid_sig).decode("utf-8"),
        },
        headers=owner_headers,
    )
    assert reg_ok.status_code == 201
    device_id = reg_ok.json()["id"]

    # 6. Activate license
    lic_res = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": device_id, "application_id": app_id},
        headers=owner_headers,
    )
    assert lic_res.status_code == 201
    lic_id = lic_res.json()["id"]

    # 7. Re-activation is idempotent (does not exceed seat quota or create extra license)
    lic_reauth = await client.post(
        "/api/v1/licenses/activate",
        json={"device_id": device_id, "application_id": app_id},
        headers=owner_headers,
    )
    assert lic_reauth.status_code == 201
    assert lic_reauth.json()["id"] == lic_id

    # 8. Unsigned / Forged Heartbeat MUST fail (401)
    hb_canonical = {
        "device_id": str(device_id),
        "fingerprint": device_fp,
        "sequence": 1,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "application_id": str(app_id),
    }
    forged_hb = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(b"forged-signature-bytes-not-matching-key").decode("utf-8"),
        },
    )
    assert forged_hb.status_code == 401
    assert "cryptographic heartbeat verification failed" in forged_hb.json()["detail"].lower()

    # 9. Correctly signed heartbeat succeeds
    valid_hb_sig = priv.sign(rfc8785.dumps(hb_canonical))
    valid_hb = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(valid_hb_sig).decode("utf-8"),
        },
    )
    assert valid_hb.status_code == 200
    assert valid_hb.json()["is_valid"] is True

    # 10. Replay attack with same sequence MUST fail (400)
    replay_hb = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(valid_hb_sig).decode("utf-8"),
        },
    )
    assert replay_hb.status_code == 400
    assert "replay attack detected" in replay_hb.json()["detail"].lower()

    # 11. Heartbeat with expired/skewed timestamp (>300s in past or future) MUST fail (400)
    skewed_canonical = {
        "device_id": str(device_id),
        "fingerprint": device_fp,
        "sequence": 2,
        "timestamp": int(datetime.now(timezone.utc).timestamp()) - 3600,  # 1 hour in the past
        "application_id": str(app_id),
    }
    skewed_sig = priv.sign(rfc8785.dumps(skewed_canonical))
    skewed_res = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={
            "canonical_request": skewed_canonical,
            "signature_b64": base64.b64encode(skewed_sig).decode("utf-8"),
        },
    )
    assert skewed_res.status_code == 400
    assert "timestamp skew exceeds allowed threshold" in skewed_res.json()["detail"].lower()

    # 12. Authenticated Hardware Recovery: Re-registration via PoP challenge resets sequence counter
    chal3_res = await client.post("/api/v1/devices/challenge")
    chal3_data = chal3_res.json()
    recovery_payload = {
        "challenge_id": chal3_data["challenge_id"],
        "device_id": device_fp,
        "nonce": chal3_data["nonce"],
        "organization_id": org_id,
    }
    recovery_sig = priv.sign(rfc8785.dumps(recovery_payload))
    recovery_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Hardened POS 1 (Recovered)",
            "fingerprint": device_fp,
            "public_key": pub_b64,
            "challenge_id": chal3_data["challenge_id"],
            "signature_b64": base64.b64encode(recovery_sig).decode("utf-8"),
        },
        headers=owner_headers,
    )
    assert recovery_res.status_code == 201

    # Now sequence 1 works again after authenticated recovery
    reset_canonical = {
        "device_id": str(device_id),
        "fingerprint": device_fp,
        "sequence": 1,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "application_id": str(app_id),
    }
    reset_sig = priv.sign(rfc8785.dumps(reset_canonical))
    reset_hb = await client.post(
        f"/api/v1/devices/{device_id}/heartbeat",
        json={
            "canonical_request": reset_canonical,
            "signature_b64": base64.b64encode(reset_sig).decode("utf-8"),
        },
    )
    assert reset_hb.status_code == 200
    assert reset_hb.json()["is_valid"] is True
