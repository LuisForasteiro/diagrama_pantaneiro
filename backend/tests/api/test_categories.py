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


async def _leaf_ids(client: AsyncClient, headers: dict) -> dict[str, str]:
    """name -> id para as folhas da árvore _valid_tree()."""
    tree = (await client.get("/api/categories", headers=headers)).json()
    out: dict[str, str] = {}
    for g in tree["groups"]:
        if g["children"]:
            for c in g["children"]:
                out[c["name"]] = c["id"]
        else:
            out[g["name"]] = g["id"]
    return out


async def test_create_position_with_leaf_category(client: AsyncClient) -> None:
    headers = await _login(client, "cat-pos-create@example.com")
    await client.get("/api/positions", headers=headers)  # auto-seed
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    leaves = await _leaf_ids(client, headers)

    r = await client.post(
        "/api/positions",
        json={
            "name": "BBAS3",
            "assetType": "acoes_nacionais",
            "amount": 100,
            "currentPrice": 50,
            "strength": 5,
            "categoryId": leaves["Ações"],
        },
        headers=headers,
    )
    assert r.status_code == 201
    assert r.json()["categoryId"] == leaves["Ações"]


async def test_create_position_rejects_group_as_category(client: AsyncClient) -> None:
    headers = await _login(client, "cat-pos-grp@example.com")
    await client.get("/api/positions", headers=headers)
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    tree = (await client.get("/api/categories", headers=headers)).json()
    brasil_group_id = next(g["id"] for g in tree["groups"] if g["name"] == "Brasil")

    r = await client.post(
        "/api/positions",
        json={
            "name": "X",
            "assetType": "acoes_nacionais",
            "amount": 1,
            "currentPrice": 1,
            "strength": 5,
            "categoryId": brasil_group_id,  # grupo com filhos: não é folha
        },
        headers=headers,
    )
    assert r.status_code == 422


async def test_patch_position_sets_category(client: AsyncClient) -> None:
    headers = await _login(client, "cat-pos-patch@example.com")
    await client.get("/api/positions", headers=headers)
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    leaves = await _leaf_ids(client, headers)
    btc_leaf = leaves["Bitcoin"]

    created = await client.post(
        "/api/positions",
        json={
            "name": "BTC",
            "assetType": "criptomoedas",
            "amount": 0.1,
            "currentPrice": 100000,
            "strength": 5,
        },
        headers=headers,
    )
    pid = created.json()["id"]
    r = await client.patch(
        f"/api/positions/{pid}",
        json={"categoryId": btc_leaf},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["categoryId"] == btc_leaf


def _leaf_id_named(tree: dict, name: str) -> str:
    for g in tree["groups"]:
        if g["name"] == name and not g["children"]:
            return g["id"]
        for c in g["children"]:
            if c["name"] == name:
                return c["id"]
    raise AssertionError(f"leaf {name} not found")


async def test_put_with_ids_preserves_categories_and_links(client) -> None:
    """Editing weights (resending the tree WITH ids) must keep the same
    category ids and keep positions assigned — no orphaning."""
    headers = await _login(client, "cat-edit-preserve@example.com")
    await client.get("/api/positions", headers=headers)  # auto-seed
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    tree = (await client.get("/api/categories", headers=headers)).json()
    acoes = _leaf_id_named(tree, "Ações")

    pos = (await client.get("/api/positions", headers=headers)).json()
    pid = next(p["id"] for p in pos if p["assetType"] == "acoes_nacionais")
    await client.patch(
        f"/api/positions/{pid}", json={"categoryId": acoes}, headers=headers
    )

    # Resend the same tree (ids included) with changed group weights.
    tree["groups"][0]["weightPct"] = 30  # Bitcoin
    tree["groups"][1]["weightPct"] = 35  # Brasil  (30+35+35 = 100)
    r = await client.put("/api/categories", json=tree, headers=headers)
    assert r.status_code == 200
    tree2 = r.json()

    assert _leaf_id_named(tree2, "Ações") == acoes  # id preservado
    pos2 = (await client.get("/api/positions", headers=headers)).json()
    assert next(p for p in pos2 if p["id"] == pid)["categoryId"] == acoes  # vínculo


async def test_put_removing_leaf_nulls_its_positions(client) -> None:
    """Removing a leaf must NULL its positions' categoryId (not leave it
    dangling), regardless of SQLite FK enforcement."""
    headers = await _login(client, "cat-edit-remove@example.com")
    await client.get("/api/positions", headers=headers)
    await client.put("/api/categories", json=_valid_tree(), headers=headers)
    tree = (await client.get("/api/categories", headers=headers)).json()
    btc = _leaf_id_named(tree, "Bitcoin")

    created = await client.post(
        "/api/positions",
        json={
            "name": "BTC",
            "assetType": "criptomoedas",
            "amount": 0.1,
            "currentPrice": 100000,
            "strength": 5,
            "categoryId": btc,
        },
        headers=headers,
    )
    pid = created.json()["id"]

    # Remove the Bitcoin group; rebalance the rest to 100.
    new_tree = {"groups": [g for g in tree["groups"] if g["name"] != "Bitcoin"]}
    new_tree["groups"][0]["weightPct"] = 50  # Brasil
    new_tree["groups"][1]["weightPct"] = 50  # Internacional
    r = await client.put("/api/categories", json=new_tree, headers=headers)
    assert r.status_code == 200

    pos = (await client.get("/api/positions", headers=headers)).json()
    assert next(p for p in pos if p["id"] == pid)["categoryId"] is None
