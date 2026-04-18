from __future__ import annotations

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
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO RENDA + 2065")
    assert quote.price_brl == pytest.approx(2136.00)


@respx.mock
async def test_picks_most_recent_row_for_same_title() -> None:
    """Fixture has two rows for the 2065 title: 16/04 and 15/04. We should
    pick the newest (16/04 = R$2136, not 15/04 = R$2134)."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO RENDA + 2065")
    assert quote.price_brl == pytest.approx(2136.00)


@respx.mock
async def test_matches_ipca_2035() -> None:
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO IPCA+ 2035")
    assert quote.price_brl == pytest.approx(3200.00)


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
