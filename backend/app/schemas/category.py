from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class SubcategoryIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    weight_pct: float = Field(ge=0, le=100)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("name")
    @classmethod
    def _trim(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class GroupIn(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    weight_pct: float = Field(ge=0, le=100)
    children: list[SubcategoryIn] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("name")
    @classmethod
    def _trim(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("name must not be blank")
        return v.strip()


class CategoryTreeIn(BaseModel):
    groups: list[GroupIn] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class SubcategoryOut(BaseModel):
    id: uuid.UUID
    name: str
    weight_pct: float

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class GroupOut(BaseModel):
    id: uuid.UUID
    name: str
    weight_pct: float
    children: list[SubcategoryOut] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class CategoryTreeOut(BaseModel):
    groups: list[GroupOut] = Field(default_factory=list)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
