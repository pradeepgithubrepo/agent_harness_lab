from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, str_strip_whitespace=True)


class ToolRequest(StrictModel):
    correlation_id: str | None = Field(default=None, max_length=80)
    workflow_id: str | None = Field(default=None, max_length=80)

    @field_validator("correlation_id", "workflow_id")
    @classmethod
    def nonblank_optional(cls, value: str | None) -> str | None:
        if value is not None and not value:
            raise ValueError("identifier must not be blank")
        return value

    def resolved_correlation_id(self) -> str:
        return self.correlation_id or str(uuid4())


def utcnow() -> datetime:
    return datetime.now(timezone.utc)
