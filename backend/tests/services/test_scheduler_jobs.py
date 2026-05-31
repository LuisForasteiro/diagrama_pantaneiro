from __future__ import annotations

import uuid

import respx
from httpx import Response
from sqlalchemy import select

from app.market_data import usd_brl
from app.market_data.yfinance_adapter import _CHART_URL
from app.models.portfolio import Portfolio
from app.models.position import Position
from app.services.refresh_prices import refresh_all_portfolios


@respx.mock
async def test_refresh_all_portfolios_updates_every_portfolio(session_maker) -> None:
    usd_brl._reset_cache_for_tests()
    respx.get(usd_brl._ENDPOINT).mock(
        return_value=Response(200, json={"USDBRL": {"bid": "5.0"}})
    )
    respx.get(url__regex=rf"{_CHART_URL}/.*").mock(
        return_value=Response(
            200,
            json={
                "chart": {
                    "result": [
                        {"meta": {"regularMarketPrice": 10.0, "currency": "BRL"}}
                    ]
                }
            },
        )
    )
    uid = uuid.uuid4()
    async with session_maker() as session:
        pf = Portfolio(id=uuid.uuid4(), user_id=uid, name="P1", is_default=True)
        session.add(pf)
        session.add(
            Position(
                id=uuid.uuid4(),
                user_id=uid,
                portfolio_id=pf.id,
                name="VALE3",
                asset_type="acoes_nacionais",
                amount=10,
                current_price=None,
                strength=0,
            )
        )
        await session.commit()
        pid = pf.id

    async with session_maker() as session:
        total = await refresh_all_portfolios(session)
        assert total >= 1

    async with session_maker() as session:
        pos = (
            await session.execute(select(Position).where(Position.portfolio_id == pid))
        ).scalars().all()
    assert pos[0].current_price == 10.0
