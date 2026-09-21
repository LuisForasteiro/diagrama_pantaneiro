"""Regression: "16 posição(ões) atualizada(s) · 18 falharam: BTLG11, GGRC11, ..."

With BRAPI_TOKEN set, every B3 position is priced by Brapi, and the refresh
fires all positions at once. Brapi only allows 2 simultaneous requests per token
and answers the rest with 429 "Limite de requisições simultâneas atingido"
(measured against the live API: 18/18 OK at 2 in flight, 429s from 3 up).
"""

from __future__ import annotations

import asyncio
import uuid

import pytest
import respx
from httpx import Response

from app.market_data import brapi
from app.market_data.brapi import _BASE_URL
from app.market_data.registry import adapter_for_asset_type
from app.models import Position
from app.services.refresh_prices import refresh_portfolio_prices

_USER_TICKERS = [
    "BTLG11", "GGRC11", "KNRI11", "HSML11", "KNCA11", "ISAE4", "OBTC3", "TAEE4", "SBSP3",
    "VISC11", "HGLG11", "IVVB11", "IFRA11", "PSSA3", "RZAG11", "KNCR11", "KDIF11", "VALE3",
]
_YAHOO_CHART = "https://query1.finance.yahoo.com/v8/finance/chart"


def _brapi_allowing(max_in_flight: int):
    """Brapi stand-in that rate-limits like the real one."""
    in_flight = 0

    async def respond(request):
        nonlocal in_flight
        ticker = request.url.path.rsplit("/", 1)[-1]
        if in_flight >= max_in_flight:
            return Response(
                429,
                headers={"Retry-After": "0"},
                json={"error": True, "code": "RATE_LIMIT",
                      "message": "Limite de requisições simultâneas atingido."},
            )
        in_flight += 1
        try:
            await asyncio.sleep(0.01)
            return Response(200, json={"results": [{"symbol": ticker, "regularMarketPrice": 10.0}]})
        finally:
            in_flight -= 1

    return respond


@pytest.fixture(autouse=True)
def brapi_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BRAPI_TOKEN", "test-token")


@respx.mock
async def test_refresh_prices_every_b3_position_despite_brapi_concurrency_limit(
    session_maker,
) -> None:
    respx.get(url__startswith=_BASE_URL).mock(side_effect=_brapi_allowing(2))
    portfolio_id, user_id = uuid.uuid4(), uuid.uuid4()
    async with session_maker() as session:
        for ticker in _USER_TICKERS:
            asset_type = "fundos_imobiliarios" if ticker.endswith("11") else "acoes_nacionais"
            session.add(Position(
                user_id=user_id, portfolio_id=portfolio_id, name=ticker,
                asset_type=asset_type, amount=1, current_price=1.0, strength=0,
            ))
        await session.commit()

        result = await refresh_portfolio_prices(session, portfolio_id)

    assert [f.name for f in result.failed] == []
    assert result.refreshed == len(_USER_TICKERS)


@respx.mock
async def test_b3_price_falls_back_to_yahoo_when_brapi_keeps_failing() -> None:
    respx.get(url__startswith=_BASE_URL).mock(
        return_value=Response(503, json={"error": True, "message": "indisponível"})
    )
    respx.get(f"{_YAHOO_CHART}/VALE3.SA").mock(
        return_value=Response(200, json={"chart": {"result": [
            {"meta": {"regularMarketPrice": 72.85, "currency": "BRL"}}
        ]}})
    )
    adapter, external_id = adapter_for_asset_type("acoes_nacionais", "VALE3")

    quote = await adapter.fetch_price(external_id)

    assert quote.price_brl == pytest.approx(72.85)


@respx.mock
async def test_brapi_retries_after_a_rate_limit_answer() -> None:
    route = respx.get(f"{_BASE_URL}/VALE3").mock(side_effect=[
        Response(429, headers={"Retry-After": "0"}, json={"code": "RATE_LIMIT"}),
        Response(200, json={"results": [{"symbol": "VALE3", "regularMarketPrice": 72.85}]}),
    ])

    quote = await brapi.BrapiAdapter().fetch_price("VALE3")

    assert quote.price_brl == pytest.approx(72.85)
    assert route.call_count == 2


@pytest.mark.parametrize("header", ["3600", "inf", "nan", "-5", "soon"])
def test_retry_after_is_bounded(header: str) -> None:
    """The refresh request waits on these sleeps: an upstream sending a huge (or
    bogus) Retry-After must not hang the "atualizar" button for an hour."""
    wait = brapi._retry_after(Response(429, headers={"Retry-After": header}))

    assert 0.0 <= wait <= brapi._MAX_RETRY_AFTER_S
