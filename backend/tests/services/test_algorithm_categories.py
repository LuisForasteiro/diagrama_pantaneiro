from __future__ import annotations

from app.services.algorithm import compute_suggestions
from app.services.types import Asset, Portfolio


def _portfolio() -> Portfolio:
    # Duas folhas: "leaf_a" (ação BR, meta efetiva 70%) e "leaf_b" (cripto, 30%).
    # Carteira sem valor inicial -> o aporte deve seguir as metas das folhas.
    assets = [
        Asset(
            id="a1",
            type="acoes_nacionais",
            name="BBAS3",
            amount=0,
            strength=5,
            current_price=10.0,
            group_key="leaf_a",
        ),
        Asset(
            id="b1",
            type="criptomoedas",
            name="BTC",
            amount=0,
            strength=5,
            current_price=100.0,
            group_key="leaf_b",
        ),
    ]
    targets = {"leaf_a": 70.0, "leaf_b": 30.0}
    return Portfolio(assets=assets, targets=targets, questions=[])


def test_allocation_follows_leaf_targets() -> None:
    sugg = compute_suggestions(_portfolio(), 1000.0)
    by_id = {s.asset_id: s for s in sugg}
    # ~70% para a folha de ação, ~30% para a cripto (tolerância por quantização).
    assert by_id["a1"].suggestion_value > 600
    assert by_id["b1"].suggestion_value > 250


def test_group_key_none_falls_back_to_type() -> None:
    # Sem group_key, agrupa por type — comportamento de modo plano.
    assets = [
        Asset(
            id="a1",
            type="acoes_nacionais",
            name="BBAS3",
            amount=0,
            strength=5,
            current_price=10.0,
        ),
    ]
    p = Portfolio(assets=assets, targets={"acoes_nacionais": 100.0}, questions=[])
    sugg = compute_suggestions(p, 100.0)
    assert sugg and sugg[0].asset_id == "a1"
