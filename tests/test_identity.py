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
