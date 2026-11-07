import pytest
from httpx import AsyncClient
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
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    # 2. Create Organization
    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Metropolis Branch"},
        headers=owner_headers,
    )
    assert org_res.status_code == 201
    org_id = org_res.json()["id"]

    # 3. Register VEX-POS Application
    app_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-POS-COMMERCIAL",
            "name": "Vexxero Point of Sale",
            "type": "LOCAL_HYBRID",
        },
    )
    assert app_res.status_code == 201
    app_id = app_res.json()["id"]

    # 4. Create Plan with 1 device seat limit
    plan_res = await client.post(
        "/api/v1/plans",
        json={
            "application_id": app_id,
            "code": "POS-STARTER-1SEAT",
            "name": "POS Starter (1 Terminal)",
            "user_seats": 5,
            "device_seats": 1,
        },
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # 5. Purchase Organization Subscription
    sub_res = await client.post(
        "/api/v1/subscriptions",
        json={
            "plan_id": plan_id,
            "owner_type": "ORGANIZATION",
            "organization_id": org_id,
        },
    )
    assert sub_res.status_code == 201

    # 6. Register First POS Terminal (Terminal 01)
    dev1_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Terminal 01 - Cashier",
            "fingerprint": "HW-CPU-SN-99887766-TERM1",
            "public_key": "MCowBQYDK2VwAyEA9YQYyqZ9dO1Z...",
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
    signed_payload = license_data["signed_payload"]
    signature = license_data["signature"]

    # 8. Test Offline Verification Routine (simulating local POS Terminal Agent offline)
    offline_verified_data = CommercialAndLicensingService.verify_offline_license(
        signed_payload, signature
    )
    assert offline_verified_data["application_code"] == "VEX-POS-COMMERCIAL"
    assert offline_verified_data["fingerprint"] == "HW-CPU-SN-99887766-TERM1"
    assert offline_verified_data["grace_period_days"] == 7

    # 9. Register Second POS Terminal (Terminal 02)
    dev2_res = await client.post(
        "/api/v1/devices/register",
        json={
            "organization_id": org_id,
            "name": "Terminal 02 - Drive-thru",
            "fingerprint": "HW-CPU-SN-99887766-TERM2",
            "public_key": "MCowBQYDK2VwAyEA...",
        },
        headers=owner_headers,
    )
    assert dev2_res.status_code == 201
    dev2_id = dev2_res.json()["id"]

    # 10. Attempt to Activate Terminal 02: Must fail with HTTP 403 (device seat quota exceeded)
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

    # 11. Test POS Heartbeat Check-in (startup & periodic sync)
    hb_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "fingerprint": "HW-CPU-SN-99887766-TERM1",
            "application_id": app_id,
        },
    )
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert hb_data["is_valid"] is True
    assert hb_data["license_status"] == "ACTIVE"
    assert hb_data["license"] is not None

    # 12. Revoke Terminal 01 (Admin Action)
    revoke_res = await client.post(
        f"/api/v1/devices/{dev1_id}/revoke",
        headers=owner_headers,
    )
    assert revoke_res.status_code == 200
    assert revoke_res.json()["status"] == "REVOKED"

    # 13. Terminal 01 Heartbeat should now report revocation
    hb_revoked_res = await client.post(
        f"/api/v1/devices/{dev1_id}/heartbeat",
        json={
            "fingerprint": "HW-CPU-SN-99887766-TERM1",
            "application_id": app_id,
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
