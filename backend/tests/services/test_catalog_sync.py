from __future__ import annotations

from sqlalchemy import select

from app.models.ticker_catalog import TickerCatalog


async def test_ticker_catalog_table_exists(session_maker) -> None:
    async with session_maker() as session:
        session.add(
            TickerCatalog(symbol="PETR4", name=None, source="b3", external_id=None)
        )
        await session.commit()
        rows = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.source == "b3")
            )
        ).scalars().all()
        assert [r.symbol for r in rows] == ["PETR4"]


import respx
from httpx import Response

from app.services.catalog_sync import sync_catalog, _COINGECKO_LIST
from app.market_data.brapi import _AVAILABLE_URL


@respx.mock
async def test_sync_populates_b3_and_crypto(session_maker) -> None:
    respx.get(_AVAILABLE_URL).mock(
        return_value=Response(200, json={"stocks": ["PETR4", "VALE3", "bova11"]})
    )
    respx.get(_COINGECKO_LIST).mock(
        return_value=Response(
            200,
            json=[
                {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                {"id": "ethereum", "symbol": "eth", "name": "Ethereum"},
            ],
        )
    )
    async with session_maker() as session:
        await sync_catalog(session)
        b3 = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.source == "b3")
            )
        ).scalars().all()
        crypto = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.source == "crypto")
            )
        ).scalars().all()
    assert {r.symbol for r in b3} == {"PETR4", "VALE3", "BOVA11"}
    assert {r.symbol for r in crypto} == {"BTC", "ETH"}
    btc = next(r for r in crypto if r.symbol == "BTC")
    assert btc.external_id == "bitcoin"
    assert btc.name == "Bitcoin"


@respx.mock
async def test_sync_resync_updates_not_duplicates(session_maker) -> None:
    respx.get(_AVAILABLE_URL).mock(
        return_value=Response(200, json={"stocks": ["PETR4"]})
    )
    respx.get(_COINGECKO_LIST).mock(return_value=Response(200, json=[]))
    async with session_maker() as session:
        await sync_catalog(session)
        await sync_catalog(session)  # segunda passada
        rows = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.symbol == "PETR4")
            )
        ).scalars().all()
    assert len(rows) == 1


@respx.mock
async def test_sync_dedupes_duplicate_crypto_symbols(session_maker) -> None:
    respx.get(_AVAILABLE_URL).mock(return_value=Response(200, json={"stocks": []}))
    respx.get(_COINGECKO_LIST).mock(
        return_value=Response(
            200,
            json=[
                {"id": "bitcoin", "symbol": "btc", "name": "Bitcoin"},
                {"id": "fake-btc", "symbol": "btc", "name": "Fake BTC"},
            ],
        )
    )
    async with session_maker() as session:
        await sync_catalog(session)
        rows = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.symbol == "BTC")
            )
        ).scalars().all()
    assert len(rows) == 1  # dedup por símbolo evita violar a unique constraint


@respx.mock
async def test_sync_source_failure_keeps_other_source(session_maker) -> None:
    # B3 falha, crypto OK -> crypto ainda popula, sem exceção propagada
    respx.get(_AVAILABLE_URL).mock(return_value=Response(500))
    respx.get(_COINGECKO_LIST).mock(
        return_value=Response(
            200, json=[{"id": "ethereum", "symbol": "eth", "name": "Ethereum"}]
        )
    )
    async with session_maker() as session:
        await sync_catalog(session)
        crypto = (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.source == "crypto")
            )
        ).scalars().all()
    assert [r.symbol for r in crypto] == ["ETH"]
