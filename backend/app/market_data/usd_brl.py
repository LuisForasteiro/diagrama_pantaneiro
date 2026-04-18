"""USD->BRL rate from AwesomeAPI (https://economia.awesomeapi.com.br)."""

from __future__ import annotations

import time

import httpx

from app.market_data.base import AdapterNetworkError

_ENDPOINT = "https://economia.awesomeapi.com.br/json/last/USD-BRL"
_CACHE_TTL_SECONDS = 600  # 10 min

_cache: dict[str, tuple[float, float]] = {}  # key -> (rate, fetched_at_epoch)


async def get_usd_brl_rate() -> float:
    """Current USD->BRL rate. Cached for 10 min to avoid hammering AwesomeAPI.
    On network failure, returns the last cached rate if available, else raises."""
    now = time.time()
    cached = _cache.get("rate")
    if cached is not None and now - cached[1] < _CACHE_TTL_SECONDS:
        return cached[0]

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            r = await client.get(_ENDPOINT)
            r.raise_for_status()
            data = r.json()
        rate = float(data["USDBRL"]["bid"])
    except Exception as e:
        if cached is not None:
            return cached[0]  # fall back to stale
        raise AdapterNetworkError(f"USD-BRL fetch failed: {e}") from e

    _cache["rate"] = (rate, now)
    return rate


def _reset_cache_for_tests() -> None:
    _cache.clear()
