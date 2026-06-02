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
async def test_matches_ipca_2035_picks_chronologically_newest() -> None:
    """IPCA+ 2035 has rows 16/04/2026 (3200) and 01/06/2026 (3500). The newest
    by DATE is 01/06 — even though '01/06' sorts BEFORE '16/04' as a string.
    Must NOT pick the semestrais variant (3900) either."""
    respx.get(_CSV_URL).mock(
        return_value=Response(200, text=_fixture_csv_text())
    )
    quote = await TesouroAdapter().fetch_price("TESOURO IPCA+ 2035")
    assert quote.price_brl == pytest.approx(3500.00)


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
    assert quote.price_brl == pytest.approx(3900.00)


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
