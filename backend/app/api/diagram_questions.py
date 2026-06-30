from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func as sa_func
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.core.db import get_async_session
from app.models.diagram_question import DiagramQuestion
from app.models.position import Position
from app.models.user import User
from app.schemas.diagram_question import (
    DiagramQuestionCreate,
    DiagramQuestionOut,
    DiagramQuestionUpdate,
)
from app.services.strength import DIAGRAM_FOR_CLASS

router = APIRouter(prefix="/api/diagram-questions", tags=["diagram-questions"])


VALID_DIAGRAMS = {
    "diagrama-do-cerrado",
    "investimentos-imobiliarios",
    "diagrama-etfs",
}


async def _bank_size(
    session: AsyncSession, user_id: uuid.UUID, diagram_type: str
) -> int:
    return (
        await session.execute(
            sa_func.count(DiagramQuestion.id).select().where(  # type: ignore[attr-defined]
                DiagramQuestion.user_id == user_id,
                DiagramQuestion.diagram_type == diagram_type,
            )
        )
    ).scalar_one()


async def _recompute_strengths_for_diagram(
    session: AsyncSession,
    user_id: uuid.UUID,
    diagram_type: str,
    *,
    drop_response_id: str | None = None,
) -> None:
    """After a question is added or deleted, recompute strength for every
    position whose asset_type maps to this diagram_type. If `drop_response_id`
    is given (on delete), also remove that ID from each position's
    diagram_responses list before recomputing."""
    # Which asset types use this diagram
    affected_types = [t for t, d in DIAGRAM_FOR_CLASS.items() if d == diagram_type]
    if not affected_types:
        return

    n = (
        await session.execute(
            select(sa_func.count(DiagramQuestion.id)).where(
                DiagramQuestion.user_id == user_id,
                DiagramQuestion.diagram_type == diagram_type,
            )
        )
    ).scalar_one()

    # Diagram questions are user-level (shared across all the user's portfolios),
    # so the recompute must span every position in every portfolio the user owns.
    positions = (
        await session.execute(
            select(Position).where(
                Position.user_id == user_id,
                Position.asset_type.in_(affected_types),
            )
        )
    ).scalars().all()

    for p in positions:
        responses = list(p.diagram_responses or [])
        if drop_response_id and drop_response_id in responses:
            responses = [r for r in responses if r != drop_response_id]
            p.diagram_responses = responses
        p.strength = 2 * len(responses) - n


@router.get("", response_model=list[DiagramQuestionOut])
async def list_diagram_questions(
    diagram: str | None = Query(default=None),
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[DiagramQuestionOut]:
    stmt = (
        select(DiagramQuestion)
        .where(DiagramQuestion.user_id == user.id)
        .order_by(DiagramQuestion.diagram_type, DiagramQuestion.display_order)
    )
    if diagram:
        stmt = stmt.where(DiagramQuestion.diagram_type == diagram)
    rows = (await session.execute(stmt)).scalars().all()
    return [DiagramQuestionOut.model_validate(r) for r in rows]


@router.post("", response_model=DiagramQuestionOut, status_code=status.HTTP_201_CREATED)
async def create_diagram_question(
    body: DiagramQuestionCreate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> DiagramQuestionOut:
    if body.diagram_type not in VALID_DIAGRAMS:
        raise HTTPException(
            status_code=422,
            detail=f"diagram_type must be one of {sorted(VALID_DIAGRAMS)}",
        )

    # Default display_order to (current max + 1) for this diagram
    if body.display_order is None:
        current_max = (
            await session.execute(
                select(sa_func.max(DiagramQuestion.display_order)).where(
                    DiagramQuestion.user_id == user.id,
                    DiagramQuestion.diagram_type == body.diagram_type,
                )
            )
        ).scalar_one()
        next_order = (current_max or -1) + 1
    else:
        next_order = body.display_order

    q = DiagramQuestion(
        user_id=user.id,
        diagram_type=body.diagram_type,
        criterias=body.criterias,
        question_text=body.question_text,
        display_order=next_order,
    )
    session.add(q)
    await session.flush()

    # Adding a question grows N for everyone using this diagram; recompute.
    await _recompute_strengths_for_diagram(session, user.id, body.diagram_type)
    await session.commit()
    await session.refresh(q)
    return DiagramQuestionOut.model_validate(q)


@router.patch("/{question_id}", response_model=DiagramQuestionOut)
async def update_diagram_question(
    question_id: uuid.UUID,
    body: DiagramQuestionUpdate,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> DiagramQuestionOut:
    q = (
        await session.execute(
            select(DiagramQuestion).where(
                DiagramQuestion.id == question_id,
                DiagramQuestion.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if q is None:
        raise HTTPException(status_code=404, detail="question not found")

    updates: dict[str, Any] = body.model_dump(exclude_unset=True)
    for k, v in updates.items():
        setattr(q, k, v)
    # PATCH doesn't change N, so no strength recompute needed.
    await session.commit()
    await session.refresh(q)
    return DiagramQuestionOut.model_validate(q)


@router.delete("/{question_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_diagram_question(
    question_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    q = (
        await session.execute(
            select(DiagramQuestion).where(
                DiagramQuestion.id == question_id,
                DiagramQuestion.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if q is None:
        raise HTTPException(status_code=404, detail="question not found")

    diagram_type = q.diagram_type
    # external_id was how positions referenced questions during auto-import;
    # newly created questions may only be referenced by the UUID id (as string).
    response_ids_to_drop = [str(q.id)]
    if q.external_id:
        response_ids_to_drop.append(q.external_id)

    await session.delete(q)
    await session.flush()

    # Deleting shrinks N AND may leave stale IDs in diagram_responses.
    for rid in response_ids_to_drop:
        await _recompute_strengths_for_diagram(
            session, user.id, diagram_type, drop_response_id=rid
        )

    await session.commit()
