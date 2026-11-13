import pytest
import uuid
import base64
import rfc8785
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from app.domains.licensing.service import CommercialAndLicensingService


@pytest.mark.asyncio
async def test_application_registry_client_and_installation_architecture(client: AsyncClient):
    admin_headers = {"X-Platform-Admin-Key": "dev-platform-admin-key-change-in-production"}

    # 1. Register VEX-POS, VEX-ERP, VEX-PMS
    pos_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-POS-REG",
            "name": "VEX POS Windows Desktop",
            "platform_type": "WINDOWS_DESKTOP",
            "type": "LOCAL_HYBRID",
            "current_version": "1.0.0",
        },
        headers=admin_headers,
    )
    assert pos_res.status_code == 201
    pos_app_id = pos_res.json()["id"]
    assert pos_res.json()["platform_type"] == "WINDOWS_DESKTOP"
    assert pos_res.json()["status"] == "ACTIVE"

    # Reject duplicate application code
    dup_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-POS-REG",
            "name": "Duplicate VEX POS",
            "platform_type": "WINDOWS_DESKTOP",
        },
        headers=admin_headers,
    )
    assert dup_res.status_code == 409

    # Reject non-admin application registration
    unauth_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-UNAUTH",
            "name": "Unauthorized App",
        },
    )
    assert unauth_res.status_code == 401 or unauth_res.status_code == 403

    # Register VEX-ERP and VEX-PMS
    erp_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-ERP-REG",
            "name": "VEX Enterprise ERP",
            "platform_type": "WEB",
            "type": "WEB",
        },
        headers=admin_headers,
    )
    assert erp_res.status_code == 201

    pms_res = await client.post(
        "/api/v1/applications",
        json={
            "code": "VEX-PMS-REG",
            "name": "VEX Property Management",
            "platform_type": "WEB",
            "type": "WEB",
        },
        headers=admin_headers,
    )
    assert pms_res.status_code == 201

    # 2. Register Application Client
    client_res = await client.post(
        f"/api/v1/applications/{pos_app_id}/clients",
        json={
            "client_code": "VEX-POS-WIN-01",
            "client_name": "VEX POS Windows Desktop Client v1",
            "client_type": "DESKTOP",
        },
        headers=admin_headers,
    )
    assert client_res.status_code == 201
    assert client_res.json()["client_code"] == "VEX-POS-WIN-01"

    # 3. Create Plan and Multiple Subscriptions for Pooling Test
    plan_res = await client.post(
        "/api/v1/plans",
        json={
            "application_id": pos_app_id,
            "code": "POS-POOL-PLAN",
            "name": "POS Entitlement Pool Plan",
            "user_seats": 10,
            "device_seats": 2,  # 2 seats per subscription
        },
        headers=admin_headers,
    )
    assert plan_res.status_code == 201
    plan_id = plan_res.json()["id"]

    # Register an Organization Owner & Org
    owner_reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "poolowner@vex.com", "password": "Password123!", "first_name": "Pool", "last_name": "Owner"},
    )
    owner_login = await client.post(
        "/api/v1/auth/login",
        json={"email": "poolowner@vex.com", "password": "Password123!"},
    )
    owner_token = owner_login.json()["access_token"]
    owner_id = owner_login.json()["user"]["id"]
    owner_headers = {"Authorization": f"Bearer {owner_token}"}

    from app.core.security import create_email_verification_token
    verify_token = create_email_verification_token(owner_id, "poolowner@vex.com")
    await client.post("/api/v1/auth/verify-email", json={"token": verify_token})

    org_res = await client.post(
        "/api/v1/organizations",
        json={"name": "Acme Retail Chain"},
        headers=owner_headers,
    )
    org_id = org_res.json()["id"]

    # Purchase Subscription A (expires in 10 days)
    now = datetime.now(timezone.utc)
    subA_res = await client.post(
        "/api/v1/subscriptions",
        json={
            "plan_id": plan_id,
            "owner_type": "ORGANIZATION",
            "organization_id": org_id,
        },
        headers=admin_headers,
    )
    subA_id = subA_res.json()["id"]

    # Purchase Subscription B (expires in 30 days)
    subB_res = await client.post(
        "/api/v1/subscriptions",
        json={
            "plan_id": plan_id,
            "owner_type": "ORGANIZATION",
            "organization_id": org_id,
        },
        headers=admin_headers,
    )
    subB_id = subB_res.json()["id"]

    # Verify Entitlements Pooling: 2 + 2 = 4 total pooled device seats
    entitlements_res = await client.get(
        f"/api/v1/licenses/entitlements?organization_id={org_id}&application_code=VEX-POS-REG",
        headers=owner_headers,
    )
    assert entitlements_res.status_code == 200
    ent_data = entitlements_res.json()
    assert ent_data["max_terminals"] == 4
    assert ent_data["available_terminals"] == 4
    assert ent_data["active_terminals"] == 0

    # 4. Register Device 1
    term1_priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub1 = term1_priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
    )
    pub1_b64 = base64.b64encode(raw_pub1).decode("utf-8")
    term1_fp = "FP-TERM-POOLED-01"

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
            "name": "Terminal 1 - POS",
            "fingerprint": term1_fp,
            "public_key": pub1_b64,
            "challenge_id": chal1_data["challenge_id"],
            "signature_b64": base64.b64encode(sig1).decode("utf-8"),
        },
        headers=owner_headers,
    )
    dev1_id = dev1_res.json()["id"]

    # 5. Activate License for Terminal 1 with installation_id and client_code
    act1_res = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev1_id,
            "application_id": pos_app_id,
            "installation_id": "INSTALL-WIN-UUID-001",
            "client_code": "VEX-POS-WIN-01",
        },
        headers=owner_headers,
    )
    assert act1_res.status_code == 201
    act1_data = act1_res.json()
    assert act1_data["status"] == "ACTIVE"
    assert act1_data["device_license_id"] == act1_data["id"]
    assert act1_data["installation_id"] is not None

    # Idempotent reinstallation on the same terminal: Must NOT consume another seat!
    act1_reinstall = await client.post(
        "/api/v1/licenses/activate",
        json={
            "device_id": dev1_id,
            "application_id": pos_app_id,
            "installation_id": "INSTALL-WIN-UUID-001",
            "client_code": "VEX-POS-WIN-01",
        },
        headers=owner_headers,
    )
    assert act1_reinstall.status_code == 201
    assert act1_reinstall.json()["id"] == act1_data["id"]

    # Check updated pooled availability: 1 active, 3 available
    ent2_res = await client.get(
        f"/api/v1/licenses/entitlements?organization_id={org_id}&application_code=VEX-POS-REG",
        headers=owner_headers,
    )
    assert ent2_res.json()["active_terminals"] == 1
    assert ent2_res.json()["available_terminals"] == 3

    # 6. Admin Licensing Dashboard (Phase 12 / Spec Section 17)
    dashboard_res = await client.get(
        f"/api/v1/admin/licensing/dashboard?organization_id={org_id}&application_code=VEX-POS-REG",
        headers=admin_headers,
    )
    assert dashboard_res.status_code == 200
    dash_data = dashboard_res.json()
    assert dash_data["total_pooled_capacity"] == 4
    assert dash_data["active_device_licenses_count"] == 1
    assert dash_data["available_seats"] == 3
    assert dash_data["utilization_percentage"] == 25.0
    assert len(dash_data["subscriptions"]) == 2
    assert len(dash_data["recent_allocations"]) >= 1

