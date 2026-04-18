from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class CandidateOut(BaseModel):
    name: str
    label: str | None = None
    current_price_brl: float | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
