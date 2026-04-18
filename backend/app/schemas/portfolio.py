from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class PortfolioOut(BaseModel):
    id: uuid.UUID
    name: str
    is_default: bool
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class PortfolioCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("name")
    @classmethod
    def _trim(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed


class PortfolioRename(PortfolioCreate):
    pass
