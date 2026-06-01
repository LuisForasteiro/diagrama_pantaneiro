from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

from app.schemas.target import ALL_CLASS_TYPES


def _validate_effective_class(v: str | None) -> str | None:
    if v is None:
        return v
    if v not in ALL_CLASS_TYPES:
        raise ValueError(f"unknown effective_class: {v}")
    return v


class PositionOut(BaseModel):
    id: uuid.UUID
    name: str
    asset_type: str
    effective_class: str | None = None
    amount: float
    current_price: float | None = None
    current_value_brl: float  # derived: price x amount OR amount (RF)
    price_updated_at: datetime | None = None
    category_id: uuid.UUID | None = None
    strength: int
    diagram_responses: list[str] | None = None
    source: str

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class PositionCreate(BaseModel):
    name: str
    asset_type: str
    effective_class: str | None = None
    category_id: uuid.UUID | None = None
    amount: float
    current_price: float | None = None
    strength: int
    diagram_responses: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("effective_class")
    @classmethod
    def _validate_eff(cls, v: str | None) -> str | None:
        return _validate_effective_class(v)


class PositionUpdate(BaseModel):
    amount: float | None = None
    current_price: float | None = None
    strength: int | None = None
    diagram_responses: list[str] | None = None
    effective_class: str | None = None
    category_id: uuid.UUID | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("effective_class")
    @classmethod
    def _validate_eff(cls, v: str | None) -> str | None:
        return _validate_effective_class(v)
