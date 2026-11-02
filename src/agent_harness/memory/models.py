"""Typed, auditable three-tier memory contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class MemoryBase(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: str = Field(default_factory=lambda: str(uuid4()))
    scope_id: str
    created_at: datetime = Field(default_factory=utcnow)
    updated_at: datetime = Field(default_factory=utcnow)
    source: str
    sensitivity: Literal["public", "internal", "restricted"] = "internal"
    status: Literal["active", "superseded", "archived", "invalid"] = "active"
    version: int = Field(default=1, ge=1)
    provenance: dict[str, str] = Field(default_factory=dict)


class WorkingMemory(MemoryBase):
    session_id: str
    task_id: str
    objective: str
    workflow_state_projection: dict[str, Any] = Field(default_factory=dict)
    temporary_tool_results: list[dict[str, Any]] = Field(default_factory=list)
    evidence_references: list[str] = Field(default_factory=list)
    retry_count: int = Field(default=0, ge=0)
    pending_question: str | None = None
    next_proposed_action: str | None = None


class EpisodeMemory(MemoryBase):
    session_summary: str
    entities: list[str] = Field(default_factory=list)
    actions_taken: list[str] = Field(default_factory=list)
    outcome: str
    failures_and_recoveries: list[str] = Field(default_factory=list)
    user_corrections: list[str] = Field(default_factory=list)
    lessons_learned: list[str] = Field(default_factory=list)
    importance: float = Field(ge=0, le=1)
    promotion_status: Literal["not_reviewed", "promoted", "rejected"] = "not_reviewed"
    source_working_memory_ids: list[str] = Field(default_factory=list)


class SemanticMemory(MemoryBase):
    subject: str
    fact: str
    supporting_details: str | None = None
    source_episode_id: str
    confidence: float = Field(ge=0, le=1)
    valid_from: datetime = Field(default_factory=utcnow)
    valid_to: datetime | None = None
    superseded_by: str | None = None
    security_scope: str


class MemoryCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory: WorkingMemory | EpisodeMemory | SemanticMemory
    relevance: float = Field(ge=0, le=1)
    estimated_tokens: int = Field(ge=0)
    retrieval_reason: str


class TierMovementDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_tier: Literal["working", "episodic", "semantic"]
    target_tier: Literal["working", "episodic", "semantic", "none"]
    action: Literal["retain", "compress_to_episode", "promote_to_semantic", "update", "supersede", "reject"]
    reason_code: str
    confidence: float = Field(ge=0, le=1)
    validation_required: bool
    approved: bool


class EvictionDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")
    memory_id: str
    tier: Literal["working", "episodic", "semantic"]
    action: Literal["keep", "expire", "delete", "archive", "supersede"]
    reason_code: str
    evaluated_at: datetime = Field(default_factory=utcnow)


class MemoryContextPackage(BaseModel):
    model_config = ConfigDict(extra="forbid")
    working_memory: list[MemoryCandidate] = Field(default_factory=list)
    episodic_memories: list[MemoryCandidate] = Field(default_factory=list)
    semantic_memories: list[MemoryCandidate] = Field(default_factory=list)
    excluded_memories: list[MemoryCandidate] = Field(default_factory=list)
    retrieval_reason: str
    total_candidate_tokens: int = Field(ge=0)


class MemoryAuditEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    occurred_at: datetime = Field(default_factory=utcnow)
    memory_id: str
    scope_id: str
    event_type: Literal["created", "movement", "eviction", "retrieval", "updated", "superseded"]
    tier: Literal["working", "episodic", "semantic"]
    decision: TierMovementDecision | EvictionDecision | None = None
    reason_code: str
