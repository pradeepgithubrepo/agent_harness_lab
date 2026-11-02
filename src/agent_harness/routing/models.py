"""Typed contracts for routing evaluation."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RoutingDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Literal["system_one", "system_two", "human_review"]
    confidence: float = Field(ge=0, le=1)
    risk_level: Literal["low", "medium", "high"]
    reason_code: str = Field(min_length=1)
    selected_deployment: str = Field(min_length=1)
    approval_required: bool


class RoutingCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request_id: str
    category: Literal["simple_lookup", "ambiguous", "investigation", "state_change"]
    request: str
    expected_route: Literal["system_one", "system_two", "human_review"]


class RoutingEvaluationResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy: str
    request_id: str
    expected_route: str
    actual_route: str
    route_correct: bool
    confidence: float | None = None
    selected_deployment: str | None = None
    underlying_model: str | None = None
    latency_ms: int = Field(ge=0)
    token_usage: dict[str, int] | None = None
    policy_override: str | None = None
    validation_error: str | None = None
    sanitized_failure: str | None = None


class RoutingOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision: RoutingDecision
    underlying_model: str | None = None
    token_usage: dict[str, int] | None = None
    policy_override: str | None = None
    validation_error: str | None = None
