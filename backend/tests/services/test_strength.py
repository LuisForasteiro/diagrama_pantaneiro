"""Mirrors test/strength.test.ts 1:1."""

from __future__ import annotations

import pytest

from app.services.strength import compute_strength
from app.services.types import Portfolio


def _equities(portfolio: Portfolio):
    return [a for a in portfolio.assets if a.diagram_responses is not None]


def test_strength_matches_stored_for_every_equity(portfolio: Portfolio) -> None:
    equities = _equities(portfolio)
    assert len(equities) > 0
    for asset in equities:
        computed = compute_strength(asset, portfolio.questions)
        assert computed == asset.strength, f"Mismatch for {asset.name}: computed={computed}, stored={asset.strength}"


def test_asset_with_no_responses_scores_negative_n(portfolio: Portfolio) -> None:
    taee4 = next(a for a in portfolio.assets if a.name == "TAEE4")
    # 0 yes answers - 11 cerrado questions = -11
    assert taee4.strength == -11


def test_asset_with_all_responses_yes_scores_plus_n(portfolio: Portfolio) -> None:
    wege3 = next(a for a in portfolio.assets if a.name == "WEGE3")
    # 11 yes answers, 11 cerrado questions: 2*11 - 11 = 11
    assert wege3.strength == 11


def test_crypto_strength_passed_through_unchanged(portfolio: Portfolio) -> None:
    btc = next(a for a in portfolio.assets if a.name == "BTC")
    # Crypto has no diagram; compute_strength should return the stored value as-is.
    assert compute_strength(btc, portfolio.questions) == btc.strength
    assert btc.strength == 10  # confirms the fixture value
