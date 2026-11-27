import base64
import hashlib
import uuid
from datetime import datetime, timezone
import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from sqlalchemy.exc import IntegrityError

from app.domains.identity.models import User
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.licensing.models import Device, DeviceCredential, CredentialStatus
from app.domains.licensing.schemas import DeviceRegisterRequest
from app.domains.licensing.service import CommercialAndLicensingService


def _gen_key_and_fp():
    priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    raw_hash = hashlib.sha256(raw_pub).hexdigest()
    fp = f"VEX-DEV-{raw_hash}"
    return pub_b64, fp, raw_hash


@pytest.mark.asyncio
async def test_milestone_2_1_device_and_credential_lifecycle(db_session):
    user = User(id=uuid.uuid4(), email=f"owner_{uuid.uuid4().hex[:6]}@vex.local")
    org = Organization(id=uuid.uuid4(), name="M21 Org")
    db_session.add_all([user, org])
    await db_session.flush()
    db_session.add(OrganizationMember(organization_id=org.id, user_id=user.id, role=OrganizationRole.OWNER))
    await db_session.commit()

    pub1, fp1, raw_hash1 = _gen_key_and_fp()
    req = DeviceRegisterRequest(organization_id=org.id, name="POS M21", fingerprint=fp1, public_key=pub1)
    dev = await CommercialAndLicensingService.register_device(db_session, user.id, req)
    dev_id = dev.id

    assert dev.terminal_id == fp1
    assert len(dev.credentials) == 1
    cred1 = dev.credentials[0]
    assert cred1.credential_version == 1
    assert cred1.status == CredentialStatus.ACTIVE
    assert cred1.key_fingerprint == raw_hash1

    # Next version allocation is monotonic
    next_ver = await CommercialAndLicensingService.allocate_next_credential_version(db_session, dev.id)
    assert next_ver == 2

    # Duplicate ACTIVE credential on same Device must be rejected by partial unique index
    pub2, _, raw_hash2 = _gen_key_and_fp()
    dup_active = DeviceCredential(
        device_id=dev.id,
        public_key=pub2,
        key_fingerprint=raw_hash2,
        credential_version=next_ver,
        status=CredentialStatus.ACTIVE,
    )
    db_session.add(dup_active)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()

    # Multiple REVOKED historical credentials are permitted
    for v in (2, 3):
        p, _, h = _gen_key_and_fp()
        db_session.add(
            DeviceCredential(
                device_id=dev_id,
                public_key=p,
                key_fingerprint=h,
                credential_version=v,
                status=CredentialStatus.REVOKED,
                revoked_at=datetime.now(timezone.utc),
            )
        )
    await db_session.commit()

    next_ver_after = await CommercialAndLicensingService.allocate_next_credential_version(db_session, dev_id)
    assert next_ver_after == 4
