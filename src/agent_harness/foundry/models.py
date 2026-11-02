"""Strict request, response, and smoke-test result contracts."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FoundryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deployment: str
    deployment_role: str
    prompt: str

    @field_validator("deployment", "deployment_role", "prompt")
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Foundry request values must not be blank")
        return value


class FoundryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deployment: str
    model_identifier: str | None = None
    content: str
    response_valid: bool
    token_usage: dict[str, int] | None = None


class DeploymentSmokeTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    deployment: str
    deployment_role: str
    success: bool
    latency_ms: int = Field(ge=0)
    model_identifier: str | None = None
    response_valid: bool = False
    sanitized_error: str | None = None
