from __future__ import annotations

from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from agent_harness.foundry.client import FoundryClient, FoundryClientError, build_smoke_prompt
from agent_harness.foundry.config import FoundrySettings
from agent_harness.foundry.models import FoundryRequest


class FakeResponses:
    def __init__(self, response: object | Exception) -> None:
        self.response = response
        self.calls: list[dict[str, str]] = []

    def create(self, **kwargs: str) -> object:
        self.calls.append(kwargs)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


class FakeSdk:
    def __init__(self, response: object | Exception) -> None:
        self.chat = SimpleNamespace(completions=FakeResponses(response))


def settings() -> FoundrySettings:
    return FoundrySettings(
        foundry_endpoint="https://foundry.example.invalid/models",
        foundry_api_key=SecretStr("nonsecret-placeholder"),
        foundry_light_deployment="gpt-5-mini",
        foundry_frontier_deployment="gpt-5.4",
        foundry_router_deployment="agent-router-managed",
    )


def test_client_returns_validated_structured_response() -> None:
    sdk = FakeSdk(
        SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content='{"status":"ok","deployment_role":"lightweight"}'
                    )
                )
            ],
            model="gpt-5-mini-2026-01-01",
        )
    )
    client = FoundryClient(settings(), sdk_client=sdk)

    response = client.complete(
        FoundryRequest(
            deployment="gpt-5-mini",
            deployment_role="lightweight",
            prompt=build_smoke_prompt("lightweight"),
        )
    )

    assert response.deployment == "gpt-5-mini"
    assert response.model_identifier == "gpt-5-mini-2026-01-01"
    assert response.response_valid is True
    assert sdk.chat.completions.calls == [
        {
            "model": "gpt-5-mini",
            "messages": [{"role": "user", "content": build_smoke_prompt("lightweight")}],
            "response_format": {"type": "json_object"},
        }
    ]


def test_client_marks_invalid_json_without_exposing_response_details() -> None:
    client = FoundryClient(
        settings(),
        sdk_client=FakeSdk(
            SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content="not json"))],
                model="mock-model",
            )
        ),
    )

    response = client.complete(
        FoundryRequest(
            deployment="gpt-5-mini",
            deployment_role="lightweight",
            prompt=build_smoke_prompt("lightweight"),
        )
    )

    assert response.response_valid is False


def test_client_returns_safe_timeout_error() -> None:
    client = FoundryClient(settings(), sdk_client=FakeSdk(TimeoutError("internal endpoint detail")))

    with pytest.raises(FoundryClientError, match="Foundry request timed out"):
        client.complete(
            FoundryRequest(
                deployment="gpt-5-mini",
                deployment_role="lightweight",
                prompt=build_smoke_prompt("lightweight"),
            )
        )


def test_settings_keep_api_key_secret_and_deployments_are_typed() -> None:
    configured = settings()

    assert str(configured.foundry_api_key) == "**********"
    assert configured.deployments() == (
        ("gpt-5-mini", "lightweight"),
        ("gpt-5.4", "frontier"),
        ("agent-router-managed", "managed_router"),
    )
