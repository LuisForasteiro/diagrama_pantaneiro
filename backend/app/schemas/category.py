from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, field_validator
from pydantic.alias_generators import to_camel

_SUM_TOL = 0.01


class CategoryNodeIn(BaseModel):
    name: str
    weight_pct: float
    display_order: int | None = None
    children: list["CategoryNodeIn"] = []

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("name")
    @classmethod
    def _name_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("category name must not be blank")
        return v.strip()

    @field_validator("children")
    @classmethod
    def _max_depth_two(cls, v: list["CategoryNodeIn"]) -> list["CategoryNodeIn"]:
        # Subgrupos (nível 2) não podem ter filhos (nível 3).
        for child in v:
            if child.children:
                raise ValueError("category tree is limited to 2 levels")
        if v:
            total = sum(c.weight_pct for c in v)
            if abs(total - 100.0) > _SUM_TOL:
                raise ValueError("child weights must sum to 100")
        return v


class CategoryTreeUpdate(BaseModel):
    groups: list[CategoryNodeIn]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("groups")
    @classmethod
    def _group_weights_sum_100(cls, v: list[CategoryNodeIn]) -> list[CategoryNodeIn]:
        if v:
            total = sum(g.weight_pct for g in v)
            if abs(total - 100.0) > _SUM_TOL:
                raise ValueError("group weights must sum to 100")
        return v


class CategoryOut(BaseModel):
    id: uuid.UUID
    parent_id: uuid.UUID | None
    name: str
    weight_pct: float
    display_order: int
    children: list["CategoryOut"] = []

    model_config = ConfigDict(
        populate_by_name=True, alias_generator=to_camel, from_attributes=True
    )
