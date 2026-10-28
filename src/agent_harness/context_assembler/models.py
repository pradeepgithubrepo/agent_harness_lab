"""Application policy models for LangChain context middleware."""

from __future__ import annotations

from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContextType(StrEnum):
    WORKING_MEMORY = "working_memory"
    EVIDENCE = "evidence"
    RUNTIME_STATE = "runtime_state"


class ContextItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    item_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    context_type: ContextType
    mandatory: bool = False
    relevance: float = Field(default=0, ge=0)
    priority: int = 0
    estimated_tokens: int | None = Field(default=None, ge=0)
    compact_content: str | None = None
    evidence_pointer: str | None = None


class ContextAssemblyConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    model_context_limit: int = Field(gt=0)
    application_operating_limit: int = Field(gt=0)
    reserved_output_tokens: int = Field(ge=0)
    safety_margin_tokens: int = Field(ge=0)
    maximum_input_utilisation: float = Field(default=0.85, gt=0, le=1)
    characters_per_token: int = Field(default=4, gt=0)


class ContextRuntime(BaseModel):
    """Per-invocation data supplied through LangChain's invocation context."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    request_id: str
    agent_role: str
    task_type: str
    workflow_state: dict[str, Any]
    context_items: list[ContextItem]
    permitted_tool_names: set[str]
    config: ContextAssemblyConfig
    manifest: ContextManifest | None = None


class ContextManifest(BaseModel):
    """Audit metadata only: it never includes raw context, messages, or tools."""

    model_config = ConfigDict(frozen=True)

    request_id: str
    agent_role: str
    effective_context_limit: int
    available_input_tokens: int
    packing_limit: int
    estimated_tokens_used: int
    remaining_tokens: int
    included_item_ids: tuple[str, ...]
    compacted_item_ids: tuple[str, ...]
    excluded_items: dict[str, str]
    selected_tool_names: tuple[str, ...]
    warnings: tuple[str, ...]
    policy_version: str


class ContextAssemblyResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    selected_items: tuple[ContextItem, ...]
    selected_tool_names: tuple[str, ...]
    manifest: ContextManifest
