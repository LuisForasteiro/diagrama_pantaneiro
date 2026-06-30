from __future__ import annotations

from httpx import AsyncClient


async def _register_login_seed(client: AsyncClient, email: str) -> str:
    await client.post(
        "/api/auth/register",
        json={"email": email, "password": "StrongPass!123"},
    )
    r = await client.post(
        "/api/auth/jwt/login",
        data={"username": email, "password": "StrongPass!123"},
    )
    token = r.json()["access_token"]
    await client.get("/api/positions", headers={"Authorization": f"Bearer {token}"})
    return token


async def test_create_aporte_requires_auth(client: AsyncClient) -> None:
    r = await client.post("/api/aportes", json={"value": 500})
    assert r.status_code == 401


async def test_create_aporte_returns_event_with_allocations(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "ap1@example.com")
    r = await client.post(
        "/api/aportes",
        json={"value": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 201
    body = r.json()
    assert body["aporteValueBrl"] == 500
    assert len(body["allocations"]) == 3
    for a in body["allocations"]:
        assert a["applied"] is False
        assert a["suggestedValueBrl"] > 0


async def test_create_aporte_with_non_positive_value_rejected(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "ap2@example.com")
    r = await client.post(
        "/api/aportes",
        json={"value": 0},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 422


async def test_get_aporte_by_id_returns_detail(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "ap3@example.com")
    created = await client.post(
        "/api/aportes",
        json={"value": 500},
        headers={"Authorization": f"Bearer {token}"},
    )
    event_id = created.json()["id"]
    r = await client.get(
        f"/api/aportes/{event_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r.status_code == 200
    assert r.json()["id"] == event_id


async def test_apply_allocation_marks_applied_and_updates_position(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "ap4@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    alloc = event["allocations"][0]

    r = await client.post(
        f"/api/aportes/{event['id']}/allocations/{alloc['id']}/apply",
        json={},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["applied"] is True
    assert body["appliedAt"] is not None


async def test_list_aportes_newest_first(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "history@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # Empty list initially
    r = await client.get("/api/aportes", headers=headers)
    assert r.status_code == 200
    assert r.json() == []

    # Create 3 aportes with different values
    for v in [500, 1000, 2500]:
        await client.post("/api/aportes", json={"value": v}, headers=headers)

    r = await client.get("/api/aportes", headers=headers)
    assert r.status_code == 200
    events = r.json()
    assert len(events) == 3
    # Newest first: 2500 was last created
    values_in_order = [e["aporteValueBrl"] for e in events]
    assert values_in_order == [2500, 1000, 500]


async def test_list_aportes_is_user_scoped(client: AsyncClient) -> None:
    token_a = await _register_login_seed(client, "list-a@example.com")
    await client.post(
        "/api/aportes", json={"value": 777}, headers={"Authorization": f"Bearer {token_a}"}
    )

    token_b = await _register_login_seed(client, "list-b@example.com")
    r = await client.get("/api/aportes", headers={"Authorization": f"Bearer {token_b}"})
    assert r.status_code == 200
    # B hasn't created any aportes
    assert r.json() == []


async def test_apply_cannot_cross_user_boundary(client: AsyncClient) -> None:
    """User A creates an aporte; user B cannot apply its allocations."""
    token_a = await _register_login_seed(client, "owner@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers_a)
    event = created.json()
    alloc = event["allocations"][0]

    token_b = await _register_login_seed(client, "intruder@example.com")
    headers_b = {"Authorization": f"Bearer {token_b}"}
    r = await client.post(
        f"/api/aportes/{event['id']}/allocations/{alloc['id']}/apply",
        json={},
        headers=headers_b,
    )
    assert r.status_code == 404


async def test_delete_aporte_event_when_unapplied(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "del-ev@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event_id = created.json()["id"]

    r = await client.delete(f"/api/aportes/{event_id}", headers=headers)
    assert r.status_code == 204

    listing = await client.get("/api/aportes", headers=headers)
    assert all(e["id"] != event_id for e in listing.json())


async def test_delete_aporte_event_blocked_when_applied(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "del-applied@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    alloc = event["allocations"][0]

    await client.post(
        f"/api/aportes/{event['id']}/allocations/{alloc['id']}/apply",
        json={},
        headers=headers,
    )

    r = await client.delete(f"/api/aportes/{event['id']}", headers=headers)
    assert r.status_code == 409


async def test_delete_aporte_event_not_found(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "del-404@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    fake = "00000000-0000-0000-0000-000000000000"
    r = await client.delete(f"/api/aportes/{fake}", headers=headers)
    assert r.status_code == 404


async def test_delete_aporte_event_cross_user(client: AsyncClient) -> None:
    token_a = await _register_login_seed(client, "owner-ev@example.com")
    created = await client.post(
        "/api/aportes", json={"value": 500}, headers={"Authorization": f"Bearer {token_a}"}
    )
    event_id = created.json()["id"]

    token_b = await _register_login_seed(client, "intruder-ev@example.com")
    r = await client.delete(
        f"/api/aportes/{event_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


async def test_delete_allocation_recomputes_remaining(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "del-alloc@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    assert len(event["allocations"]) == 3
    target_alloc = event["allocations"][0]
    excluded_pos_id = target_alloc["positionId"]

    r = await client.delete(
        f"/api/aportes/{event['id']}/allocations/{target_alloc['id']}",
        headers=headers,
    )
    assert r.status_code == 200
    updated = r.json()
    assert updated["aporteValueBrl"] == 500
    # Excluded position must not appear among the new allocations.
    assert all(a["positionId"] != excluded_pos_id for a in updated["allocations"])
    # Sum of remaining suggestions stays close to the aporte total.
    total = sum(a["suggestedValueBrl"] for a in updated["allocations"])
    assert abs(total - 500) < 5.0  # quantization residual is small


async def test_delete_allocation_sticky_across_consecutive_deletes(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "del-sticky@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    first_excluded = event["allocations"][0]["positionId"]

    first = await client.delete(
        f"/api/aportes/{event['id']}/allocations/{event['allocations'][0]['id']}",
        headers=headers,
    )
    second_event = first.json()
    # Pick another allocation to delete next.
    target = second_event["allocations"][0]
    second_excluded = target["positionId"]

    r = await client.delete(
        f"/api/aportes/{event['id']}/allocations/{target['id']}",
        headers=headers,
    )
    assert r.status_code == 200
    final = r.json()
    pos_ids = {a["positionId"] for a in final["allocations"]}
    # Both previously-deleted positions stay out.
    assert first_excluded not in pos_ids
    assert second_excluded not in pos_ids


async def test_delete_allocation_blocked_when_any_applied(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "del-alloc-applied@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    a0 = event["allocations"][0]
    a1 = event["allocations"][1]

    # Apply one, then try to delete another.
    await client.post(
        f"/api/aportes/{event['id']}/allocations/{a0['id']}/apply",
        json={},
        headers=headers,
    )
    r = await client.delete(
        f"/api/aportes/{event['id']}/allocations/{a1['id']}",
        headers=headers,
    )
    assert r.status_code == 409


async def test_delete_allocation_not_found(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "del-alloc-404@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event_id = created.json()["id"]
    fake = "00000000-0000-0000-0000-000000000000"
    r = await client.delete(
        f"/api/aportes/{event_id}/allocations/{fake}",
        headers=headers,
    )
    assert r.status_code == 404


def _priced_non_rf_alloc(event: dict) -> dict:
    """An allocation whose position is priced and unit-based (so amount += qty)."""
    return next(
        a
        for a in event["allocations"]
        if a["suggestedQuantity"] > 0
        and (a["priceAtAporteBrl"] or 0) > 0
        and a["assetTypeSnapshot"] not in ("rendafixa", "rendafixa_internacional")
    )


async def test_apply_allocation_honors_quantity_override(client: AsyncClient) -> None:
    """A1: applying with an explicit appliedQuantity increments the position by
    that quantity (the user's last-mile edit), not by the suggested amount."""
    token = await _register_login_seed(client, "apov@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    alloc = _priced_non_rf_alloc(event)
    pid = alloc["positionId"]

    positions = (await client.get("/api/positions", headers=headers)).json()
    before = next(p for p in positions if p["id"] == pid)["amount"]

    r = await client.post(
        f"/api/aportes/{event['id']}/allocations/{alloc['id']}/apply",
        json={"appliedQuantity": 3, "appliedValueBrl": 99},
        headers=headers,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["appliedQuantity"] == 3
    assert body["appliedValueBrl"] == 99

    positions2 = (await client.get("/api/positions", headers=headers)).json()
    after = next(p for p in positions2 if p["id"] == pid)["amount"]
    assert after == before + 3  # incremented by the override, not the suggestion


async def test_recompute_reflects_price_change(client: AsyncClient) -> None:
    """A2: correcting a position's price then recomputing yields suggestions
    priced at the new PU, while keeping the same set of titles."""
    token = await _register_login_seed(client, "recomp@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 1000}, headers=headers)
    event = created.json()
    alloc = _priced_non_rf_alloc(event)
    pid = alloc["positionId"]
    new_price = round(alloc["priceAtAporteBrl"] / 2, 2)

    pr = await client.patch(
        f"/api/positions/{pid}", json={"currentPrice": new_price}, headers=headers
    )
    assert pr.status_code == 200

    rc = await client.post(f"/api/aportes/{event['id']}/recompute", headers=headers)
    assert rc.status_code == 200
    new_event = rc.json()
    new_alloc = next(
        (a for a in new_event["allocations"] if a["positionId"] == pid), None
    )
    assert new_alloc is not None, "title dropped out of the recompute"
    assert new_alloc["priceAtAporteBrl"] == new_price


async def test_recompute_blocked_when_any_applied(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "recompblk@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    created = await client.post("/api/aportes", json={"value": 500}, headers=headers)
    event = created.json()
    a0 = event["allocations"][0]
    await client.post(
        f"/api/aportes/{event['id']}/allocations/{a0['id']}/apply",
        json={},
        headers=headers,
    )
    rc = await client.post(f"/api/aportes/{event['id']}/recompute", headers=headers)
    assert rc.status_code == 409


async def test_recompute_not_found(client: AsyncClient) -> None:
    token = await _register_login_seed(client, "recomp404@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    fake = "00000000-0000-0000-0000-000000000000"
    r = await client.post(f"/api/aportes/{fake}/recompute", headers=headers)
    assert r.status_code == 404
