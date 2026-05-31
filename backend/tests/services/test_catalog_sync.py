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
