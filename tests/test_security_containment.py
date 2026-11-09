import pytest
from httpx import AsyncClient
from app.core.security import create_email_verification_token
from app.core.config import settings


@pytest.mark.asyncio
async def test_token_type_confusion_prevention(client: AsyncClient):
    """
    Ensure email verification tokens CANNOT be used as access tokens
    to access protected API endpoints.
    """
    # 1. Register a user
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "victim@bbcafe.com",
            "password": "Password123!",
            "first_name": "Vic",
            "last_name": "Tim",
        },
    )
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]

    # 2. Forge an email verification token for this user
    email_token = create_email_verification_token(user_id, "victim@bbcafe.com")

    # 3. Attempt to call protected /api/v1/organizations using email verification token as Bearer
    protected_res = await client.get(
        "/api/v1/organizations",
        headers={"Authorization": f"Bearer {email_token}"},
    )
    # Must fail with 401 because token type is 'email_verification', not 'access'
    assert protected_res.status_code == 401
    assert "access token required" in protected_res.json()["detail"].lower()


@pytest.mark.asyncio
async def test_platform_admin_boundary(client: AsyncClient):
    """
    Ensure application registry, plan definition, and subscription creation
    strictly require platform admin authorization.
    """
    # 1. Anonymous request to create application -> 401
    res1 = await client.post(
        "/api/v1/applications",
        json={"code": "ROGUE-APP", "name": "Rogue App", "type": "WEB"},
    )
    assert res1.status_code == 401

    # 2. Request with invalid platform admin key -> 403
    res2 = await client.post(
        "/api/v1/applications",
        json={"code": "ROGUE-APP", "name": "Rogue App", "type": "WEB"},
        headers={"X-Platform-Admin-Key": "wrong-key"},
    )
    assert res2.status_code == 403

    # 3. Request with valid platform admin key -> 201
    res3 = await client.post(
        "/api/v1/applications",
        json={"code": "VALID-APP", "name": "Valid App", "type": "WEB"},
        headers={"X-Platform-Admin-Key": settings.PLATFORM_ADMIN_KEY},
    )
    assert res3.status_code == 201


@pytest.mark.asyncio
async def test_reset_data_endpoint_isolation(client: AsyncClient):
    """
    Test reset-data endpoint security:
    - Rejects invalid secret key with 403
    - Disables endpoint (404) if ENVIRONMENT != 'development'
    """
    # 1. Invalid key in dev -> 403
    bad_res = await client.post(
        "/api/v1/system/reset-data",
        headers={"X-Secret-Key": "invalid-secret"},
    )
    assert bad_res.status_code == 403

    # 2. Switch ENVIRONMENT to production -> 404
    original_env = settings.ENVIRONMENT
    try:
        settings.ENVIRONMENT = "production"
        prod_res = await client.post(
            "/api/v1/system/reset-data",
            headers={"X-Secret-Key": settings.SECRET_KEY},
        )
        assert prod_res.status_code == 404
    finally:
        settings.ENVIRONMENT = original_env


@pytest.mark.asyncio
async def test_redis_fail_closed_in_production(client: AsyncClient):
    """
    Ensure that in production mode, when distributed Redis is unavailable,
    token authentication fails closed (503 Service Unavailable) rather than
    silently falling back to process-local memory.
    """
    from app.core.security import create_access_token
    from app.core import redis as redis_module

    fake_token = create_access_token("00000000-0000-0000-0000-000000000001")
    original_env = settings.ENVIRONMENT
    original_client = redis_module._redis_client

    try:
        settings.ENVIRONMENT = "production"
        # Simulate Redis disconnection
        redis_module._redis_client = None
        settings.REDIS_URL = ""

        res = await client.get(
            "/api/v1/organizations",
            headers={"Authorization": f"Bearer {fake_token}"},
        )
        assert res.status_code == 503
        assert "distributed session revocation service is unavailable" in res.json()["detail"].lower()
    finally:
        settings.ENVIRONMENT = original_env
        redis_module._redis_client = original_client
