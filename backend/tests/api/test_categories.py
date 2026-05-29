from __future__ import annotations

import pytest
from httpx import AsyncClient
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


async def _auth(client: AsyncClient, email: str) -> dict[str, str]:
    await client.post("/api/auth/register", json={"email": email, "password": "StrongPass!123"})
    r = await client.post(
        "/api/auth/jwt/login", data={"username": email, "password": "StrongPass!123"}
    )
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    await client.get("/api/positions", headers=headers)  # triggers default-portfolio seed
    return headers


_TREE = {"groups": [
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
]}


async def test_categories_requires_auth(client: AsyncClient):
    r = await client.get("/api/categories")
    assert r.status_code == 401


async def test_put_then_get_roundtrip(client: AsyncClient):
    headers = await _auth(client, "cat1@example.com")
    r = await client.put("/api/categories", json=_TREE, headers=headers)
    assert r.status_code == 200
    groups = r.json()
    assert {g["name"] for g in groups} == {"Bitcoin", "Brasil", "Internacional"}
    brasil = next(g for g in groups if g["name"] == "Brasil")
    assert len(brasil["children"]) == 2
    assert all(c["parentId"] == brasil["id"] for c in brasil["children"])

    r2 = await client.get("/api/categories", headers=headers)
    assert {g["name"] for g in r2.json()} == {"Bitcoin", "Brasil", "Internacional"}


async def test_put_replaces_previous_tree(client: AsyncClient):
    headers = await _auth(client, "cat2@example.com")
    await client.put("/api/categories", json=_TREE, headers=headers)
    await client.put("/api/categories", json={"groups": [
        {"name": "Tudo", "weightPct": 100, "children": []},
    ]}, headers=headers)
    r = await client.get("/api/categories", headers=headers)
    assert [g["name"] for g in r.json()] == ["Tudo"]


async def test_put_rejects_bad_sum(client: AsyncClient):
    headers = await _auth(client, "cat3@example.com")
    r = await client.put("/api/categories", json={"groups": [
        {"name": "A", "weightPct": 40, "children": []},
        {"name": "B", "weightPct": 40, "children": []},
    ]}, headers=headers)
    assert r.status_code == 422
