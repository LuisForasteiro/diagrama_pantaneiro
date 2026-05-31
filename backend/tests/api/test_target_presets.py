from __future__ import annotations

from httpx import AsyncClient


async def _register_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    return r.json()["access_token"]


def _valid_values() -> dict[str, int]:
    return {
        "acoes_nacionais": 30,
        "acoes_internacionais": 10,
        "etfs_nacionais": 5,
        "etfs_internacionais": 5,
        "fundos_imobiliarios": 15,
        "reits": 5,
        "criptomoedas": 10,
        "rendafixa": 15,
        "rendafixa_internacional": 5,
    }


async def test_presets_require_auth(client: AsyncClient) -> None:
    r = await client.get("/api/target-presets")
    assert r.status_code == 401


async def test_post_preset_happy_path(client: AsyncClient) -> None:
    token = await _register_login(client, "p1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/target-presets",
        json={"name": "Agressivo", "values": _valid_values()},
        headers=headers,
    )
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Agressivo"
    assert body["values"]["acoes_nacionais"] == 30
    assert "id" in body and "createdAt" in body

    r2 = await client.get("/api/target-presets", headers=headers)
    assert r2.status_code == 200
    rows = r2.json()
    assert len(rows) == 1
    assert rows[0]["name"] == "Agressivo"


async def test_post_preset_rejects_sum_not_100(client: AsyncClient) -> None:
    token = await _register_login(client, "p2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    bad = _valid_values()
    bad["acoes_nacionais"] = 50
    r = await client.post(
        "/api/target-presets",
        json={"name": "Nope", "values": bad},
        headers=headers,
    )
    assert r.status_code == 422


async def test_post_preset_rejects_long_name(client: AsyncClient) -> None:
    token = await _register_login(client, "p3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/target-presets",
        json={"name": "x" * 49, "values": _valid_values()},
        headers=headers,
    )
    assert r.status_code == 422


async def test_post_preset_rejects_blank_name(client: AsyncClient) -> None:
    token = await _register_login(client, "p3b@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.post(
        "/api/target-presets",
        json={"name": "   ", "values": _valid_values()},
        headers=headers,
    )
    assert r.status_code == 422


async def test_post_preset_duplicate_name_returns_409(client: AsyncClient) -> None:
    token = await _register_login(client, "p4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    body = {"name": "Dup", "values": _valid_values()}
    r1 = await client.post("/api/target-presets", json=body, headers=headers)
    assert r1.status_code == 201
    r2 = await client.post("/api/target-presets", json=body, headers=headers)
    assert r2.status_code == 409

    rows = (await client.get("/api/target-presets", headers=headers)).json()
    assert len(rows) == 1


async def test_delete_preset_removes_only_target_preset(
    client: AsyncClient,
) -> None:
    token = await _register_login(client, "p5@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    a = await client.post(
        "/api/target-presets",
        json={"name": "A", "values": _valid_values()},
        headers=headers,
    )
    await client.post(
        "/api/target-presets",
        json={"name": "B", "values": _valid_values()},
        headers=headers,
    )
    a_id = a.json()["id"]

    r = await client.delete(f"/api/target-presets/{a_id}", headers=headers)
    assert r.status_code == 204

    rows = (await client.get("/api/target-presets", headers=headers)).json()
    assert len(rows) == 1
    assert rows[0]["name"] == "B"


async def test_delete_preset_does_not_touch_investment_targets(
    client: AsyncClient,
) -> None:
    token = await _register_login(client, "p6@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    await client.get("/api/positions", headers=headers)
    targets_before = (await client.get("/api/targets", headers=headers)).json()

    created = await client.post(
        "/api/target-presets",
        json={"name": "Temp", "values": _valid_values()},
        headers=headers,
    )
    preset_id = created.json()["id"]

    r = await client.delete(f"/api/target-presets/{preset_id}", headers=headers)
    assert r.status_code == 204

    targets_after = (await client.get("/api/targets", headers=headers)).json()
    assert targets_before == targets_after


async def test_presets_user_isolation(client: AsyncClient) -> None:
    token_a = await _register_login(client, "iso-a@example.com")
    token_b = await _register_login(client, "iso-b@example.com")

    await client.post(
        "/api/target-presets",
        json={"name": "OnlyA", "values": _valid_values()},
        headers={"Authorization": f"Bearer {token_a}"},
    )

    b_headers = {"Authorization": f"Bearer {token_b}"}
    r = await client.get("/api/target-presets", headers=b_headers)
    assert r.status_code == 200
    assert r.json() == []

    a_headers = {"Authorization": f"Bearer {token_a}"}
    a_rows = (await client.get("/api/target-presets", headers=a_headers)).json()
    a_preset_id = a_rows[0]["id"]
    r_del = await client.delete(
        f"/api/target-presets/{a_preset_id}", headers=b_headers
    )
    assert r_del.status_code == 404

    a_after = (await client.get("/api/target-presets", headers=a_headers)).json()
    assert len(a_after) == 1
