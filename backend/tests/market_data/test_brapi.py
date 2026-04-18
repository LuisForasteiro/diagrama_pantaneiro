from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.market_data.base import AdapterNetworkError, AdapterNotFoundError
from app.market_data.brapi import BrapiAdapter, _BASE_URL


@respx.mock
async def test_fetches_ticker_price() -> None:
    respx.get(f"{_BASE_URL}/VALE3").mock(
        return_value=Response(
            200,
            json={"results": [{"symbol": "VALE3", "regularMarketPrice": 88.79}]},
        )
    )
    quote = await BrapiAdapter().fetch_price("vale3")
    assert quote.external_id == "VALE3"
    assert quote.price_brl == pytest.approx(88.79)


@respx.mock
async def test_404_raises_not_found() -> None:
    respx.get(f"{_BASE_URL}/XXXX9").mock(return_value=Response(404, json={}))
    with pytest.raises(AdapterNotFoundError):
        await BrapiAdapter().fetch_price("XXXX9")


@respx.mock
async def test_empty_results_raises_not_found() -> None:
    respx.get(f"{_BASE_URL}/FAKE1").mock(
        return_value=Response(200, json={"results": []})
    )
    with pytest.raises(AdapterNotFoundError):
        await BrapiAdapter().fetch_price("FAKE1")


@respx.mock
async def test_network_error_raises_adapter_network() -> None:
    respx.get(f"{_BASE_URL}/VALE3").mock(side_effect=Exception("boom"))
    with pytest.raises(AdapterNetworkError):
        await BrapiAdapter().fetch_price("VALE3")
