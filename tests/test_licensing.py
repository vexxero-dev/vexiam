import pytest
import base64
import rfc8785
from datetime import datetime, timezone
from httpx import AsyncClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.domains.licensing.service import CommercialAndLicensingService


@pytest.mark.asyncio
async def test_commercial_and_offline_device_licensing(client: AsyncClient):
    # 1. Register Owner
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "boss@bbcafe.com", "password": "Password123!", "first_name": "Boss", "last_name": "Man"},
    )
    assert owner_reg.status_code == 201

    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "boss@bbcafe.com", "password": "Password123!"},
    )
    owner_token = owner_login.json()["access_token"]
    owner_id = owner_login.json()["user"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # Verify Owner's email before creating organization and registering devices
    from app.core.security import create_email_verification_token
    owner_verify_token = create_email_verification_token(owner_id, "boss@bbcafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": owner_verify_token})

    # 2. Create Organization
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Metropolis Branch"},
        headers=owner_headers,
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 3. Register VEX-POS Application (Platform Admin boundary)
    admin_headers = {"X-Platform-Admin-Key": "dev-platform-admin-key-change-in-production"}
    app_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-POS-COMMERCIAL",
            "name": "Vexxero Point of Sale",
            "type": "LOCAL_HYBRID",
        },
        headers=admin_headers,
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 4. Create Plan with 1 device seat limit (Platform Admin only)
    plan_res = await client.post(
        "/api/v1/plans",
        json={
            "application_id": app_id,
            "code": "POS-STARTER-1SEAT",
            "name": "POS Starter (1 Terminal)",
            "user_seats": 5,
            "device_seats": 1,
        },
        headers=admin_headers,
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # 5. Purchase Organization Subscription (Platform Admin / Billing Webhook)
    sub_res = await client.post(
        "/api/v1/subscriptions",
        json={
            "plan_id": plan_id,
            "owner_type": "ORGANIZATION",
            "organization_id": org_id,
        },
        headers=admin_headers,
    )
    assert sub_res.status_code == 201

    # 6. Register First POS Terminal (Terminal 01) with mandatory Proof-of-Possession
    term1_priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub1 = term1_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub1_b64 = base64.b64encode(raw_pub1).decode("utf-8")
    term1_fp = "HW-CPU-SN-99887766-TERM1"

    chal1_res = await client.post("/api/v1/devices/challenge")
    chal1_data = chal1_res.json()

    chal1_payload = {
        "challenge_id": chal1_data["challenge_id"],
        "device_id": term1_fp,
        "nonce": chal1_data["nonce"],
        "organization_id": org_id,
    }
    sig1 = term1_priv.sign(rfc8785.dumps(chal1_payload))

    dev1_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Terminal 01 - Cashier",
            "fingerprint": term1_fp,
            "public_key": pub1_b64,
            "challenge_id": chal1_data["challenge_id"],
            "signature_b64": base64.b64encode(sig1).decode("utf-8"),
        },
        headers=owner_headers,
    )
    assert dev1_res.status_code == 201
    dev1_id = dev1_res.json()["id"]

    # 7. Activate License for Terminal 01
    lic1_res = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev1_id,
            "application_id": app_id,
        },
        headers=owner_headers,
    )
    assert lic1_res.status_code == 201
    license_data = lic1_res.json()
    assert license_data["status"] == "ACTIVE"
    assert license_data["organization_name"] == "Metropolis Branch"
    assert license_data["product_name"] == "Vexxero Point of Sale"
    signed_payload = license_data["signed_payload"]
    signature = license_data["signature"]
    lic1_id = license_data["id"]

    # 7B. Test Idempotency: Re-activating the same terminal must update the lease and NOT fail quota
    lic1_reauth = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev1_id,
            "application_id": app_id,
        },
        headers=owner_headers,
    )
    assert lic1_reauth.status_code == 201
    assert lic1_reauth.json()["id"] == lic1_id

    # 8. Test Offline Verification Routine (simulating local POS Terminal Agent offline)
    offline_verified_data = CommercialAndLicensingService.verify_offline_license(
        signed_payload, signature
    )
    assert offline_verified_data["application_code"] == "VEX-POS-COMMERCIAL"
    assert offline_verified_data["product_name"] == "Vexxero Point of Sale"
    assert offline_verified_data["organization_name"] == "Metropolis Branch"
    assert offline_verified_data["fingerprint"] == term1_fp
    assert offline_verified_data["grace_period_days"] == 7

    # 9. Register Second POS Terminal (Terminal 02) with Proof-of-Possession
    term2_priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub2 = term2_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub2_b64 = base64.b64encode(raw_pub2).decode("utf-8")
    term2_fp = "HW-CPU-SN-99887766-TERM2"

    chal2_res = await client.post("/api/v1/devices/challenge")
    chal2_data = chal2_res.json()
    chal2_payload = {
        "challenge_id": chal2_data["challenge_id"],
        "device_id": term2_fp,
        "nonce": chal2_data["nonce"],
        "organization_id": org_id,
    }
    sig2 = term2_priv.sign(rfc8785.dumps(chal2_payload))

    dev2_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Terminal 02 - Drive-thru",
            "fingerprint": term2_fp,
            "public_key": pub2_b64,
            "challenge_id": chal2_data["challenge_id"],
            "signature_b64": base64.b64encode(sig2).decode("utf-8"),
        },
        headers=owner_headers,
    )
    assert dev2_res.status_code == 201
    dev2_id = dev2_res.json()["id"]

    # 10. Attempt to Activate Terminal 02: Must fail with HTTP 403 (device seat quota limit: 1)
    lic2_res = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev2_id,
            "application_id": app_id,
        },
        headers=owner_headers,
    )
    assert lic2_res.status_code == 403
    assert "Device seat quota exceeded" in lic2_res.json()["detail"]

    # 11. Test Cryptographically-Signed POS Heartbeat (sequence 1)
    hb_canonical = {
        "device_id": str(dev1_id),
        "fingerprint": term1_fp,
        "sequence": 1,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "application_id": str(app_id),
    }
    hb_sig = term1_priv.sign(rfc8785.dumps(hb_canonical))

    hb_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(hb_sig).decode("utf-8"),
        },
    )
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert hb_data["is_valid"] is True
    assert hb_data["license_status"] == "ACTIVE"
    assert hb_data["organization_name"] == "Metropolis Branch"
    assert hb_data["product_name"] == "Vexxero Point of Sale"
    assert hb_data["license"] is not None

    # 11B. Test Replay Attack Prevention: Re-sending sequence 1 MUST fail with 400
    replay_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(hb_sig).decode("utf-8"),
        },
    )
    assert replay_res.status_code == 400
    assert "replay attack detected" in replay_res.json()["detail"].lower()

    # 11C. Monotonic sequence 2 succeeds
    hb_canonical2 = dict(hb_canonical, sequence=2)
    hb_sig2 = term1_priv.sign(rfc8785.dumps(hb_canonical2))
    hb2_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "canonical_request": hb_canonical2,
            "signature_b64": base64.b64encode(hb_sig2).decode("utf-8"),
        },
    )
    assert hb2_res.status_code == 200

    # 12. Revoke Terminal 01 (Admin Action)
    revoke_res = await client.post(
        f"/api/v1/devices/{dev1_id}/revoke",
        headers=owner_headers,
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "REVOKED"

    # 13. Terminal 01 Heartbeat (sequence 3) reports revocation
    hb_canonical3 = dict(hb_canonical, sequence=3)
    hb_sig3 = term1_priv.sign(rfc8785.dumps(hb_canonical3))
    hb_revoked_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "canonical_request": hb_canonical3,
            "signature_b64": base64.b64encode(hb_sig3).decode("utf-8"),
        },
    )
    assert hb_revoked_res.status_code == 200
    hb_revoked_data = hb_revoked_res.json()
    assert hb_revoked_data["is_valid"] is False
    assert hb_revoked_data["device_status"] == "REVOKED"

    # 14. Terminal 02 can now activate because Terminal 01 revocation freed up the seat!
    lic2_retry_res = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev2_id,
            "application_id": app_id,
        },
        headers=owner_headers,
    )
    assert lic2_retry_res.status_code == 201
    assert lic2_retry_res.json()["status"] == "ACTIVE"
