from __future__ import annotations

from httpx import AsyncClient


async def _seed(client: AsyncClient, email: str = "tgt@example.com") -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    token = r.json()["access_token"]
    # Trigger seeding by calling /positions once
    await client.get("/api/positions", headers={"Authorization": f"Bearer {token}"})
    return token


async def test_targets_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/targets")
    assert r.status_code == 401


async def test_targets_returns_seeded_rows(client: AsyncClient) -> None:
    token = await _seed(client)
    r = await client.get("/api/targets", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    targets = r.json()
    assert len(targets) == 7

    percentages = {t["assetType"]: t["targetPercentage"] for t in targets}
    # Captured AUVP fixture:
    # 5% Acoes Int, 55% Acoes Nac, 0 FIIs/REITs, 20 Cripto, 20 RF, 0 RF Int
    assert percentages["acoes_nacionais"] == 55.0
    assert percentages["criptomoedas"] == 20.0
    assert sum(percentages.values()) == 100.0


async def test_put_targets_happy_path(client: AsyncClient) -> None:
    token = await _seed(client, email="put1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 30},
            {"assetType": "acoes_internacionais", "targetPercentage": 10},
            {"assetType": "etfs_nacionais", "targetPercentage": 5},
            {"assetType": "etfs_internacionais", "targetPercentage": 5},
            {"assetType": "fundos_imobiliarios", "targetPercentage": 15},
            {"assetType": "reits", "targetPercentage": 5},
            {"assetType": "criptomoedas", "targetPercentage": 10},
            {"assetType": "rendafixa", "targetPercentage": 15},
            {"assetType": "rendafixa_internacional", "targetPercentage": 5},
        ]
    }
    r = await client.put("/api/targets", json=body, headers=headers)
    assert r.status_code == 200
    returned = {t["assetType"]: t["targetPercentage"] for t in r.json()}
    assert returned["acoes_nacionais"] == 30
    assert returned["fundos_imobiliarios"] == 15
    assert returned["etfs_nacionais"] == 5
    assert sum(returned.values()) == 100

    r2 = await client.get("/api/targets", headers=headers)
    persisted = {t["assetType"]: t["targetPercentage"] for t in r2.json()}
    assert persisted == returned


async def test_put_targets_rejects_sum_not_100(client: AsyncClient) -> None:
    token = await _seed(client, email="put2@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 30},
            {"assetType": "acoes_internacionais", "targetPercentage": 10},
            {"assetType": "etfs_nacionais", "targetPercentage": 5},
            {"assetType": "etfs_internacionais", "targetPercentage": 5},
            {"assetType": "fundos_imobiliarios", "targetPercentage": 15},
            {"assetType": "reits", "targetPercentage": 5},
            {"assetType": "criptomoedas", "targetPercentage": 10},
            {"assetType": "rendafixa", "targetPercentage": 15},
            {"assetType": "rendafixa_internacional", "targetPercentage": 4},
        ]
    }
    r = await client.put("/api/targets", json=body, headers=headers)
    assert r.status_code == 422


async def test_put_targets_rejects_decimal(client: AsyncClient) -> None:
    token = await _seed(client, email="put3@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 30.5},
            {"assetType": "acoes_internacionais", "targetPercentage": 9.5},
            {"assetType": "etfs_nacionais", "targetPercentage": 5},
            {"assetType": "etfs_internacionais", "targetPercentage": 5},
            {"assetType": "fundos_imobiliarios", "targetPercentage": 15},
            {"assetType": "reits", "targetPercentage": 5},
            {"assetType": "criptomoedas", "targetPercentage": 10},
            {"assetType": "rendafixa", "targetPercentage": 15},
            {"assetType": "rendafixa_internacional", "targetPercentage": 5},
        ]
    }
    r = await client.put("/api/targets", json=body, headers=headers)
    assert r.status_code == 422


async def test_put_targets_rejects_duplicate_class(client: AsyncClient) -> None:
    token = await _seed(client, email="put4@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 50},
            {"assetType": "acoes_nacionais", "targetPercentage": 50},
            {"assetType": "etfs_nacionais", "targetPercentage": 0},
            {"assetType": "etfs_internacionais", "targetPercentage": 0},
            {"assetType": "fundos_imobiliarios", "targetPercentage": 0},
            {"assetType": "reits", "targetPercentage": 0},
            {"assetType": "criptomoedas", "targetPercentage": 0},
            {"assetType": "rendafixa", "targetPercentage": 0},
            {"assetType": "rendafixa_internacional", "targetPercentage": 0},
        ]
    }
    r = await client.put("/api/targets", json=body, headers=headers)
    assert r.status_code == 422


async def test_put_targets_rejects_missing_class(client: AsyncClient) -> None:
    token = await _seed(client, email="put5@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 100},
        ]
    }
    r = await client.put("/api/targets", json=body, headers=headers)
    assert r.status_code == 422


async def test_put_targets_idempotent(client: AsyncClient) -> None:
    token = await _seed(client, email="put6@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    body = {
        "targets": [
            {"assetType": "acoes_nacionais", "targetPercentage": 20},
            {"assetType": "acoes_internacionais", "targetPercentage": 10},
            {"assetType": "etfs_nacionais", "targetPercentage": 5},
            {"assetType": "etfs_internacionais", "targetPercentage": 5},
            {"assetType": "fundos_imobiliarios", "targetPercentage": 10},
            {"assetType": "reits", "targetPercentage": 10},
            {"assetType": "criptomoedas", "targetPercentage": 10},
            {"assetType": "rendafixa", "targetPercentage": 15},
            {"assetType": "rendafixa_internacional", "targetPercentage": 15},
        ]
    }
    await client.put("/api/targets", json=body, headers=headers)
    await client.put("/api/targets", json=body, headers=headers)

    r = await client.get("/api/targets", headers=headers)
    rows = r.json()
    assert len(rows) == 9


async def test_put_targets_requires_auth(client: AsyncClient) -> None:
    body = {"targets": []}
    r = await client.put("/api/targets", json=body)
    assert r.status_code == 401
