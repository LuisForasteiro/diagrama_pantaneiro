from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.category import CategoryTreeUpdate


def _tree(groups):
    return {"groups": groups}


def test_valid_two_level_tree_parses():
    body = CategoryTreeUpdate.model_validate(_tree([
        {"name": "Bitcoin", "weightPct": 40, "children": []},
        {"name": "Brasil", "weightPct": 25, "children": [
            {"name": "Ações", "weightPct": 50, "children": []},
            {"name": "Renda Fixa", "weightPct": 50, "children": []},
        ]},
        {"name": "Internacional", "weightPct": 35, "children": [
            {"name": "Ações americanas", "weightPct": 50, "children": []},
            {"name": "REITs", "weightPct": 25, "children": []},
            {"name": "RF americana", "weightPct": 25, "children": []},
        ]},
    ]))
    assert len(body.groups) == 3


def test_group_weights_must_sum_100():
    with pytest.raises(ValidationError):
        CategoryTreeUpdate.model_validate(_tree([
            {"name": "A", "weightPct": 40, "children": []},
            {"name": "B", "weightPct": 40, "children": []},
        ]))


def test_child_weights_must_sum_100():
    with pytest.raises(ValidationError):
        CategoryTreeUpdate.model_validate(_tree([
            {"name": "Brasil", "weightPct": 100, "children": [
                {"name": "Ações", "weightPct": 60, "children": []},
                {"name": "RF", "weightPct": 30, "children": []},
            ]},
        ]))


def test_depth_capped_at_two_levels():
    with pytest.raises(ValidationError):
        CategoryTreeUpdate.model_validate(_tree([
            {"name": "Brasil", "weightPct": 100, "children": [
                {"name": "Ações", "weightPct": 100, "children": [
                    {"name": "Tech", "weightPct": 100, "children": []},
                ]},
            ]},
        ]))


def test_empty_tree_allowed():
    body = CategoryTreeUpdate.model_validate(_tree([]))
    assert body.groups == []
