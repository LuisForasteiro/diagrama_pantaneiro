from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class PriceFailureOut(BaseModel):
    name: str
    reason: str

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class RefreshSummaryOut(BaseModel):
    refreshed: int
    skipped_manual: int
    failed: list[PriceFailureOut]

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
