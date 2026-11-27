import base64
import json
import uuid
import pytest
import rfc8785
from datetime import datetime, timezone
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.locations.models import Location, LocationApplication, LocationApplicationStatus
from app.domains.applications.models import Application
from app.domains.subscriptions.models import Subscription, Plan, SubscriptionStatus, OwnerType
from app.domains.licensing.models import Device, DeviceLicense, LicenseStatus, DeviceStatus
from app.domains.licensing.service import CommercialAndLicensingService


@pytest.mark.asyncio
async def test_menu_mode_governance_and_signed_license_entitlements(client: AsyncClient, db_session: AsyncSession):
    db = db_session
    # 1. Setup Org, Location, App, Plan, Active Subscription
    org = Organization(name="Menu Test Org")
    db.add(org)
    await db.flush()

    loc = Location(organization_id=org.id, name="Main Store", code="MAIN-1")
    db.add(loc)
    await db.flush()

    app = Application(code="VEX-POS", name="Vexxero POS Desktop", is_active=True)
    db.add(app)
    await db.flush()

    loc_app = LocationApplication(
        organization_id=org.id,
        location_id=loc.id,
        application_id=app.id,
        status=LocationApplicationStatus.ACTIVE,
    )
    db.add(loc_app)
    await db.flush()

    plan = Plan(name="POS Pro", code="POS-PRO-TEST", application_id=app.id, device_seats=5)
    db.add(plan)
    await db.flush()

    sub = Subscription(
        organization_id=org.id,
        plan_id=plan.id,
        owner_type=OwnerType.ORGANIZATION,
        status=SubscriptionStatus.ACTIVE,
    )
    db.add(sub)
    await db.flush()

    # 2. Register Device with default (None) terminal menu mode -> inherits location default (LOCAL)
    device_priv = Ed25519PrivateKey.generate()
    device_pub = device_priv.public_key()
    device_pub_b64 = base64.b64encode(device_pub.public_bytes_raw()).decode("utf-8")

    device = Device(
        organization_id=org.id,
        location_id=loc.id,
        name="Counter Terminal 1",
        fingerprint="DEV-FINGERPRINT-001",
        public_key=device_pub_b64,
        status=DeviceStatus.ACTIVE,
        sync_enabled=True,
        menu_mode=None,
    )
    db.add(device)
    await db.commit()
    await db.refresh(device)

    assert device.menu_mode is None

    from app.core.config import settings
    admin_headers = {"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY}

    # 3. Query Device Verification -> effective_menu_mode resolves to LOCAL from location default
    res = await client.get(
        f"/api/v1/devices/internal/verify?organization_id={org.id}&terminal_identifier={device.id}",
        headers=admin_headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["menu_mode"] is None
    assert data["effective_menu_mode"] == "LOCAL"

    actor_id = uuid.uuid4()
    member = OrganizationMember(
        organization_id=org.id,
        user_id=actor_id,
        role=OrganizationRole.OWNER,
    )
    db.add(member)
    await db.flush()

    from app.domains.licensing.schemas import LicenseIssueRequest
    lic_res = await CommercialAndLicensingService.issue_device_license(
        db,
        actor_user_id=actor_id,
        req=LicenseIssueRequest(
            device_id=device.id,
            application_id=str(app.id),
            installation_id=str(uuid.uuid4()),
        ),
    )
    raw_payload = lic_res.signed_payload
    payload_dict = json.loads(raw_payload)
    assert "entitlements" in payload_dict
    assert "menu_management.mode:local" in payload_dict["entitlements"]
    assert "menu_management.mode:cloud" not in payload_dict["entitlements"]

    # 4. Switch terminal to CLOUD -> SUCCEEDS (200)
    mode_switch_res = await client.post(
        f"/api/v1/devices/{device.id}/menu-mode?mode=CLOUD"
    )
    assert mode_switch_res.status_code == 200
    assert mode_switch_res.json()["menu_mode"] == "CLOUD"
    assert mode_switch_res.json()["effective_menu_mode"] == "CLOUD"

    # 6. Verify heartbeat rolls license and delivers menu_management.mode:cloud
    hb_canonical = {
        "device_id": str(device.id),
        "fingerprint": device.fingerprint,
        "sequence": 1,
        "timestamp": int(datetime.now(timezone.utc).timestamp()),
        "application_id": str(app.id),
    }
    hb_sig = device_priv.sign(rfc8785.dumps(hb_canonical))

    hb_res = await client.post(
        f"/api/v1/devices/{device.id}/heartbeat",
        json={
            "canonical_request": hb_canonical,
            "signature_b64": base64.b64encode(hb_sig).decode("utf-8"),
        },
    )
    assert hb_res.status_code == 200
    hb_data = hb_res.json()
    assert hb_data["menu_mode"] == "CLOUD"
    assert hb_data["effective_menu_mode"] == "CLOUD"

    target_lic = await db.execute(select(DeviceLicense).where(DeviceLicense.device_id == device.id))
    lic_record = target_lic.scalars().first()
    assert lic_record is not None
    hb_payload_dict = json.loads(lic_record.signed_payload)
    assert "menu_management.mode:cloud" in hb_payload_dict["entitlements"]
    assert "menu_management.mode:local" not in hb_payload_dict["entitlements"]

