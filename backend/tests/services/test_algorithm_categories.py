from __future__ import annotations

import math

from app.services.algorithm import compute_suggestions
from app.services.types import Asset, Portfolio


def _a(id, type_, name, amount, price, strength, bucket):
    return Asset(id=id, type=type_, name=name, amount=amount,
                 current_price=price, strength=strength, bucket=bucket)


def test_groups_by_bucket_not_type():
    # Duas ações nacionais em buckets diferentes; metas por bucket.
    assets = [
        _a("1", "acoes_nacionais", "AAA", 0, 10.0, 5, bucket="brasil_acoes"),
        _a("2", "acoes_nacionais", "BBB", 0, 10.0, 5, bucket="intl_acoes"),
    ]
    pf = Portfolio(assets=assets, targets={"brasil_acoes": 50.0, "intl_acoes": 50.0}, questions=[])
    out = compute_suggestions(pf, 1000)
    by_id = {s.asset_id: s.suggestion_value for s in out}
    # Mesmo tipo, buckets distintos com metas iguais e preços iguais → split ~igual.
    assert math.isclose(by_id["1"], by_id["2"], rel_tol=0.05)


def test_bucket_none_falls_back_to_type_flat_mode():
    # Sem bucket → comporta como hoje (chave = type).
    assets = [
        Asset(id="1", type="criptomoedas", name="BTC", amount=0, current_price=100.0, strength=10),
    ]
    pf = Portfolio(assets=assets, targets={"criptomoedas": 100.0}, questions=[])
    out = compute_suggestions(pf, 500)
    assert math.isclose(sum(s.suggestion_value for s in out), 500, abs_tol=1e-2)
