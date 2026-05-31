"""Refresh all auto-refreshable positions for a given portfolio."""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.market_data.base import AdapterError
from app.market_data.registry import adapter_for_asset_type
from app.models.portfolio import Portfolio
from app.models.position import Position

logger = logging.getLogger(__name__)


@dataclass
class Failure:
    name: str
    reason: str


@dataclass
class RefreshResult:
    refreshed: int = 0
    skipped_manual: int = 0
    failed: list[Failure] = field(default_factory=list)


async def refresh_portfolio_prices(
    session: AsyncSession, portfolio_id: uuid.UUID
) -> RefreshResult:
    positions = (
        await session.execute(
            select(Position).where(Position.portfolio_id == portfolio_id)
        )
    ).scalars().all()

    result = RefreshResult()

    async def refresh_one(p: Position) -> None:
        routing = adapter_for_asset_type(p.asset_type, p.name)
        if routing is None:
            result.skipped_manual += 1
            return
        adapter, external_id = routing
        try:
            quote = await adapter.fetch_price(external_id)
        except AdapterError as e:
            result.failed.append(Failure(name=p.name, reason=str(e)))
            return

        # One-shot migration: if an RF position's current_price was None
        # (legacy amount-in-BRL shape) and a Tesouro price arrives, convert
        # amount from BRL to units. Safe because private RF never reaches
        # this branch (the registry returns None for it), so we know this
        # must be a Tesouro match.
        if (
            p.asset_type in ("rendafixa", "rendafixa_internacional")
            and p.current_price is None
            and quote.price_brl > 0
        ):
            p.amount = p.amount / quote.price_brl

        p.current_price = quote.price_brl
        p.price_updated_at = datetime.now(timezone.utc)
        result.refreshed += 1

    # Run adapters in parallel; a failure in one doesn't block others.
    await asyncio.gather(*(refresh_one(p) for p in positions))
    await session.commit()
    return result


async def refresh_all_portfolios(session: AsyncSession) -> int:
    """Refresh every portfolio in the DB. Used by the scheduled daily job.
    A failure in one portfolio is logged and skipped, never aborting the rest.
    Returns the total number of positions refreshed across all portfolios."""
    portfolios = (await session.execute(select(Portfolio))).scalars().all()
    total = 0
    for pf in portfolios:
        try:
            res = await refresh_portfolio_prices(session, pf.id)
            total += res.refreshed
        except Exception:
            logger.exception("price refresh failed for portfolio %s", pf.id)
    return total
