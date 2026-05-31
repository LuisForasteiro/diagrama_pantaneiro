"""Yahoo Finance adapter via the public chart JSON endpoint.

Replaces the heavyweight, scraping-based `yfinance` library with a direct
httpx call to query1.finance.yahoo.com — lighter and more stable. A browser
User-Agent is required or Yahoo returns HTTP 429.

For BRL tickers (B3's .SA suffix) the price passes through; USD tickers are
converted via the current USD-BRL rate. Other currencies raise AdapterError.
"""

from __future__ import annotations

import httpx

from app.market_data.base import (
    AdapterError,
    AdapterNetworkError,
    AdapterNotFoundError,
    PriceQuote,
)
from app.market_data.usd_brl import get_usd_brl_rate

_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart"
_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
)


class YFinanceAdapter:
    async def fetch_price(self, external_id: str) -> PriceQuote:
        ticker = external_id.upper().strip()
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                r = await client.get(
                    f"{_CHART_URL}/{ticker}",
                    params={"interval": "1d", "range": "1d"},
                    headers={"User-Agent": _USER_AGENT},
                )
                r.raise_for_status()
                data = r.json()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise AdapterNotFoundError(f"yfinance: {ticker} not found") from e
            raise AdapterNetworkError(
                f"yfinance HTTP {e.response.status_code} for {ticker}"
            ) from e
        except Exception as e:
            raise AdapterNetworkError(
                f"yfinance network error for {ticker}: {e}"
            ) from e

        results = (data.get("chart") or {}).get("result") or []
        if not results:
            raise AdapterNotFoundError(f"yfinance: empty result for {ticker}")
        meta = results[0].get("meta") or {}
        price = meta.get("regularMarketPrice")
        currency = (meta.get("currency") or "USD").upper()
        if price is None or price == 0:
            raise AdapterNotFoundError(f"yfinance: no price for {ticker}")
        price = float(price)

        if currency == "BRL":
            price_brl = price
        elif currency == "USD":
            rate = await get_usd_brl_rate()
            price_brl = price * rate
        else:
            raise AdapterError(
                f"yfinance: unsupported currency {currency} for {ticker}"
            )

        return PriceQuote.now(external_id=ticker, price_brl=price_brl)
