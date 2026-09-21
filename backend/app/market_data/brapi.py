"""Brapi.dev adapter for Brazilian-listed securities (B3).

Used for ações nacionais (VALE3, BBAS3, etc.) and fundos imobiliários
(HGLG11, etc.). Prices are already in BRL so no conversion needed.
"""

from __future__ import annotations

import asyncio
import math
import os

import httpx

from app.market_data.base import (
    AdapterNetworkError,
    AdapterNotFoundError,
    Candidate,
    PriceQuote,
)

_BASE_URL = "https://brapi.dev/api/quote"
_AVAILABLE_URL = "https://brapi.dev/api/available"

# Brapi allows 2 simultaneous requests per token and answers the rest with 429
# "Limite de requisições simultâneas atingido" (measured against the live API:
# 18/18 OK at 2 in flight, 429s from 3 up). The refresh prices every position at
# once, which used to fail most B3 tickers.
_MAX_IN_FLIGHT = 2
_RATE_LIMIT_RETRIES = 2
_DEFAULT_RETRY_AFTER_S = 1.0
# The refresh request waits on these sleeps; never trust an upstream value blindly.
_MAX_RETRY_AFTER_S = 5.0

_gate: asyncio.Semaphore | None = None
_gate_loop: asyncio.AbstractEventLoop | None = None


def _get_gate() -> asyncio.Semaphore:
    # Created lazily per event loop: asyncio primitives bind to the loop they
    # first wait on, and tests run each case on a fresh loop.
    global _gate, _gate_loop
    loop = asyncio.get_running_loop()
    if _gate is None or _gate_loop is not loop:
        _gate, _gate_loop = asyncio.Semaphore(_MAX_IN_FLIGHT), loop
    return _gate


def _retry_after(response: httpx.Response) -> float:
    try:
        wait = float(response.headers.get("Retry-After", _DEFAULT_RETRY_AFTER_S))
    except ValueError:  # e.g. an HTTP-date instead of seconds
        return _DEFAULT_RETRY_AFTER_S
    if math.isnan(wait):
        return _DEFAULT_RETRY_AFTER_S
    return min(max(wait, 0.0), _MAX_RETRY_AFTER_S)


async def _get_quote(ticker: str, params: dict[str, str]) -> dict:
    async with httpx.AsyncClient(timeout=8.0) as client:
        for attempt in range(_RATE_LIMIT_RETRIES + 1):
            async with _get_gate():
                r = await client.get(f"{_BASE_URL}/{ticker}", params=params)
            if r.status_code != 429 or attempt == _RATE_LIMIT_RETRIES:
                r.raise_for_status()
                return r.json()
            # Wait outside the gate so other tickers keep using the free slots.
            await asyncio.sleep(_retry_after(r))
    raise AssertionError("unreachable")


class BrapiAdapter:
    async def search(self, query: str) -> list[Candidate]:
        """Brapi's /api/available endpoint returns matching tickers WITHOUT
        requiring BRAPI_TOKEN (unlike /api/quote). Free to use for search."""
        q = query.strip()
        if not q:
            return []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(_AVAILABLE_URL, params={"search": q})
                r.raise_for_status()
                data = r.json()
        except Exception:
            return []

        stocks = data.get("stocks") or []
        # Limit to 20 to keep the dropdown manageable
        return [Candidate(name=s) for s in stocks[:20]]

    async def fetch_price(self, external_id: str) -> PriceQuote:
        ticker = external_id.upper().strip()
        token = os.getenv("BRAPI_TOKEN")
        params = {"token": token} if token else {}
        try:
            data = await _get_quote(ticker, params)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise AdapterNotFoundError(f"Brapi: {ticker} not found") from e
            raise AdapterNetworkError(
                f"Brapi HTTP {e.response.status_code} for {ticker}"
            ) from e
        except Exception as e:
            raise AdapterNetworkError(f"Brapi network error for {ticker}: {e}") from e

        results = data.get("results") or []
        if not results:
            raise AdapterNotFoundError(f"Brapi: empty results for {ticker}")
        price = results[0].get("regularMarketPrice")
        if price is None:
            raise AdapterNotFoundError(f"Brapi: no regularMarketPrice for {ticker}")
        return PriceQuote.now(external_id=ticker, price_brl=float(price))
