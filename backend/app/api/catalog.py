"""Catalog search endpoint — autocomplete for the add-position form.

B3 and crypto are served from the local `ticker_catalog` table (populated
weekly by the scheduler) for instant, rate-limit-free lookups. If the table
is empty for that source (cold start before the first sync) we fall back to
the live adapter. Tesouro stays live — its CSV is already cached 6h in memory.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.core.db import get_async_session
from app.market_data.brapi import BrapiAdapter
from app.market_data.coingecko import CoinGeckoAdapter
from app.market_data.tesouro import TesouroAdapter
from app.models.ticker_catalog import TickerCatalog
from app.models.user import User
from app.schemas.catalog import CandidateOut

router = APIRouter(prefix="/api/catalog", tags=["catalog"])

_brapi = BrapiAdapter()
_coingecko = CoinGeckoAdapter()
_tesouro = TesouroAdapter()

# asset_type -> ticker_catalog.source
_SOURCE_FOR_TYPE = {
    "acoes_nacionais": "b3",
    "fundos_imobiliarios": "b3",
    "etfs_nacionais": "b3",
    "criptomoedas": "crypto",
}


async def _local_search(
    session: AsyncSession, source: str, q: str
) -> list[CandidateOut]:
    rows = (
        await session.execute(
            select(TickerCatalog)
            .where(
                TickerCatalog.source == source,
                or_(
                    TickerCatalog.symbol.ilike(f"{q}%"),
                    TickerCatalog.name.ilike(f"%{q}%"),
                ),
            )
            .order_by(TickerCatalog.symbol)
            .limit(20)
        )
    ).scalars().all()
    return [CandidateOut(name=r.symbol, label=r.name) for r in rows]


async def _source_is_empty(session: AsyncSession, source: str) -> bool:
    row = (
        await session.execute(
            select(TickerCatalog.id).where(TickerCatalog.source == source).limit(1)
        )
    ).first()
    return row is None


@router.get("/search", response_model=list[CandidateOut])
async def search(
    type: str = Query(..., description="asset_type to search within"),
    q: str = Query(default="", max_length=64),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[CandidateOut]:
    q = q.strip()
    if not q:
        return []

    source = _SOURCE_FOR_TYPE.get(type)
    if source is not None:
        if not await _source_is_empty(session, source):
            return await _local_search(session, source, q)
        # Cold-start fallback: hit the live adapter until the first sync runs.
        adapter = _brapi if source == "b3" else _coingecko
        candidates = await adapter.search(q)
    elif type == "rendafixa":
        candidates = await _tesouro.search(q)
    else:
        candidates = []

    return [
        CandidateOut(
            name=c.name, label=c.label, current_price_brl=c.current_price_brl
        )
        for c in candidates
    ]
