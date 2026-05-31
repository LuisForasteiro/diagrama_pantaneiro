from __future__ import annotations

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient


async def _register_login_seed(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    token = r.json()["access_token"]
    await client.get("/api/positions", headers={"Authorization": f"Bearer {token}"})
    return token


async def test_refresh_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/api/prices/refresh")
    assert r.status_code == 401


async def test_refresh_counts_by_outcome(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "prices@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    from app.services import refresh_prices as svc

    async def fake_refresh(session, portfolio_id):
        return svc.RefreshResult(refreshed=15, skipped_manual=4, failed=[])

    with patch(
        "app.api.prices.refresh_portfolio_prices",
        new=AsyncMock(side_effect=fake_refresh),
    ):
        r = await client.post("/api/prices/refresh", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["refreshed"] == 15
    assert body["skippedManual"] == 4
    assert body["failed"] == []


async def test_refresh_reports_adapter_failure(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "prices2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    from app.services import refresh_prices as svc

    async def fake_refresh(session, portfolio_id):
        return svc.RefreshResult(
            refreshed=14,
            skipped_manual=4,
            failed=[svc.Failure(name="TAEE4", reason="Brapi: TAEE4 not found")],
        )

    with patch(
        "app.api.prices.refresh_portfolio_prices",
        new=AsyncMock(side_effect=fake_refresh),
    ):
        r = await client.post("/api/prices/refresh", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["failed"] == [
        {"name": "TAEE4", "reason": "Brapi: TAEE4 not found"}
    ]


async def test_refresh_auto_migrates_rf_amount_to_units_on_first_price(
    session_maker,
) -> None:
    """Legacy Tesouro position: amount stored as BRL, current_price None.
    After a successful Tesouro adapter refresh, amount should be units
    (BRL / price) and current_price should hold the new PU."""
    import uuid

    from unittest.mock import AsyncMock, patch

    from app.market_data.base import PriceQuote
    from app.models.portfolio import Portfolio as PortfolioModel
    from app.models.position import Position
    from app.services.refresh_prices import refresh_portfolio_prices

    async with session_maker() as session:
        user_id = uuid.uuid4()
        portfolio = PortfolioModel(
            id=uuid.uuid4(), user_id=user_id, name="Principal", is_default=True
        )
        session.add(portfolio)
        await session.flush()
        p = Position(
            user_id=user_id,
            portfolio_id=portfolio.id,
            name="TESOURO RENDA + 2064",
            asset_type="rendafixa",
            amount=1074.0,  # legacy: BRL value
            current_price=None,
            strength=9,
            source="auvp_import",
        )
        session.add(p)
        await session.commit()
        await session.refresh(p)
        p_id = p.id
        portfolio_id = portfolio.id

    with patch(
        "app.market_data.tesouro.TesouroAdapter.fetch_price",
        new=AsyncMock(
            return_value=PriceQuote.now(
                external_id="TESOURO RENDA + 2064", price_brl=500.0
            )
        ),
    ):
        async with session_maker() as session:
            summary = await refresh_portfolio_prices(session, portfolio_id)

    assert summary.refreshed == 1
    async with session_maker() as session:
        from sqlalchemy import select

        refreshed = (
            await session.execute(select(Position).where(Position.id == p_id))
        ).scalar_one()
        # 1074 BRL / 500 PU = 2.148 units
        assert abs(refreshed.amount - 2.148) < 1e-4
        assert refreshed.current_price == 500.0
        # Value preserved: 2.148 units * 500 PU = 1074 BRL
        assert abs(refreshed.amount * refreshed.current_price - 1074.0) < 1e-3


async def test_refresh_does_not_remigrate_on_subsequent_calls(
    session_maker,
) -> None:
    """Once current_price is set, later refreshes update the price but
    must not re-divide amount by the new price."""
    import uuid

    from unittest.mock import AsyncMock, patch

    from app.market_data.base import PriceQuote
    from app.models.portfolio import Portfolio as PortfolioModel
    from app.models.position import Position
    from app.services.refresh_prices import refresh_portfolio_prices

    async with session_maker() as session:
        user_id = uuid.uuid4()
        portfolio = PortfolioModel(
            id=uuid.uuid4(), user_id=user_id, name="Principal", is_default=True
        )
        session.add(portfolio)
        await session.flush()
        p = Position(
            user_id=user_id,
            portfolio_id=portfolio.id,
            name="TESOURO RENDA + 2064",
            asset_type="rendafixa",
            amount=2.148,  # already-migrated units
            current_price=500.0,
            strength=9,
            source="user",
        )
        session.add(p)
        await session.commit()
        p_id = p.id
        portfolio_id = portfolio.id

    with patch(
        "app.market_data.tesouro.TesouroAdapter.fetch_price",
        new=AsyncMock(
            return_value=PriceQuote.now(
                external_id="TESOURO RENDA + 2064", price_brl=520.0
            )
        ),
    ):
        async with session_maker() as session:
            await refresh_portfolio_prices(session, portfolio_id)

    async with session_maker() as session:
        from sqlalchemy import select

        refreshed = (
            await session.execute(select(Position).where(Position.id == p_id))
        ).scalar_one()
        # amount unchanged — no re-division
        assert abs(refreshed.amount - 2.148) < 1e-6
        # price picked up the new value
        assert refreshed.current_price == 520.0
