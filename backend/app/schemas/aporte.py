from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class AporteCreate(BaseModel):
    value: float = Field(gt=0)


class AporteAllocationOut(BaseModel):
    id: uuid.UUID
    position_id: uuid.UUID | None = None
    position_name_snapshot: str
    asset_type_snapshot: str
    price_at_aporte_brl: float | None = None
    suggested_value_brl: float
    suggested_quantity: float
    applied: bool
    applied_at: datetime | None = None
    applied_value_brl: float | None = None
    applied_quantity: float | None = None

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=to_camel, from_attributes=True
    )


class AporteEventOut(BaseModel):
    id: uuid.UUID
    aporte_value_brl: float
    created_at: datetime
    allocations: list[AporteAllocationOut]

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=to_camel, from_attributes=True
    )


class ApplyRequest(BaseModel):
    applied_value_brl: float | None = None
    applied_quantity: float | None = None

    # The frontend sends camelCase (appliedValueBrl / appliedQuantity). Without
    # this alias the keys silently miss the snake_case fields and the user's
    # last-mile qty/value edit is dropped — apply falls back to the suggestion.
    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
