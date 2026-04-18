from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PositionOut(BaseModel):
    id: uuid.UUID
    name: str
    asset_type: str
    amount: float
    current_price: float | None = None
    current_value_brl: float  # derived: price x amount OR amount (RF)
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
    amount: float
    current_price: float | None = None
    strength: int
    diagram_responses: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class PositionUpdate(BaseModel):
    amount: float | None = None
    current_price: float | None = None
    strength: int | None = None
    diagram_responses: list[str] | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
