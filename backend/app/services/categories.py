"""Pure helpers for hierarchical allocation categories (max 2 levels).

Kept ORM-free so the algorithm and validators can be unit-tested in isolation.
Weights are RELATIVE to siblings (each level sums to 100); a leaf's effective
target in points is the product down the path.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CatNode:
    id: str
    parent_id: str | None
    name: str
    weight_pct: float
    display_order: int


class CategoryValidationError(ValueError):
    """Raised when a category tree breaks an invariant (sum, depth, name)."""


def _children_map(nodes: list[CatNode]) -> dict[str | None, list[CatNode]]:
    out: dict[str | None, list[CatNode]] = {}
    for n in nodes:
        out.setdefault(n.parent_id, []).append(n)
    return out


def _assert_sum_100(weights: list[float], label: str) -> None:
    if abs(sum(weights) - 100.0) > 0.01:
        raise CategoryValidationError(f"{label}: pesos devem somar 100")


def validate_tree(nodes: list[CatNode]) -> None:
    by_id = {n.id: n for n in nodes}
    children = _children_map(nodes)

    for n in nodes:
        if not n.name.strip():
            raise CategoryValidationError("nome de categoria não pode ser vazio")
        if n.parent_id is not None:
            parent = by_id.get(n.parent_id)
            if parent is None:
                raise CategoryValidationError(
                    "parent_id aponta para categoria inexistente"
                )
            if parent.parent_id is not None:
                raise CategoryValidationError("a árvore não pode exceder 2 níveis")

    groups = children.get(None, [])
    if groups:
        _assert_sum_100([g.weight_pct for g in groups], "grupos")
    for g in groups:
        kids = children.get(g.id, [])
        if kids:
            _assert_sum_100([k.weight_pct for k in kids], f"filhos de {g.name}")


def leaf_effective_targets(nodes: list[CatNode]) -> dict[str, float]:
    """Leaf category id -> effective target in percentage points.

    A top-level group with no children is itself a leaf (its weight stands).
    A subgroup leaf's target is group% / 100 × subgroup%.
    """
    children = _children_map(nodes)
    out: dict[str, float] = {}
    for n in nodes:
        if n.parent_id is not None:
            continue  # subgroups are reached via their group below
        kids = children.get(n.id, [])
        if not kids:
            out[n.id] = n.weight_pct
        else:
            for k in kids:
                out[k.id] = (n.weight_pct / 100.0) * k.weight_pct
    return out
