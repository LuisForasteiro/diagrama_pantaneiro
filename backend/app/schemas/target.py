from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from app.services.types import ClassType

ALL_CLASS_TYPES: tuple[str, ...] = (
    "acoes_nacionais",
    "acoes_internacionais",
    "fundos_imobiliarios",
    "reits",
    "criptomoedas",
    "rendafixa",
    "rendafixa_internacional",
)


class TargetOut(BaseModel):
    id: uuid.UUID
    asset_type: str
    target_percentage: float

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class TargetUpdateIn(BaseModel):
    asset_type: str
    target_percentage: int = Field(ge=0, le=100)

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("asset_type")
    @classmethod
    def _known_class(cls, v: str) -> str:
        if v not in ALL_CLASS_TYPES:
            raise ValueError(f"unknown asset_type: {v}")
        return v


class TargetsUpdateBody(BaseModel):
    targets: list[TargetUpdateIn]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("targets")
    @classmethod
    def _all_seven_and_sum_100(
        cls, v: list[TargetUpdateIn]
    ) -> list[TargetUpdateIn]:
        if len(v) != 7:
            raise ValueError("exactly 7 target entries required")
        types_seen = [t.asset_type for t in v]
        if len(set(types_seen)) != 7:
            raise ValueError("duplicate asset_type entries")
        if set(types_seen) != set(ALL_CLASS_TYPES):
            raise ValueError("targets must cover all 7 asset classes")
        if sum(t.target_percentage for t in v) != 100:
            raise ValueError("target percentages must sum to 100")
        return v


class PresetIn(BaseModel):
    name: str = Field(min_length=1, max_length=48)
    values: dict[str, int]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)

    @field_validator("name")
    @classmethod
    def _trim_name(cls, v: str) -> str:
        trimmed = v.strip()
        if not trimmed:
            raise ValueError("name must not be blank")
        return trimmed

    @field_validator("values")
    @classmethod
    def _values_shape(cls, v: dict[str, int]) -> dict[str, int]:
        if set(v.keys()) != set(ALL_CLASS_TYPES):
            raise ValueError("values must cover exactly the 7 asset classes")
        for k, pct in v.items():
            if not isinstance(pct, int) or isinstance(pct, bool):
                raise ValueError(f"values[{k}] must be an integer")
            if pct < 0 or pct > 100:
                raise ValueError(f"values[{k}] must be in [0, 100]")
        if sum(v.values()) != 100:
            raise ValueError("values must sum to 100")
        return v


class PresetOut(BaseModel):
    id: uuid.UUID
    name: str
    values: dict[str, int]
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )
