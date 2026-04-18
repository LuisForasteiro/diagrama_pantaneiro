from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import current_active_user
from app.core.db import get_async_session
from app.models.target_preset import TargetPreset
from app.models.user import User
from app.schemas.target import PresetIn, PresetOut

router = APIRouter(prefix="/api/target-presets", tags=["target-presets"])


def _to_out(row: TargetPreset) -> PresetOut:
    return PresetOut(
        id=row.id,
        name=row.name,
        values=row.values_json,
        created_at=row.created_at,
    )


@router.get("", response_model=list[PresetOut])
async def list_presets(
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> list[PresetOut]:
    rows = (
        await session.execute(
            select(TargetPreset)
            .where(TargetPreset.user_id == user.id)
            .order_by(TargetPreset.created_at)
        )
    ).scalars().all()
    return [_to_out(r) for r in rows]


@router.post("", response_model=PresetOut, status_code=status.HTTP_201_CREATED)
async def create_preset(
    body: PresetIn,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> PresetOut:
    preset = TargetPreset(
        user_id=user.id,
        name=body.name,
        values_json=body.values,
    )
    session.add(preset)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="preset name already exists",
        )
    await session.refresh(preset)
    return _to_out(preset)


@router.delete("/{preset_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_preset(
    preset_id: uuid.UUID,
    user: User = Depends(current_active_user),
    session: AsyncSession = Depends(get_async_session),
) -> None:
    row = (
        await session.execute(
            select(TargetPreset).where(
                TargetPreset.id == preset_id,
                TargetPreset.user_id == user.id,
            )
        )
    ).scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="preset not found")
    await session.delete(row)
    await session.commit()
