from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.market_data import usd_brl
from app.market_data.base import AdapterNotFoundError
from app.market_data.yfinance_adapter import YFinanceAdapter, _CHART_URL


@pytest.fixture(autouse=True)
def reset():
    usd_brl._reset_cache_for_tests()


def _chart(price, currency):
    return {
        "chart": {
            "result": [{"meta": {"regularMarketPrice": price, "currency": currency}}],
            "error": None,
        }
    }


@respx.mock
async def test_fetches_usd_and_converts_to_brl() -> None:
    respx.get(usd_brl._ENDPOINT).mock(
        return_value=Response(200, json={"USDBRL": {"bid": "5.0"}})
    )
    respx.get(f"{_CHART_URL}/QQQ").mock(
        return_value=Response(200, json=_chart(400.0, "USD"))
    )
    quote = await YFinanceAdapter().fetch_price("QQQ")
    assert quote.external_id == "QQQ"
    assert quote.price_brl == pytest.approx(2000.0)  # 400 x 5


@respx.mock
async def test_brl_ticker_passes_through_without_conversion() -> None:
    respx.get(f"{_CHART_URL}/VALE3.SA").mock(
        return_value=Response(200, json=_chart(88.79, "BRL"))
    )
    quote = await YFinanceAdapter().fetch_price("VALE3.SA")
    assert quote.price_brl == pytest.approx(88.79)


@respx.mock
async def test_404_raises_not_found() -> None:
    respx.get(f"{_CHART_URL}/NOPE").mock(
        return_value=Response(404, json={"chart": {"result": None}})
    )
    with pytest.raises(AdapterNotFoundError):
        await YFinanceAdapter().fetch_price("NOPE")


@respx.mock
async def test_missing_price_raises_not_found() -> None:
    respx.get(f"{_CHART_URL}/EMPTY").mock(
        return_value=Response(200, json=_chart(None, "USD"))
    )
    with pytest.raises(AdapterNotFoundError):
        await YFinanceAdapter().fetch_price("EMPTY")
