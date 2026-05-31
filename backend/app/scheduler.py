"""Background scheduler: daily price refresh + weekly catalog sync.

Uses APScheduler's AsyncIOScheduler so jobs run on the FastAPI event loop.
Started/stopped by the app lifespan (see app/main.py). Each job opens its
own DB session (it runs outside any request scope) and swallows/logs its
own errors so a single failure never kills the scheduler.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.core.config import Settings
from app.core.db import get_async_session_maker
from app.models.portfolio import Portfolio  # noqa: F401  (ensures table registered)
from app.models.ticker_catalog import TickerCatalog
from app.services.catalog_sync import sync_catalog
from app.services.refresh_prices import refresh_all_portfolios

logger = logging.getLogger(__name__)


async def refresh_prices_job() -> None:
    maker = get_async_session_maker()
    async with maker() as session:
        try:
            n = await refresh_all_portfolios(session)
            logger.info("scheduled refresh: %s positions updated", n)
        except Exception:
            logger.exception("scheduled price refresh failed")


async def sync_catalog_job() -> None:
    maker = get_async_session_maker()
    async with maker() as session:
        try:
            await sync_catalog(session)
            logger.info("scheduled catalog sync done")
        except Exception:
            logger.exception("scheduled catalog sync failed")


async def run_startup_jobs() -> None:
    """Fire-and-forget at boot: sync the catalog if empty so autocomplete
    works on a fresh deploy, then refresh prices once."""
    maker = get_async_session_maker()
    async with maker() as session:
        empty = (
            await session.execute(select(TickerCatalog.id).limit(1))
        ).first() is None
    if empty:
        await sync_catalog_job()
    await refresh_prices_job()


def build_scheduler(settings: Settings) -> AsyncIOScheduler:
    tz = settings.timezone
    sched = AsyncIOScheduler(timezone=tz)
    sched.add_job(
        refresh_prices_job,
        CronTrigger(day_of_week="mon-fri", hour=18, minute=30, timezone=tz),
        id="refresh_prices",
        replace_existing=True,
    )
    sched.add_job(
        sync_catalog_job,
        CronTrigger(day_of_week="sun", hour=3, minute=0, timezone=tz),
        id="sync_catalog",
        replace_existing=True,
    )
    return sched
