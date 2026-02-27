"""test_auth.py — Auth endpoint tests."""
import pytest
import pytest_asyncio


@pytest.mark.asyncio
async def test_register_success(client):
    resp = await client.post("/api/auth/register", json={
        "email":    "new@example.com",
        "username": "newuser",
        "password": "strongpassword123",
    })
    assert resp.status_code == 201
    body = resp.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client):
    payload = {"email": "dup@example.com", "username": "u1", "password": "pass1234567890"}
    await client.post("/api/auth/register", json=payload)
    resp = await client.post("/api/auth/register", json=payload)
    assert resp.status_code == 400
    assert resp.json()["detail"]["code"] == "EMAIL_TAKEN"


@pytest.mark.asyncio
async def test_login_success(client):
    await client.post("/api/auth/register", json={
        "email":    "login@example.com",
        "username": "loginuser",
        "password": "mypassword123",
    })
    resp = await client.post("/api/auth/login", json={
        "email":    "login@example.com",
        "password": "mypassword123",
    })
    assert resp.status_code == 200
    assert "access_token" in resp.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):
    await client.post("/api/auth/register", json={
        "email": "wp@example.com", "username": "wp", "password": "correctpassword"
    })
    resp = await client.post("/api/auth/login", json={
        "email": "wp@example.com", "password": "wrongpassword"
    })
    assert resp.status_code == 401
    assert resp.json()["detail"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_get_me(client, auth_headers):
    resp = await client.get("/api/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_get_me_unauthenticated(client):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401
