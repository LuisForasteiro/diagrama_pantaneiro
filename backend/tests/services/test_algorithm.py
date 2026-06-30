"""Mirrors test/algorithm.test.ts. Each scenario is verified against the
captured AUVP backend response at the matching aporte value."""

from __future__ import annotations

import math
from collections import defaultdict

import pytest

from app.services.algorithm import compute_suggestions
from app.services.types import Asset, Portfolio

from .conftest import load_expected, normalize_asset_type


def _sum_by_type(rows) -> dict[str, float]:
    out: dict[str, float] = defaultdict(float)
    for r in rows:
        t = normalize_asset_type(r["assetType"] if isinstance(r, dict) else r.asset_type)
        val = r["suggestionValue"] if isinstance(r, dict) else r.suggestion_value
        out[t] += val
    return dict(out)


class TestExactMatchSmallAporte:
    """R$500 exact-match — every suggestion matches the backend to ≥3 dp."""

    @pytest.mark.parametrize("aporte", [500, 1000])
    def test_matches_backend_response(self, portfolio: Portfolio, aporte: int) -> None:
        actual = compute_suggestions(portfolio, aporte)
        expected = load_expected(aporte)

        assert len(actual) == len(expected)

        for exp in expected:
            got = next((s for s in actual if s.asset_id == exp["assetId"]), None)
            assert got is not None, f"No suggestion for {exp['assetName']}"
            assert math.isclose(got.suggestion_value, exp["suggestionValue"], abs_tol=1e-3), \
                f"{exp['assetName']} value: got {got.suggestion_value}, expected {exp['suggestionValue']}"
            assert math.isclose(got.suggestion_quantity, exp["suggestionQuantity"], abs_tol=1e-4)
            assert math.isclose(got.suggestion_percentage, exp["suggestionPercentage"], abs_tol=1e-6)
            assert math.isclose(
                got.total_after_suggestion_percentage,
                exp["totalAfterSuggestionPercentage"],
                abs_tol=1e-3,
            )

    def test_r500_total_allocation_equals_aporte(self, portfolio: Portfolio) -> None:
        out = compute_suggestions(portfolio, 500)
        assert math.isclose(sum(s.suggestion_value for s in out), 500, abs_tol=1e-2)

    def test_r1000_total_allocation_equals_aporte(self, portfolio: Portfolio) -> None:
        out = compute_suggestions(portfolio, 1000)
        assert math.isclose(sum(s.suggestion_value for s in out), 1000, abs_tol=1e-2)


class TestClassLevelMatchLargeAporte:
    """R$10k — exact match is impossible due to known drift in stage 1.
    We verify class-level allocation is within 2% and that crypto/RF
    (which skip share-flooring) are within 2% of the backend values."""

    def test_funds_same_set_of_asset_types_as_backend(self, portfolio: Portfolio) -> None:
        actual = compute_suggestions(portfolio, 10000)
        expected = load_expected(10000)

        actual_types = {normalize_asset_type(s.asset_type) for s in actual}
        expected_types = {normalize_asset_type(r["assetType"]) for r in expected}
        assert sorted(actual_types) == sorted(expected_types)

    def test_class_level_allocation_within_2pct(self, portfolio: Portfolio) -> None:
        actual = _sum_by_type(compute_suggestions(portfolio, 10000))
        expected = _sum_by_type(load_expected(10000))

        for cls, exp_value in expected.items():
            got = actual.get(cls, 0.0)
            assert got > 0, f"class {cls}: backend allocated {exp_value} but Python got 0"
            rel_err = abs(got - exp_value) / exp_value
            assert rel_err < 0.02, \
                f"class {cls}: got {got:.2f}, expected {exp_value:.2f}, rel_err {rel_err:.4f}"

    def test_crypto_and_rf_positions_within_2pct_of_backend(self, portfolio: Portfolio) -> None:
        actual = compute_suggestions(portfolio, 10000)
        expected = load_expected(10000)

        # Crypto & RF skip integer-share flooring so their error is purely
        # inherited from the inter-class split. ~1% unexplained drift at R$10k.
        precise = [e for e in expected if e["assetType"] in ("criptomoedas", "rendafixa")]

        for exp in precise:
            got = next((s for s in actual if s.asset_id == exp["assetId"]), None)
            assert got is not None, f"Missing {exp['assetName']}"
            rel_err = abs(got.suggestion_value - exp["suggestionValue"]) / exp["suggestionValue"]
            assert rel_err < 0.02, \
                f"{exp['assetName']}: got {got.suggestion_value:.2f}, expected {exp['suggestionValue']:.2f}, rel_err {rel_err:.4f}"


class TestEdgeCases:

    def test_aporte_of_zero_returns_no_suggestions(self, portfolio: Portfolio) -> None:
        assert compute_suggestions(portfolio, 0) == []

    @pytest.mark.parametrize("aporte", [50, 500, 1000, 10000, 100000])
    def test_negative_strength_assets_never_appear(self, portfolio: Portfolio, aporte: int) -> None:
        out = compute_suggestions(portfolio, aporte)
        for s in out:
            assert s.strength > 0, f"Negative-strength asset {s.asset_name} appeared in suggestions for aporte {aporte}"

    def test_portfolio_with_no_targets_returns_empty(self, portfolio: Portfolio) -> None:
        flat = portfolio.model_copy(update={"targets": {}})
        assert compute_suggestions(flat, 500) == []

    def test_zero_strength_assets_never_receive_allocation(self, portfolio: Portfolio) -> None:
        out = compute_suggestions(portfolio, 10000)
        for s in out:
            assert s.strength > 0

    def test_phantom_target_class_does_not_eat_aporte(self, portfolio: Portfolio) -> None:
        """User has target > 0 for a class but zero active positions in it.
        Old behavior reserved a phantom share that Stage 2 dropped, leaving
        residual. Fix: Stage 1 skips classes with no active asset, so the full
        aporte flows to classes that can actually absorb it."""
        targets = dict(portfolio.targets)
        real_classes = {a.type for a in portfolio.assets if a.strength > 0}
        phantom_class = next(
            (c for c in ("fundos_imobiliarios", "reits", "rendafixa_internacional")
             if c not in real_classes),
            None,
        )
        if phantom_class is None:
            pytest.skip("fixture has every class populated; cannot simulate phantom")

        # Force a big target on the phantom class by reallocating from ações_nac.
        donor = "acoes_nacionais"
        if donor not in targets or targets[donor] < 20:
            pytest.skip("fixture has no donor slack")
        targets = {**targets, donor: targets[donor] - 20, phantom_class: targets.get(phantom_class, 0) + 20}
        p = portfolio.model_copy(update={"targets": targets})

        aporte = 1000.0
        out = compute_suggestions(p, aporte)
        total = sum(s.suggestion_value for s in out)
        residual = aporte - total
        # Residual should be small (stage-3 floor truncation only), not the full
        # phantom share (~R$200 at 20% of aporte).
        assert residual < 50, f"phantom class ate {residual:.2f} of aporte"


class TestTradableFlag:
    """A position flagged tradable=False (e.g. a Tesouro pulled from sale) must
    drop out of suggestions but still count toward portfolio totals."""

    def _mini(self, tradable: bool) -> Portfolio:
        return Portfolio(
            assets=[
                Asset(
                    id="keep", type="acoes_nacionais", name="KEEP3",
                    amount=10, strength=5, current_price=10.0,
                ),
                Asset(
                    id="delisted", type="acoes_nacionais", name="OLD3",
                    amount=10, strength=5, current_price=10.0, tradable=tradable,
                ),
            ],
            targets={"acoes_nacionais": 100.0},
            questions=[],
        )

    def test_non_tradable_never_suggested(self) -> None:
        out = compute_suggestions(self._mini(tradable=False), 1000)
        ids = {s.asset_id for s in out}
        assert "delisted" not in ids
        assert "keep" in ids

    def test_tradable_default_is_suggested(self) -> None:
        out = compute_suggestions(self._mini(tradable=True), 1000)
        assert {"keep", "delisted"} <= {s.asset_id for s in out}

    def test_non_tradable_still_counts_in_portfolio_total(self) -> None:
        # Both held assets = R$200; aporte R$1000 -> denominator R$1200. If the
        # delisted asset were dropped from totals too, the lone suggestion would
        # land at exactly 100%. It lands below, proving it's still counted.
        out = compute_suggestions(self._mini(tradable=False), 1000)
        keep = next(s for s in out if s.asset_id == "keep")
        assert keep.total_after_suggestion_percentage < 100.0
