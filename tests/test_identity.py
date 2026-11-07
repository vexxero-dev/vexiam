import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    res = await client.get("/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy", "service": "VEX IAM"}


@pytest.mark.asyncio
async def test_jwks_endpoint(client: AsyncClient):
    res = await client.get("/.well-known/jwks.json")
    assert res.status_code == 200
    data = res.json()
    assert "keys" in data
    assert data["keys"][0]["alg"] == "EdDSA"


@pytest.mark.asyncio
async def test_register_and_login(client: AsyncClient):
    # Register
    reg_payload = {
        "email": "cashier@vexxero.com",
        "password": "StrongPassword123!",
        "first_name": "Alex",
        "last_name": "Smith",
        "phone": "+1234567890",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201, reg_res.text
    user_data = reg_res.json()
    assert user_data["email"] == "cashier@vexxero.com"
    assert user_data["profile"]["first_name"] == "Alex"

    # Login
    login_payload = {
        "email": "cashier@vexxero.com",
        "password": "StrongPassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200, login_res.text
    token_data = login_res.json()
    assert "access_token" in token_data
    assert token_data["token_type"] == "bearer"
    assert token_data["user"]["email"] == "cashier@vexxero.com"



@pytest.mark.asyncio
async def test_email_verification_flow(client: AsyncClient):
    from app.core.security import create_email_verification_token
    import uuid

    # 1. Register a user
    email = f"verify_{uuid.uuid4().hex[:6]}@vexxero.com"
    reg_payload = {
        "email": email,
        "password": "Password123!",
        "first_name": "Test",
        "last_name": "User",
    }
    reg_res = await client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["id"]
    assert reg_res.json()["email_verified"] is False
    assert reg_res.json()["status"] == "PENDING_VERIFICATION"

    # 2. Verify with valid token
    token = create_email_verification_token(user_id, email)
    verify_res = await client.post("/api/v1/auth/verify-email", json={"token": token})
    assert verify_res.status_code == 200
    assert verify_res.json()["email_verified"] is True
    assert verify_res.json()["status"] == "ACTIVE"
