from __future__ import annotations

import pytest
from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    return r.json()["access_token"]


async def test_get_positions_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/positions")
    assert r.status_code == 401


async def test_get_positions_auto_imports_on_first_call(client: AsyncClient) -> None:
    token = await _register_and_login(client, "first@example.com")
    r = await client.get("/api/positions", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    positions = r.json()
    assert len(positions) == 19
    names = {p["name"] for p in positions}
    assert "VALE3" in names
    assert "BTC" in names
    assert "LCI INTER 90,00" in names


async def test_get_positions_is_user_scoped(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "a@example.com")
    await client.get("/api/positions", headers={"Authorization": f"Bearer {token_a}"})

    token_b = await _register_and_login(client, "b@example.com")
    r = await client.get("/api/positions", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 200
    # B gets their own seed, not the 38 total
    assert len(r.json()) == 19


async def test_create_position(client: AsyncClient) -> None:
    token = await _register_and_login(client, "create@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/api/positions", headers=headers)  # seed

    r = await client.post(
        "/api/positions",
        json={
            "name": "PETR4",
            "assetType": "acoes_nacionais",
            "amount": 100,
            "currentPrice": 38.50,
            "strength": 5,
        },
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "PETR4"
    assert body["assetType"] == "acoes_nacionais"
    assert body["amount"] == 100
    assert body["currentPrice"] == 38.50
    assert body["strength"] == 5
    assert body["source"] == "user"


async def test_create_position_requires_auth(client: AsyncClient) -> None:
    r = await client.post(
        "/api/positions",
        json={
            "name": "X",
            "assetType": "acoes_nacionais",
            "amount": 1,
            "strength": 1,
        },
    )
    assert r.status_code == 401


async def test_update_position_changes_amount_and_strength(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, "update@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    rows = (await client.get("/api/positions", headers=headers)).json()
    vale3 = next(p for p in rows if p["name"] == "VALE3")

    r = await client.patch(
        f"/api/positions/{vale3['id']}",
        json={"amount": 75, "strength": 9},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["amount"] == 75
    assert body["strength"] == 9


async def test_update_position_rejects_cross_user(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "owner@example.com")
    rows_a = (
        await client.get(
            "/api/positions", headers={"Authorization": f"Bearer {token_a}"}
        )
    ).json()
    p_id = rows_a[0]["id"]

    token_b = await _register_and_login(client, "intruder@example.com")
    r = await client.patch(
        f"/api/positions/{p_id}",
        json={"amount": 999},
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


async def test_delete_position(client: AsyncClient) -> None:
    token = await _register_and_login(client, "delete@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    rows = (await client.get("/api/positions", headers=headers)).json()
    taee4 = next(p for p in rows if p["name"] == "TAEE4")

    r = await client.delete(f"/api/positions/{taee4['id']}", headers=headers)
    assert r.status_code == 204

    rows_after = (await client.get("/api/positions", headers=headers)).json()
    assert taee4["id"] not in {p["id"] for p in rows_after}


async def test_delete_position_rejects_cross_user(client: AsyncClient) -> None:
    token_a = await _register_and_login(client, "owner2@example.com")
    rows = (
        await client.get(
            "/api/positions", headers={"Authorization": f"Bearer {token_a}"}
        )
    ).json()
    p_id = rows[0]["id"]

    token_b = await _register_and_login(client, "intruder2@example.com")
    r = await client.delete(
        f"/api/positions/{p_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


async def test_create_equity_with_responses_recomputes_strength(
    client: AsyncClient,
) -> None:
    """Creating an equity with diagram_responses should yield strength = 2*yes - 11."""
    token = await _register_and_login(client, "score1@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    # Seed to populate the question bank
    await client.get("/api/positions", headers=headers)

    # Get a few known cerrado question IDs
    questions = (
        await client.get(
            "/api/diagram-questions?diagram=diagrama-do-cerrado", headers=headers
        )
    ).json()
    assert len(questions) == 11

    chosen = [q["id"] for q in questions[:7]]  # 7 yes answers
    r = await client.post(
        "/api/positions",
        json={
            "name": "MGLU3",
            "assetType": "acoes_nacionais",
            "amount": 1000,
            "currentPrice": 2.30,
            "strength": 0,  # should be overwritten
            "diagramResponses": chosen,
        },
        headers=headers,
    )
    assert r.status_code == 201
    # 2 * 7 - 11 = 3
    assert r.json()["strength"] == 3


async def test_patch_diagram_responses_recomputes_strength(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, "score2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    rows = (await client.get("/api/positions", headers=headers)).json()
    vale3 = next(p for p in rows if p["name"] == "VALE3")

    questions = (
        await client.get(
            "/api/diagram-questions?diagram=diagrama-do-cerrado", headers=headers
        )
    ).json()
    new_responses = [q["id"] for q in questions[:10]]  # 10 yes

    r = await client.patch(
        f"/api/positions/{vale3['id']}",
        json={"diagramResponses": new_responses},
        headers=headers,
    )
    assert r.status_code == 200
    # 2 * 10 - 11 = 9
    assert r.json()["strength"] == 9


async def test_crypto_strength_not_recomputed(client: AsyncClient) -> None:
    """Crypto has no diagram. Supplied strength passes through as-is."""
    token = await _register_and_login(client, "score3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/api/positions", headers=headers)

    r = await client.post(
        "/api/positions",
        json={
            "name": "ETH",
            "assetType": "criptomoedas",
            "amount": 0.5,
            "currentPrice": 15000,
            "strength": 7,
            "diagramResponses": ["ignored"],  # should not affect strength
        },
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["strength"] == 7
