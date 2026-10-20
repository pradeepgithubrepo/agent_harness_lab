"""Pydantic models used by the context assembler."""

from __future__ import annotations

from enum import StrEnum
from math import ceil

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ContextCategory(StrEnum):
    """The supported sources of context."""

    WORKING_MEMORY = "working_memory"
    TOOL_SCHEMA = "tool_schema"
    RETRIEVED_DOCUMENT = "retrieved_document"


class TokenEstimator(BaseModel):
    """Estimate tokens from character count using a configurable ratio."""

    model_config = ConfigDict(frozen=True)

    characters_per_token: int = Field(default=4, gt=0)

    def estimate(self, content: str) -> int:
        """Return a conservative, non-zero estimate for non-empty content."""
        if not content:
            return 0
        return ceil(len(content) / self.characters_per_token)


class ContextCandidate(BaseModel):
    """A complete, indivisible unit of candidate context."""

    model_config = ConfigDict(frozen=True)

    id: str = Field(min_length=1)
    category: ContextCategory
    content: str
    token_estimate: int = Field(ge=0)
    priority: int = 0
    mandatory: bool = False

    @field_validator("content")
    @classmethod
    def require_content(cls, value: str) -> str:
        if not value:
            raise ValueError("content must not be empty")
        return value

    @classmethod
    def from_content(
        cls,
        *,
        id: str,
        category: ContextCategory,
        content: str,
        priority: int = 0,
        mandatory: bool = False,
        estimator: TokenEstimator | None = None,
    ) -> ContextCandidate:
        """Create a candidate with a character-based token estimate."""
        active_estimator = estimator or TokenEstimator()
        return cls(
            id=id,
            category=category,
            content=content,
            token_estimate=active_estimator.estimate(content),
            priority=priority,
            mandatory=mandatory,
        )


class AssemblyResult(BaseModel):
    """The auditable output of a context allocation."""

    model_config = ConfigDict(frozen=True)

    selected_candidate_ids: tuple[str, ...]
    excluded_candidate_ids: tuple[str, ...]
    used_tokens: int = Field(ge=0)
    remaining_tokens: int = Field(ge=0)
    exclusion_reasons: dict[str, str]
