"""Populate the local ticker_catalog from free upstream sources.

Run weekly by the scheduler. Each source is independent: if one upstream
fails, the rows already cached for that source are left untouched — we never
wipe the catalog on a network blip.
"""

from __future__ import annotations

import logging

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.brapi import _AVAILABLE_URL
from app.models.ticker_catalog import TickerCatalog

logger = logging.getLogger(__name__)

_COINGECKO_LIST = "https://api.coingecko.com/api/v3/coins/list"

# (symbol, name, external_id)
_Row = tuple[str, str | None, str | None]


async def _fetch_b3() -> list[_Row]:
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(_AVAILABLE_URL)
        r.raise_for_status()
        data = r.json()
    return [(s.upper(), None, None) for s in (data.get("stocks") or []) if s]


async def _fetch_crypto() -> list[_Row]:
    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(_COINGECKO_LIST)
        r.raise_for_status()
        data = r.json()
    # CoinGecko reuses symbols across many coins; dedup by symbol (first wins)
    # so the (source, symbol) unique constraint holds.
    seen: dict[str, _Row] = {}
    for c in data:
        sym = (c.get("symbol") or "").upper()
        if sym and sym not in seen:
            seen[sym] = (sym, c.get("name"), c.get("id"))
    return list(seen.values())


async def _upsert(session: AsyncSession, source: str, rows: list[_Row]) -> None:
    existing = {
        r.symbol: r
        for r in (
            await session.execute(
                select(TickerCatalog).where(TickerCatalog.source == source)
            )
        ).scalars().all()
    }
    for symbol, name, external_id in rows:
        row = existing.get(symbol)
        if row is None:
            session.add(
                TickerCatalog(
                    symbol=symbol, name=name, source=source, external_id=external_id
                )
            )
        else:
            row.name = name
            row.external_id = external_id


async def sync_catalog(session: AsyncSession) -> None:
    for source, fetch in (("b3", _fetch_b3), ("crypto", _fetch_crypto)):
        try:
            rows = await fetch()
        except Exception:
            logger.exception("catalog sync: source %s failed, keeping cache", source)
            continue
        await _upsert(session, source, rows)
    await session.commit()
