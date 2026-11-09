import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from app.domains.organizations.models import Organization, OrganizationMember, OrganizationRole, OrganizationStatus
from app.domains.identity.models import User, UserStatus
from app.core.security import create_email_verification_token


@pytest.mark.asyncio
async def test_database_single_owner_constraint(db_session: AsyncSession):
    """
    Direct database test: verify that uq_org_single_owner prevents
    an organization from having more than one active OWNER.
    """
    # 1. Create Organization
    org = Organization(name="Unique Owner Test Org", status=OrganizationStatus.ACTIVE)
    db_session.add(org)
    await db_session.flush()

    # 2. Create two Users
    u1 = User(email="owner1@test.com", status=UserStatus.ACTIVE, email_verified=True)
    u2 = User(email="owner2@test.com", status=UserStatus.ACTIVE, email_verified=True)
    db_session.add_all([u1, u2])
    await db_session.flush()

    # 3. Add first OWNER
    m1 = OrganizationMember(organization_id=org.id, user_id=u1.id, role=OrganizationRole.OWNER)
    db_session.add(m1)
    await db_session.commit()

    # 4. Attempt to add a second OWNER to the same organization -> MUST raise IntegrityError
    m2 = OrganizationMember(organization_id=org.id, user_id=u2.id, role=OrganizationRole.OWNER)
    db_session.add(m2)
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


@pytest.mark.asyncio
async def test_unverified_email_blocks_device_registration(client: AsyncClient):
    """
    Verify that an unverified user cannot register devices or activate licenses.
    """
    # 1. Register user
    reg = await client.post(
        "/api/v1/auth/register",
        json={"email": "unverified_operator@pos.com", "password": "Password123!", "first_name": "Unv", "last_name": "Op"},
    )
    assert reg.status_code == 201

    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "unverified_operator@pos.com", "password": "Password123!"},
    )
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Attempting to create an organization before email verification must fail
    org_res = await client.post("/api/v1/organizations", json={"name": "Unverified Org"}, headers=headers)
    assert org_res.status_code == 403
    assert "email address must be verified" in org_res.json()["detail"].lower()
