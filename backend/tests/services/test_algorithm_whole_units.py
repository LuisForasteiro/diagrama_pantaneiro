"""Regression tests: B3-listed assets must never receive fractional
suggestion quantities, regardless of their allocation class.

Reported bug: a B3 ETF (e.g. IVVB11) put under the "ETF Internacional"
allocation class via `effective_class` (because the underlying exposure is
international) was quantized as if it were a US-brokered fractional share,
since the old algorithm decided fractional-vs-whole purely from
`Asset.type` (which carries the *effective* class, not the real market
venue). B3 never allows fractional buys, so the suggestion must stay a
whole number no matter which allocation class the asset is grouped under.
"""

from __future__ import annotations

from app.services.algorithm import compute_suggestions
from app.services.types import Asset, Portfolio


def _portfolio(asset: Asset, target_pct: float = 100.0) -> Portfolio:
    return Portfolio(assets=[asset], targets={asset.type: target_pct}, questions=[])


def test_b3_etf_overridden_to_international_class_buys_whole_units() -> None:
    """IVVB11 trades on B3 (real asset_type etfs_nacionais) but the user
    filed it under etfs_internacionais since the exposure is the S&P 500.
    The suggested quantity must still be a whole number of shares."""
    asset = Asset(
        id="ivvb11",
        type="etfs_internacionais",
        market_type="etfs_nacionais",
        name="IVVB11",
        amount=0,
        strength=5,
        current_price=350.0,
    )
    out = compute_suggestions(_portfolio(asset), 1000.0)

    assert len(out) == 1
    assert out[0].suggestion_quantity == int(out[0].suggestion_quantity)


def test_b3_shaped_ticker_stays_whole_even_without_explicit_override() -> None:
    """WRLD11 is a B3-listed ETF. Even if its stored asset_type is the
    international class outright (no effective_class override at all), the
    ticker shape (4 letters + digits) is a defensive signal that it trades
    on B3 in whole units."""
    asset = Asset(
        id="wrld11",
        type="etfs_internacionais",
        name="WRLD11",
        amount=0,
        strength=5,
        current_price=120.0,
    )
    out = compute_suggestions(_portfolio(asset), 1000.0)

    assert len(out) == 1
    assert out[0].suggestion_quantity == int(out[0].suggestion_quantity)


def test_genuine_us_etf_stays_fractional() -> None:
    """VOO is genuinely US-listed (Avenue/Nomad) and should keep its
    fractional-share suggestion — this must NOT regress."""
    asset = Asset(
        id="voo",
        type="etfs_internacionais",
        name="VOO",
        amount=0,
        strength=5,
        current_price=333.0,
    )
    out = compute_suggestions(_portfolio(asset), 1000.0)

    assert len(out) == 1
    assert out[0].suggestion_quantity != int(out[0].suggestion_quantity)


def _assert_whole_units(suggestions) -> None:
    for s in suggestions:
        assert s.suggestion_quantity == int(s.suggestion_quantity), s
        assert abs(s.suggestion_value - s.suggestion_quantity * s.current_price) < 0.01, s


def test_b3_stock_overridden_to_crypto_class_buys_whole_units() -> None:
    """OBTC3 is a B3 stock the user files under criptomoedas (bitcoin
    exposure). The crypto branch quantizes to 4 decimals — wrong for B3."""
    asset = Asset(
        id="obtc3",
        type="criptomoedas",
        market_type="acoes_nacionais",
        name="OBTC3",
        amount=0,
        strength=5,
        current_price=17.0,
    )
    out = compute_suggestions(_portfolio(asset), 1000.0)

    assert len(out) == 1
    _assert_whole_units(out)


def test_b3_etf_overridden_to_crypto_class_never_absorbs_the_residual() -> None:
    """Leftover BRL from whole-share rounding goes to an asset that accepts
    exact amounts (crypto / unpriced RF). A B3 ETF filed under criptomoedas
    (QBTC11) is not such an asset: absorbing it made its quantity fractional."""
    petr4 = Asset(
        id="petr4", type="acoes_nacionais", name="PETR4",
        amount=0, strength=5, current_price=30.0,
    )
    qbtc11 = Asset(
        id="qbtc11", type="criptomoedas", market_type="etfs_nacionais", name="QBTC11",
        amount=0, strength=5, current_price=17.0,
    )
    portfolio = Portfolio(
        assets=[petr4, qbtc11],
        targets={"acoes_nacionais": 50.0, "criptomoedas": 50.0},
        questions=[],
    )

    out = compute_suggestions(portfolio, 1000.0)

    assert {s.asset_id for s in out} == {"petr4", "qbtc11"}
    _assert_whole_units(out)


def test_b3_etf_overridden_to_fixed_income_class_buys_whole_units() -> None:
    """IMAB11 (B3 bond ETF) filed under rendafixa: priced RF quantizes to 2
    decimals (Tesouro units), which is wrong for a B3 ETF."""
    asset = Asset(
        id="imab11",
        type="rendafixa",
        market_type="etfs_nacionais",
        name="IMAB11",
        amount=0,
        strength=5,
        current_price=95.0,
    )
    out = compute_suggestions(_portfolio(asset), 1000.0)

    assert len(out) == 1
    _assert_whole_units(out)
