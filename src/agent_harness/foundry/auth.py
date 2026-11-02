"""Replaceable authentication boundary for Foundry SDK clients."""

from __future__ import annotations

from typing import Protocol

from openai import OpenAI

from .config import FoundrySettings


class FoundryAuthenticationProvider(Protocol):
    """Creates an SDK client without exposing credential material to callers."""

    def create_sdk_client(self, settings: FoundrySettings) -> OpenAI: ...


class ApiKeyAuthenticationProvider:
    """Development API-key authentication; the key remains a SecretStr in settings."""

    def create_sdk_client(self, settings: FoundrySettings) -> OpenAI:
        assert settings.foundry_api_key is not None
        return OpenAI(
            base_url=f"{settings.foundry_endpoint.rstrip('/')}/openai/v1/",
            api_key=settings.foundry_api_key.get_secret_value(),
        )
