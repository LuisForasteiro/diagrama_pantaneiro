"""Shared fixture loaders for algorithm/strength tests.

Translates the captured AUVP user document (backend/tests/fixtures/auth_me.json)
into the Python domain types, applying the same field renames that the TS
fixtures.ts loader does (RF `amount` comes from the `value` field; non-RF
`currentPrice` is computed as `value / amount`).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from app.services.types import Asset, Portfolio, Question, Suggestion

FIXTURE_DIR = Path(__file__).resolve().parent.parent / "fixtures"
RF_TYPES = {"rendafixa", "rendafixa_internacional"}


def _load_json(name: str) -> Any:
    with (FIXTURE_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


def _backend_asset_to_domain(a: dict) -> Asset:
    asset_type = a["type"]
    if asset_type in RF_TYPES:
        return Asset(
            id=a["_id"],
            type=asset_type,
            name=a["name"],
            amount=float(a["value"]),
            strength=int(a["strength"]),
        )
    amount = float(a["amount"])
    value = float(a["value"])
    current_price = value / amount if amount > 0 else None
    return Asset(
        id=a["_id"],
        type=asset_type,
        name=a["name"],
        amount=amount,
        strength=int(a["strength"]),
        current_price=current_price,
        diagram_responses=a.get("diagramResponses"),
    )


def load_portfolio() -> Portfolio:
    user = _load_json("auth_me.json")
    assets = [_backend_asset_to_domain(a) for a in user["assets"]]
    targets = {g["type"]: float(g["value"]) for g in user["investimentGoals"]}
    questions = [
        Question(id=q["_id"], criteria=q["criterias"], text=q["question"], diagram=q["diagram"])
        for q in user["diagramQuestions"]
    ]
    return Portfolio(assets=assets, targets=targets, questions=questions)


def normalize_asset_type(t: str) -> str:
    """Backend emits both 'acoesnacionais' and 'acoes_nacionais' across responses.
    This normalizes to the underscored canonical form.
    """
    mapping = {
        "acoesnacionais": "acoes_nacionais",
        "acoesinternacionais": "acoes_internacionais",
        "fundosimobiliarios": "fundos_imobiliarios",
        "rendafixainternacional": "rendafixa_internacional",
    }
    return mapping.get(t, t)


def load_expected(aporte: int) -> list[dict]:
    """Returns the list of BackendSuggestion dicts for the given aporte value.
    R$500/R$1000 fixtures wrap the list in { "responseBody": [...] };
    R$10000 fixture is the bare list.
    """
    if aporte == 10000:
        return _load_json("suggestions_10000.json")
    raw = _load_json(f"suggestions_{aporte}.json")
    return raw["responseBody"]


@pytest.fixture
def portfolio() -> Portfolio:
    return load_portfolio()
