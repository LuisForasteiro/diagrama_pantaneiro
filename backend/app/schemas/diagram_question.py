from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel


class DiagramQuestionOut(BaseModel):
    id: uuid.UUID
    diagram_type: str
    criterias: str
    question_text: str
    display_order: int
    external_id: str | None = None

    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
        from_attributes=True,
    )


class DiagramQuestionCreate(BaseModel):
    diagram_type: str
    criterias: str = ""
    question_text: str
    display_order: int | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)


class DiagramQuestionUpdate(BaseModel):
    criterias: str | None = None
    question_text: str | None = None
    display_order: int | None = None

    model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)
