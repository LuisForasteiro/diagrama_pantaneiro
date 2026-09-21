from __future__ import annotations

import asyncio
import time
from pathlib import Path

import pytest
import respx
from httpx import Response

from app.market_data import tesouro
from app.market_data.base import AdapterNotFoundError
from app.market_data.tesouro import TesouroAdapter, _CSV_URL


@pytest.fixture(autouse=True)
def clear_cache():
    tesouro._reset_cache_for_tests()


def _fixture_csv_text() -> str:
    return (Path(__file__).parent / "fixtures" / "tesouro_sample.csv").read_text()


@respx.mock
async def test_matches_renda_plus_2065() -> None:
    """Valuation uses PU Venda (redemption), matching the official platform.
    16/04 PU Venda = 2130 (not Compra 2136)."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO RENDA + 2065")
    assert quote.price_brl == pytest.approx(2130.00)


@respx.mock
async def test_picks_most_recent_row_for_same_title() -> None:
    """Fixture has two rows for the 2065 title: 16/04 and 15/04. We should
    pick the newest (16/04 PU Venda = R$2130, not 15/04 = R$2128)."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO RENDA + 2065")
    assert quote.price_brl == pytest.approx(2130.00)


@respx.mock
async def test_matches_ipca_2035_picks_chronologically_newest() -> None:
    """IPCA+ 2035 has rows 16/04/2026 (3200) and 01/06/2026 (3500). The newest
    by DATE is 01/06 — even though '01/06' sorts BEFORE '16/04' as a string.
    Must NOT pick the semestrais variant (3900) either."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO IPCA+ 2035")
    assert quote.price_brl == pytest.approx(3490.00)  # 01/06 PU Venda


@respx.mock
async def test_semestrais_variant_is_distinct() -> None:
    """'Tesouro IPCA+' and 'Tesouro IPCA+ com Juros Semestrais' must NOT
    collapse: search lists both, and a semestrais position prices to its
    own row (3900), not the plain one."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    candidates = await TesouroAdapter().search("ipca")
    names = [c.name for c in candidates]
    plain = [n for n in names if "SEMESTRAIS" not in n.upper()]
    semes = [n for n in names if "SEMESTRAIS" in n.upper()]
    assert plain, f"esperava um IPCA+ simples em {names}"
    assert semes, f"esperava um IPCA+ semestrais em {names}"

    quote = await TesouroAdapter().fetch_price(semes[0])
    assert quote.price_brl == pytest.approx(3890.00)  # PU Venda


@respx.mock
async def test_search_excludes_matured_titles() -> None:
    """The CSV carries the full history, including delisted/matured titles.
    Search must only list titles you can still buy (maturity in the future),
    so the matured IPCA+ 2020 row must NOT appear."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    names = [c.name for c in await TesouroAdapter().search("ipca")]
    assert not any("2020" in n for n in names), names
    assert any("2035" in n for n in names), names  # future ones still listed


@respx.mock
async def test_no_match_for_private_rf() -> None:
    """Private RF (LCI, CDB, etc.) should never match against Tesouro CSV."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    with pytest.raises(AdapterNotFoundError):
        await TesouroAdapter().fetch_price("LCI INTER 90,00")


@respx.mock
async def test_no_match_when_year_missing_from_position_name() -> None:
    """We require a maturity year in the position name to disambiguate."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    # "TESOURO PREFIXADO" without a year is ambiguous — but our fixture only has
    # one prefixado row (2031), so with year omitted the adapter can't match
    # which one the user meant. Expect not found.
    with pytest.raises(AdapterNotFoundError):
        await TesouroAdapter().fetch_price("TESOURO PREFIXADO SEM ANO")


def _full_history_csv(rows: int) -> str:
    """The real CSV carries ~176k rows of history (2002 onwards). Pad the
    fixture with old rows of already-matured titles so lookups have to cope
    with a realistically sized file."""
    lines = [_fixture_csv_text().rstrip("\n")]
    for i in range(rows):
        day = 1 + i % 28
        month = 1 + (i // 28) % 12
        year = 2003 + i % 15
        lines.append(
            f"Tesouro Selic;01/03/{year + 3};{day:02d}/{month:02d}/{year};"
            "0,01;0,02;9000,00;8990,00;8995,00"
        )
    return "\n".join(lines) + "\n"


async def _max_event_loop_stall(awaitable) -> float:
    """Await `awaitable` while a 10ms heartbeat runs; return the longest gap
    between beats. A lookup that hogs the loop freezes every other request
    (the API stopped answering /api/health for 17s during boot)."""
    gaps: list[float] = []
    done = False

    async def heartbeat() -> None:
        last = time.perf_counter()
        while not done:
            await asyncio.sleep(0.01)
            now = time.perf_counter()
            gaps.append(now - last)
            last = now

    beat = asyncio.create_task(heartbeat())
    await asyncio.sleep(0)  # let the heartbeat take its first timestamp
    try:
        await awaitable
    finally:
        done = True
        await beat
    return max(gaps, default=0.0)


def _serve_csv(monkeypatch: pytest.MonkeyPatch, text: str) -> None:
    """Stub the download itself: respx builds a multi-MB mocked body
    synchronously (~0.6s), which would drown out the adapter's own behavior."""

    async def download() -> str:
        await asyncio.sleep(0)
        return text

    monkeypatch.setattr(tesouro, "_download_csv", download)


async def test_fetch_price_does_not_block_event_loop_on_full_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve_csv(monkeypatch, _full_history_csv(60_000))

    async def lookups() -> None:
        # A miss walks every row of the history — the worst case.
        with pytest.raises(AdapterNotFoundError):
            await TesouroAdapter().fetch_price("TESOURO RENDA + 2099")
        quote = await TesouroAdapter().fetch_price("TESOURO IPCA+ 2035")
        assert quote.price_brl == pytest.approx(3490.00)

    assert await _max_event_loop_stall(lookups()) < 0.5


async def test_search_does_not_block_event_loop_on_full_history(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _serve_csv(monkeypatch, _full_history_csv(60_000))
    found: list[str] = []

    async def search() -> None:
        found.extend(c.name for c in await TesouroAdapter().search("tesouro"))

    assert await _max_event_loop_stall(search()) < 0.5
    assert any("2035" in n for n in found), found


@respx.mock
async def test_concurrent_lookups_download_csv_only_once() -> None:
    """The refresh job prices every position in parallel. Six Tesouro positions
    on a cold cache used to fire six 14 MB downloads at once."""
    async def slow_download(_request):
        await asyncio.sleep(0.05)  # a real 14 MB download takes seconds
        return Response(200, text=_fixture_csv_text())

    route = respx.get(_CSV_URL).mock(side_effect=slow_download)
    names = ["TESOURO RENDA + 2065", "TESOURO IPCA+ 2035", "TESOURO PREFIXADO 2031"] * 2

    quotes = await asyncio.gather(*(TesouroAdapter().fetch_price(n) for n in names))

    assert route.call_count == 1
    assert [q.price_brl for q in quotes[:3]] == pytest.approx([2130.0, 3490.0, 648.0])


@respx.mock
async def test_fetch_price_falls_back_to_newest_row_that_has_a_price() -> None:
    """If the newest row of a title has no PU Venda, use the newest one that does."""
    csv = _fixture_csv_text().rstrip("\n") + (
        "\nTesouro Prefixado;01/01/2031;20/04/2026;11,30;11,35;650,00;;649\n"
    )
    respx.get(_CSV_URL).mock(return_value=Response(200, text=csv))

    quote = await TesouroAdapter().fetch_price("TESOURO PREFIXADO 2031")

    assert quote.price_brl == pytest.approx(648.00)
