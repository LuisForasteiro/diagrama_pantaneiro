"""Maps a position to its price adapter.

`adapter_for_asset_type(asset_type, name)` returns either (adapter, external_id)
or None. None means "skip — this position is manually-priced" (private RF,
international RF, or anything else we don't have an adapter for).

Brazilian stocks + FIIs default to yfinance with the .SA suffix (works
without any API token). If BRAPI_TOKEN is set, Brapi is used instead —
higher-quality B3 data but requires a free account at brapi.dev.
"""

from __future__ import annotations

import os

from app.market_data.base import PriceProvider
from app.market_data.brapi import BrapiAdapter
from app.market_data.coingecko import CoinGeckoAdapter
from app.market_data.tesouro import TesouroAdapter
from app.market_data.yfinance_adapter import YFinanceAdapter

_ADAPTERS: dict[str, PriceProvider] = {
    "brapi": BrapiAdapter(),
    "yfinance": YFinanceAdapter(),
    "coingecko": CoinGeckoAdapter(),
    "tesouro": TesouroAdapter(),
}


def _br_stock_route(name: str) -> tuple[PriceProvider, str]:
    """Choose Brapi (if token set) or yfinance-with-.SA for B3 tickers."""
    if os.getenv("BRAPI_TOKEN"):
        return _ADAPTERS["brapi"], name
    # yfinance wants .SA for B3 tickers; tolerate names users might enter
    # with or without the suffix.
    yf_ticker = name.upper().strip()
    if not yf_ticker.endswith(".SA"):
        yf_ticker = f"{yf_ticker}.SA"
    return _ADAPTERS["yfinance"], yf_ticker


def adapter_for_asset_type(
    asset_type: str, name: str
) -> tuple[PriceProvider, str] | None:
    """Returns (adapter, external_id) for a given position, or None if manual."""
    if asset_type in ("acoes_nacionais", "fundos_imobiliarios"):
        return _br_stock_route(name)
    if asset_type in ("acoes_internacionais", "reits"):
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
