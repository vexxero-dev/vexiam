import base64
import hashlib
import uuid
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException

from app.domains.licensing.schemas import DeviceRegisterRequest
from app.domains.licensing.service import CommercialAndLicensingService
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.identity.models import User


def _gen_key_and_fp():
    priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    fp = f"VEX-DEV-{hashlib.sha256(raw_pub).hexdigest()}"
    return pub_b64, fp


@pytest.mark.asyncio
async def test_iam_register_device_idempotent_and_conflict(db_session):
    user = User(
        id=uuid.uuid4(),
        email=f"owner_{uuid.uuid4().hex[:6]}@vex.local",
    )
    org = Organization(id=uuid.uuid4(), name="Test Org")
    db_session.add_all([user, org])
    await db_session.flush()

    member = OrganizationMember(
        organization_id=org.id,
        user_id=user.id,
        role=OrganizationRole.OWNER,
    )
    db_session.add(member)
    await db_session.commit()

    pub1, fp1 = _gen_key_and_fp()
    pub2, _ = _gen_key_and_fp()

    # 1. Initial registration
    req1 = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1",
        fingerprint=fp1,
        public_key=pub1,
    )
    dev1 = await CommercialAndLicensingService.register_device(db_session, user.id, req1)
    assert dev1.fingerprint == fp1
    assert dev1.public_key == pub1
    dev1.last_sequence = 42
    await db_session.commit()

    # 2. Same fingerprint and same public key (with whitespace/Base64 formatting difference) -> idempotent & preserves last_sequence
    req_idem = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1 Renamed",
        fingerprint=fp1,
        public_key=f" {pub1}\n",
    )
    dev_idem = await CommercialAndLicensingService.register_device(db_session, user.id, req_idem)
    assert dev_idem.id == dev1.id
    assert dev_idem.public_key == pub1
    assert dev_idem.last_sequence == 42

    # 2b. Malformed public key -> 400 Bad Request
    req_malformed = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1 Malformed",
        fingerprint="HW-MALFORMED-001",
        public_key="not-a-valid-ed25519-key!!!",
    )
    with pytest.raises(HTTPException) as exc_mal:
        await CommercialAndLicensingService.register_device(db_session, user.id, req_malformed)
    assert exc_mal.value.status_code == 400

    # 3. Same fingerprint with different public key -> 409 Conflict
    pub_static, _ = _gen_key_and_fp()
    req_conflict = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1 Hijack",
        fingerprint="HW-STATIC-001",
        public_key=pub_static,
    )
    await CommercialAndLicensingService.register_device(db_session, user.id, req_conflict)

    req_conflict2 = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1 Hijack",
        fingerprint="HW-STATIC-001",
        public_key=pub2,
    )
    with pytest.raises(HTTPException) as exc_info:
        await CommercialAndLicensingService.register_device(db_session, user.id, req_conflict2)
    assert exc_info.value.status_code == 409

    # 4. VEX-DEV- fingerprint inconsistent with submitted public key -> 400 Bad Request
    req_mismatch = DeviceRegisterRequest(
        organization_id=org.id,
        name="POS 1 Mismatch",
        fingerprint=fp1,
        public_key=pub2,
    )
    with pytest.raises(HTTPException) as exc_mismatch:
        await CommercialAndLicensingService.register_device(db_session, user.id, req_mismatch)
    assert exc_mismatch.value.status_code == 400
