from __future__ import annotations

import respx
from httpx import AsyncClient, Response

from app.market_data.brapi import _AVAILABLE_URL
from app.market_data.coingecko import _SEARCH_ENDPOINT
from app.models.ticker_catalog import TickerCatalog


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


async def test_search_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/catalog/search?type=acoes_nacionais&q=PETR")
    assert r.status_code == 401


async def test_empty_query_returns_empty_list(client: AsyncClient) -> None:
    token = await _register_and_login(client, "cat-empty@example.com")
    r = await client.get(
        "/api/catalog/search?type=acoes_nacionais&q=",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


@respx.mock
async def test_search_brapi_stocks(client: AsyncClient) -> None:
    respx.get(_AVAILABLE_URL).mock(
        return_value=Response(200, json={"stocks": ["PETR3", "PETR4", "PETRW"]})
    )
    token = await _register_and_login(client, "cat-brapi@example.com")
    r = await client.get(
        "/api/catalog/search?type=acoes_nacionais&q=PETR",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    names = [c["name"] for c in r.json()]
    assert names == ["PETR3", "PETR4", "PETRW"]


@respx.mock
async def test_search_coingecko_crypto(client: AsyncClient) -> None:
    respx.get(_SEARCH_ENDPOINT).mock(
        return_value=Response(
            200,
            json={
                "coins": [
                    {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                    {"id": "bitcoin-cash", "symbol": "bch", "name": "Bitcoin Cash"},
                ]
            },
        )
    )
    token = await _register_and_login(client, "cat-cg@example.com")
    r = await client.get(
        "/api/catalog/search?type=criptomoedas&q=btc",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body[0]["name"] == "BTC"
    assert body[0]["label"] == "Bitcoin"


async def test_search_unsupported_type_returns_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, "cat-us@example.com")
    # yfinance / US stocks: no search support yet
    r = await client.get(
        "/api/catalog/search?type=acoes_internacionais&q=QQQ",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json() == []


async def _seed_catalog(session_maker) -> None:
    async with session_maker() as session:
        session.add_all(
            [
                TickerCatalog(symbol="PETR3", source="b3"),
                TickerCatalog(symbol="PETR4", source="b3"),
                TickerCatalog(symbol="VALE3", source="b3"),
                TickerCatalog(
                    symbol="BTC", name="Bitcoin", source="crypto", external_id="bitcoin"
                ),
            ]
        )
        await session.commit()


async def test_search_uses_local_b3_catalog(client, session_maker) -> None:
    await _seed_catalog(session_maker)
    token = await _register_and_login(client, "cat-local-b3@example.com")
    r = await client.get(
        "/api/catalog/search?type=acoes_nacionais&q=petr",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    names = sorted(c["name"] for c in r.json())
    assert names == ["PETR3", "PETR4"]


async def test_search_uses_local_crypto_catalog(client, session_maker) -> None:
    await _seed_catalog(session_maker)
    token = await _register_and_login(client, "cat-local-cg@example.com")
    r = await client.get(
        "/api/catalog/search?type=criptomoedas&q=bit",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body[0]["name"] == "BTC"
    assert body[0]["label"] == "Bitcoin"
