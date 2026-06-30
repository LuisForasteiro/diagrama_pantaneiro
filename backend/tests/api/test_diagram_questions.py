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
    # Trigger seeding via /positions
    await client.get("/api/positions", headers={"Authorization": f"Bearer {token}"})
    return token


async def test_list_diagram_questions_requires_auth(client: AsyncClient) -> None:
    r = await client.get("/api/diagram-questions")
    assert r.status_code == 401


async def test_list_diagram_questions_returns_seeded_banks(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "dq@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get("/api/diagram-questions", headers=headers)
    assert r.status_code == 200
    questions = r.json()
    # 11 cerrado + 12 imobiliarios + 11 etfs = 34
    assert len(questions) == 34

    by_diagram: dict[str, list[dict]] = {}
    for q in questions:
        by_diagram.setdefault(q["diagramType"], []).append(q)
    assert len(by_diagram["diagrama-do-cerrado"]) == 11
    assert len(by_diagram["investimentos-imobiliarios"]) == 12
    assert len(by_diagram["diagrama-etfs"]) == 11


async def test_list_diagram_questions_filter_by_diagram(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "dqf@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    r = await client.get(
        "/api/diagram-questions?diagram=investimentos-imobiliarios",
        headers=headers,
    )
    assert r.status_code == 200
    questions = r.json()
    assert len(questions) == 12
    for q in questions:
        assert q["diagramType"] == "investimentos-imobiliarios"


async def test_create_question_recomputes_equity_strengths(
    client: AsyncClient,
) -> None:
    """Adding a cerrado question increases N, so existing AN positions see
    their strength drop by 1 (2*yes − N shifts)."""
    token = await _register_login_seed(client, "qc1@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    before_rows = (await client.get("/api/positions", headers=headers)).json()
    vale3_before = next(p for p in before_rows if p["name"] == "VALE3")
    wege3_before = next(p for p in before_rows if p["name"] == "WEGE3")

    r = await client.post(
        "/api/diagram-questions",
        json={
            "diagramType": "diagrama-do-cerrado",
            "criterias": "NOVO CRITÉRIO",
            "questionText": "A empresa exibe novo critério?",
        },
        headers=headers,
    )
    assert r.status_code == 201
    created = r.json()
    assert created["diagramType"] == "diagrama-do-cerrado"
    assert created["displayOrder"] == 11  # appended after existing 11 (0..10)

    after_rows = (await client.get("/api/positions", headers=headers)).json()
    vale3_after = next(p for p in after_rows if p["name"] == "VALE3")
    wege3_after = next(p for p in after_rows if p["name"] == "WEGE3")
    assert vale3_after["strength"] == vale3_before["strength"] - 1
    assert wege3_after["strength"] == wege3_before["strength"] - 1


async def test_patch_question_does_not_affect_strength(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "qc2@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    questions = (
        await client.get(
            "/api/diagram-questions?diagram=diagrama-do-cerrado", headers=headers
        )
    ).json()
    target = questions[0]

    before_rows = (await client.get("/api/positions", headers=headers)).json()
    vale3_before = next(p for p in before_rows if p["name"] == "VALE3")

    r = await client.patch(
        f"/api/diagram-questions/{target['id']}",
        json={"criterias": "ROE Revised"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["criterias"] == "ROE Revised"

    after_rows = (await client.get("/api/positions", headers=headers)).json()
    vale3_after = next(p for p in after_rows if p["name"] == "VALE3")
    assert vale3_after["strength"] == vale3_before["strength"]


async def test_delete_question_recomputes_and_scrubs_stale_response(
    client: AsyncClient,
) -> None:
    """Deleting a question shrinks N AND removes the stale ID from
    diagram_responses on every affected position. Net strength change: +1
    (N shrinks by 1) unless the position had answered yes, in which case
    its yes-count also drops by 1, netting −1 on strength."""
    token = await _register_login_seed(client, "qc3@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    questions = (
        await client.get(
            "/api/diagram-questions?diagram=diagrama-do-cerrado", headers=headers
        )
    ).json()
    before_rows = (await client.get("/api/positions", headers=headers)).json()
    wege3_before = next(p for p in before_rows if p["name"] == "WEGE3")
    # WEGE3 originally answered ALL 11 yes (strength +11)
    assert wege3_before["strength"] == 11
    assert len(wege3_before["diagramResponses"]) == 11

    # Deleting one question WEGE3 had ticked: yes drops 11→10, N drops 11→10.
    # New strength = 2*10 − 10 = 10. Net −1.
    target = questions[0]
    r = await client.delete(
        f"/api/diagram-questions/{target['id']}", headers=headers
    )
    assert r.status_code == 204

    after_rows = (await client.get("/api/positions", headers=headers)).json()
    wege3_after = next(p for p in after_rows if p["name"] == "WEGE3")
    assert wege3_after["strength"] == 10
    assert len(wege3_after["diagramResponses"]) == 10


async def test_delete_question_rejects_cross_user(client: AsyncClient) -> None:
    token_a = await _register_login_seed(client, "qc-a@example.com")
    qs = (
        await client.get(
            "/api/diagram-questions",
            headers={"Authorization": f"Bearer {token_a}"},
        )
    ).json()
    q_id = qs[0]["id"]

    token_b = await _register_login_seed(client, "qc-b@example.com")
    r = await client.delete(
        f"/api/diagram-questions/{q_id}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert r.status_code == 404


async def test_create_question_invalid_diagram_rejected(
    client: AsyncClient,
) -> None:
    token = await _register_login_seed(client, "qc-inv@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    r = await client.post(
        "/api/diagram-questions",
        json={"diagramType": "bogus", "questionText": "x"},
        headers=headers,
    )
    assert r.status_code == 422
