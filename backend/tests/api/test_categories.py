from __future__ import annotations

from httpx import AsyncClient


async def _login(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post(
        "/api/auth/register", json={"email": email, "password": "StrongPass!123"}
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _valid_tree() -> dict:
    return {
        "groups": [
            {"name": "Bitcoin", "weightPct": 40, "children": []},
            {
                "name": "Brasil",
                "weightPct": 25,
                "children": [
                    {"name": "Ações", "weightPct": 50},
                    {"name": "Renda Fixa", "weightPct": 50},
                ],
            },
            {
                "name": "Internacional",
                "weightPct": 35,
                "children": [{"name": "Ações americanas", "weightPct": 100}],
            },
        ]
    }


async def test_categories_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/api/categories")).status_code == 401


async def test_get_empty_tree(client: AsyncClient) -> None:
    headers = await _login(client, "cat-tree-empty@example.com")
    r = await client.get("/api/categories", headers=headers)
    assert r.status_code == 200
    assert r.json() == {"groups": []}


async def test_put_then_get_roundtrip(client: AsyncClient) -> None:
    headers = await _login(client, "cat-tree-rt@example.com")
    r = await client.put("/api/categories", json=_valid_tree(), headers=headers)
    assert r.status_code == 200
    body = r.json()
    names = [g["name"] for g in body["groups"]]
    assert names == ["Bitcoin", "Brasil", "Internacional"]
    brasil = next(g for g in body["groups"] if g["name"] == "Brasil")
    assert [c["name"] for c in brasil["children"]] == ["Ações", "Renda Fixa"]
    assert all(g["id"] for g in body["groups"])

    got = (await client.get("/api/categories", headers=headers)).json()
    assert [g["name"] for g in got["groups"]] == names


async def test_put_replaces_previous_tree(client: AsyncClient) -> None:
    headers = await _login(client, "cat-tree-replace@example.com")
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    smaller = {"groups": [{"name": "Tudo", "weightPct": 100, "children": []}]}
    await client.put("/api/categories", json=smaller, headers=headers)
    got = (await client.get("/api/categories", headers=headers)).json()
    assert [g["name"] for g in got["groups"]] == ["Tudo"]


async def test_put_rejects_group_sum_not_100(client: AsyncClient) -> None:
    headers = await _login(client, "cat-tree-bad@example.com")
    bad = {"groups": [{"name": "A", "weightPct": 40, "children": []}]}
    r = await client.put("/api/categories", json=bad, headers=headers)
    assert r.status_code == 422


async def test_put_rejects_children_sum_not_100(client: AsyncClient) -> None:
    headers = await _login(client, "cat-tree-bad2@example.com")
    bad = {
        "groups": [
            {
                "name": "G",
                "weightPct": 100,
                "children": [
                    {"name": "C1", "weightPct": 30},
                    {"name": "C2", "weightPct": 30},
                ],
            }
        ]
    }
    r = await client.put("/api/categories", json=bad, headers=headers)
    assert r.status_code == 422
