"""Typed, credential-safe configuration for Microsoft Foundry."""

from __future__ import annotations

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class FoundrySettings(BaseSettings):
    """Settings shared by every Foundry deployment client."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    foundry_endpoint: str
    foundry_api_key: SecretStr | None = None
    foundry_auth_mode: str = "api_key"
    foundry_light_deployment: str
    foundry_frontier_deployment: str
    foundry_router_deployment: str

    @field_validator(
        "foundry_endpoint",
        "foundry_light_deployment",
        "foundry_frontier_deployment",
        "foundry_router_deployment",
    )
    @classmethod
    def require_non_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Foundry configuration value must not be blank")
        return value

    @field_validator("foundry_auth_mode")
    @classmethod
    def validate_auth_mode(cls, value: str) -> str:
        if value != "api_key":
            raise ValueError("FOUNDRY_AUTH_MODE must be api_key")
        return value

    @model_validator(mode="after")
    def validate_api_key(self) -> "FoundrySettings":
        if self.foundry_auth_mode == "api_key" and self.foundry_api_key is None:
            raise ValueError("FOUNDRY_API_KEY is required for api_key authentication")
        return self

    def deployments(self) -> tuple[tuple[str, str], ...]:
        """Return the configured deployment names with their smoke-test roles."""
        return (
            (self.foundry_light_deployment, "lightweight"),
            (self.foundry_frontier_deployment, "frontier"),
            (self.foundry_router_deployment, "managed_router"),
        )
