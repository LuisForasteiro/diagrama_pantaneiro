import pytest
from httpx import AsyncClient


async def test_register_creates_user(client: AsyncClient) -> None:
    response = await client.post(
        "/api/auth/register",
        json={"email": "lucas@example.com", "password": "StrongPass!123"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "lucas@example.com"
    assert "id" in body
    assert "hashed_password" not in body


async def test_register_duplicate_email_fails(client: AsyncClient) -> None:
    payload = {"email": "dup@example.com", "password": "StrongPass!123"}
    r1 = await client.post("/api/auth/register", json=payload)
    assert r1.status_code == 201
    r2 = await client.post("/api/auth/register", json=payload)
    assert r2.status_code == 400


async def test_login_returns_jwt(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"email": "login@example.com", "password": "StrongPass!123"},
    )
    response = await client.post(
        "/api/auth/jwt/login",
        data={"username": "login@example.com", "password": "StrongPass!123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


async def test_users_me_requires_auth(client: AsyncClient) -> None:
    response = await client.get("/api/users/me")
    assert response.status_code == 401


async def test_users_me_returns_current_user(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"email": "me@example.com", "password": "StrongPass!123"},
    )
    login = await client.post(
        "/api/auth/jwt/login",
        data={"username": "me@example.com", "password": "StrongPass!123"},
    )
    token = login.json()["access_token"]

    response = await client.get(
        "/api/users/me", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 200
    assert response.json()["email"] == "me@example.com"
