import pytest
import uuid
import base64
import rfc8785
from httpx import AsyncClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.domains.licensing.service import CommercialAndLicensingService


@pytest.mark.asyncio
async def test_challenge_response_and_rfc8785_licensing(client: AsyncClient):
    # 1. Issue device registration challenge
    chal_resp = await client.post("/api/v1/devices/challenge")
    assert chal_resp.status_code == 201
    chal_data = chal_resp.json()
    assert "challenge_id" in chal_data
    assert "nonce" in chal_data

    # 2. Register Owner & Org
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "operator@bbcafe.com", "password": "Password123!", "first_name": "Op", "last_name": "One"},
    )
    assert owner_reg.status_code == 201

    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "operator@bbcafe.com", "password": "Password123!"},
    )
    assert login_resp.status_code == 200
    owner_id = login_resp.json()["user"]["id"]
    owner_token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {owner_token}"}

    # Verify operator's email before organization creation & device registration
    from app.core.security import create_email_verification_token
    token = create_email_verification_token(owner_id, "operator@bbcafe.com")
    await client.post("/api/v1/auth/verify-email", json={"token": token})

    org_res = await client.post("/api/v1/organizations", json={"name": "Downtown Espresso"}, headers=headers)
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 3. Generate terminal keypair and sign challenge
    priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    device_id = "VEX-DEV-CHAL-001"

    challenge_payload = {
        "challenge_id": chal_data["challenge_id"],
        "device_id": device_id,
        "nonce": chal_data["nonce"],
        "organization_id": org_id,
    }
    canonical_bytes = rfc8785.dumps(challenge_payload)
    sig = priv.sign(canonical_bytes)
    sig_b64 = base64.b64encode(sig).decode("utf-8")

    # 4. Register device with proof of possession
    reg_resp = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Barista Station 1",
            "fingerprint": device_id,
            "public_key": pub_b64,
            "challenge_id": chal_data["challenge_id"],
            "signature_b64": sig_b64,
        },
        headers=headers,
    )
    assert reg_resp.status_code == 201
    assert reg_resp.json()["fingerprint"] == device_id

    # 5. Consuming the same challenge a second time MUST fail
    re_resp = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Barista Station 2",
            "fingerprint": "VEX-DEV-CHAL-002",
            "public_key": pub_b64,
            "challenge_id": chal_data["challenge_id"],
            "signature_b64": sig_b64,
        },
        headers=headers,
    )
    assert re_resp.status_code == 401
