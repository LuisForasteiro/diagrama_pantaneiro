from __future__ import annotations

import pytest
import respx
from httpx import Response

from app.market_data.base import AdapterNotFoundError
from app.market_data.coingecko import CoinGeckoAdapter, _ENDPOINT, resolve_coin_id


def test_resolve_btc_to_bitcoin() -> None:
    assert resolve_coin_id("BTC") == "bitcoin"
    assert resolve_coin_id("btc") == "bitcoin"
    assert resolve_coin_id("ETH") == "ethereum"


def test_resolve_unknown_falls_through_lowercase() -> None:
    assert resolve_coin_id("cardano") == "cardano"
    assert resolve_coin_id("FOO-BAR") == "foo-bar"


@respx.mock
async def test_fetches_brl_price_for_bitcoin() -> None:
    respx.get(_ENDPOINT).mock(
        return_value=Response(200, json={"bitcoin": {"brl": 374914.27}})
    )
    quote = await CoinGeckoAdapter().fetch_price("BTC")
    assert quote.price_brl == pytest.approx(374914.27)


@respx.mock
async def test_missing_brl_raises_not_found() -> None:
    respx.get(_ENDPOINT).mock(return_value=Response(200, json={}))
    with pytest.raises(AdapterNotFoundError):
        await CoinGeckoAdapter().fetch_price("BTC")
