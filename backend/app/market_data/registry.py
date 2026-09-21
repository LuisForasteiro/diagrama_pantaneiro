"""Maps a position to its price adapter.

`adapter_for_asset_type(asset_type, name)` returns either (adapter, external_id)
or None. None means "skip — this position is manually-priced" (private RF,
international RF, or anything else we don't have an adapter for).

Brazilian stocks + FIIs default to yfinance with the .SA suffix (works
without any API token). If BRAPI_TOKEN is set, Brapi is used instead —
higher-quality B3 data but requires a free account at brapi.dev — with Yahoo as
the fallback whenever Brapi fails for a ticker.
"""

from __future__ import annotations

import os

from app.market_data.base import AdapterError, PriceProvider, PriceQuote
from app.market_data.brapi import BrapiAdapter
from app.market_data.coingecko import CoinGeckoAdapter
from app.market_data.tesouro import TesouroAdapter
from app.market_data.yfinance_adapter import YFinanceAdapter

def _yahoo_b3_ticker(name: str) -> str:
    # yfinance wants .SA for B3 tickers; tolerate names users might enter
    # with or without the suffix.
    ticker = name.upper().strip()
    return ticker if ticker.endswith(".SA") else f"{ticker}.SA"


class B3PriceAdapter:
    """Brapi first, Yahoo (.SA) when Brapi fails for a ticker — rate limit
    that outlived the retries, outage, or a ticker outside the token's plan."""

    def __init__(self, brapi: PriceProvider, yahoo: PriceProvider) -> None:
        self._brapi = brapi
        self._yahoo = yahoo

    async def fetch_price(self, external_id: str) -> PriceQuote:
        try:
            return await self._brapi.fetch_price(external_id)
        except AdapterError as brapi_error:
            try:
                return await self._yahoo.fetch_price(_yahoo_b3_ticker(external_id))
            except AdapterError as yahoo_error:
                raise AdapterError(f"{brapi_error}; fallback: {yahoo_error}") from yahoo_error


_brapi_adapter = BrapiAdapter()
_yahoo_adapter = YFinanceAdapter()

_ADAPTERS: dict[str, PriceProvider] = {
    "brapi": _brapi_adapter,
    "b3": B3PriceAdapter(_brapi_adapter, _yahoo_adapter),
    "yfinance": _yahoo_adapter,
    "coingecko": CoinGeckoAdapter(),
    "tesouro": TesouroAdapter(),
}


def _br_stock_route(name: str) -> tuple[PriceProvider, str]:
    """Choose Brapi-with-Yahoo-fallback (if token set) or yfinance-with-.SA."""
    if os.getenv("BRAPI_TOKEN"):
        return _ADAPTERS["b3"], name
    return _ADAPTERS["yfinance"], _yahoo_b3_ticker(name)


def adapter_for_asset_type(
    asset_type: str, name: str
) -> tuple[PriceProvider, str] | None:
    """Returns (adapter, external_id) for a given position, or None if manual."""
    if asset_type in ("acoes_nacionais", "fundos_imobiliarios", "etfs_nacionais"):
        return _br_stock_route(name)
    if asset_type in ("acoes_internacionais", "reits", "etfs_internacionais"):
        return _ADAPTERS["yfinance"], name
    if asset_type == "criptomoedas":
        return _ADAPTERS["coingecko"], name
    if asset_type == "rendafixa":
        # Only public Tesouro titles are auto-refreshable.
        if "tesouro" in name.lower():
            return _ADAPTERS["tesouro"], name
        return None
    # rendafixa_internacional and anything else: manual
    return None
