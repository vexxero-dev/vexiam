import base64
import hashlib
import uuid
import pytest
import rfc8785
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization
from fastapi import HTTPException
from sqlalchemy import select

from app.domains.identity.models import User
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole
from app.domains.licensing.models import DeviceStatus, CredentialStatus, TerminalSecurityAudit
from app.domains.licensing.schemas import DeviceRegisterRequest
from app.domains.licensing.service import CommercialAndLicensingService


def _gen_keypair():
    priv = ed25519.Ed25519PrivateKey.generate()
    raw_pub = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    pub_b64 = base64.b64encode(raw_pub).decode("utf-8")
    raw_hash = hashlib.sha256(raw_pub).hexdigest()
    return priv, pub_b64, f"VEX-DEV-{raw_hash}"


def _sign_challenge(priv, chal, device_id, org_id, operation):
    payload = {
        "challenge_id": chal.challenge_id,
        "device_id": str(device_id),
        "nonce": chal.nonce,
        "operation": operation,
        "organization_id": str(org_id),
    }
    return base64.b64encode(priv.sign(rfc8785.dumps(payload))).decode("utf-8")


@pytest.mark.asyncio
async def test_milestone_2_2_rotation_recovery_revocation_and_replay(db_session):
    owner = User(id=uuid.uuid4(), email=f"owner_{uuid.uuid4().hex[:6]}@vex.local")
    cashier = User(id=uuid.uuid4(), email=f"cashier_{uuid.uuid4().hex[:6]}@vex.local")
    org = Organization(id=uuid.uuid4(), name="M22 Org")
    db_session.add_all([owner, cashier, org])
    await db_session.flush()
    db_session.add_all([
        OrganizationMember(organization_id=org.id, user_id=owner.id, role=OrganizationRole.OWNER),
        OrganizationMember(organization_id=org.id, user_id=cashier.id, role=OrganizationRole.MEMBER),
    ])
    await db_session.commit()

    _, pub1, fp1 = _gen_keypair()
    dev = await CommercialAndLicensingService.register_device(
        db_session,
        owner.id,
        DeviceRegisterRequest(organization_id=org.id, name="POS M22", fingerprint=fp1, public_key=pub1),
    )

    # 1. Unauthorized user cannot issue challenge
    priv2, pub2, _ = _gen_keypair()
    with pytest.raises(HTTPException) as exc_unauth:
        await CommercialAndLicensingService.create_bound_device_challenge(
            db_session, cashier.id, dev.id, "ROTATE", pub2
        )
    assert exc_unauth.value.status_code == 403

    # 2. Rotate credential (installation_replacement_authorized=False)
    chal_rot = await CommercialAndLicensingService.create_bound_device_challenge(
        db_session, owner.id, dev.id, "ROTATE", pub2
    )
    sig_rot = _sign_challenge(priv2, chal_rot, dev.id, org.id, "ROTATE")
    res_rot = await CommercialAndLicensingService.rotate_terminal_credential(
        db_session, owner.id, dev.id, pub2, chal_rot.challenge_id, sig_rot, reason="Planned key rotation"
    )
    assert res_rot["credential_version"] == 2
    assert res_rot["installation_replacement_authorized"] is False
    assert res_rot["device_status"] == "ACTIVE"

    # 3. Replay of consumed challenge fails (401)
    with pytest.raises(HTTPException) as exc_replay:
        await CommercialAndLicensingService.rotate_terminal_credential(
            db_session, owner.id, dev.id, pub2, chal_rot.challenge_id, sig_rot
        )
    assert exc_replay.value.status_code == 401

    # 4. Recover terminal identity on a REVOKED device: authorizes installation replacement, keeps REVOKED
    dev.status = DeviceStatus.REVOKED
    await db_session.commit()

    priv3, pub3, _ = _gen_keypair()
    chal_rec = await CommercialAndLicensingService.create_bound_device_challenge(
        db_session, owner.id, dev.id, "RECOVER", pub3
    )
    sig_rec = _sign_challenge(priv3, chal_rec, dev.id, org.id, "RECOVER")
    res_rec = await CommercialAndLicensingService.recover_terminal_identity(
        db_session, owner.id, dev.id, pub3, chal_rec.challenge_id, sig_rec, reason="Windows reinstall"
    )
    assert res_rec["credential_version"] == 3
    assert res_rec["installation_replacement_authorized"] is True
    assert res_rec["device_status"] == "REVOKED"

    # 5. Revoke credential without revoking terminal
    res_rev_cred = await CommercialAndLicensingService.revoke_terminal_credential(
        db_session, owner.id, dev.id, res_rec["credential_id"], reason="Key compromise"
    )
    assert res_rev_cred["credential_status"] == CredentialStatus.REVOKED.value
    assert res_rev_cred["device_status"] == "REVOKED"

    # 6. Revoke terminal
    res_rev_term = await CommercialAndLicensingService.revoke_terminal(
        db_session, owner.id, dev.id, reason="Decommissioned"
    )
    assert res_rev_term["device_status"] == "REVOKED"

    audits = (
        await db_session.execute(
            select(TerminalSecurityAudit).where(TerminalSecurityAudit.device_id == dev.id)
        )
    ).scalars().all()
    assert len(audits) == 4
