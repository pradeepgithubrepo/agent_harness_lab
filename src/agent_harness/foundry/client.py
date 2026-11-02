"""One reusable client for all configured Microsoft Foundry deployments."""

from __future__ import annotations

import json
from typing import Any

from openai import APIConnectionError, APIStatusError, APITimeoutError, AuthenticationError, OpenAI

from .auth import ApiKeyAuthenticationProvider, FoundryAuthenticationProvider
from .config import FoundrySettings
from .models import FoundryRequest, FoundryResponse


class FoundryClientError(RuntimeError):
    """Safe error category intended for callers and smoke-test artifacts."""


class FoundryClient:
    """Calls a deployment through the Foundry project's OpenAI v1 API."""

    def __init__(
        self,
        settings: FoundrySettings,
        auth_provider: FoundryAuthenticationProvider | None = None,
        sdk_client: OpenAI | Any | None = None,
    ) -> None:
        self._settings = settings
        self._auth_provider = auth_provider or ApiKeyAuthenticationProvider()
        self._sdk = sdk_client or self._auth_provider.create_sdk_client(settings)

    def complete(self, request: FoundryRequest) -> FoundryResponse:
        """Submit a minimal request and validate the returned JSON contract."""
        result = self._call(request)
        return FoundryResponse(
            deployment=request.deployment,
            model_identifier=result["model_identifier"],
            content=result["content"],
            response_valid=_is_expected_smoke_response(result["content"], request.deployment_role),
            token_usage=result["token_usage"],
        )

    def complete_json(self, request: FoundryRequest) -> FoundryResponse:
        """Submit a request expected to return a JSON object."""
        result = self._call(request)
        return FoundryResponse(
            deployment=request.deployment,
            model_identifier=result["model_identifier"],
            content=result["content"],
            response_valid=_is_json_object(result["content"]),
            token_usage=result["token_usage"],
        )

    def _call(self, request: FoundryRequest) -> dict[str, Any]:
        try:
            result = self._sdk.chat.completions.create(
                model=request.deployment,
                messages=[{"role": "user", "content": request.prompt}],
                response_format={"type": "json_object"},
            )
        except (APITimeoutError, TimeoutError) as error:
            raise FoundryClientError("Foundry request timed out.") from error
        except AuthenticationError as error:
            raise FoundryClientError("Foundry authentication failed.") from error
        except APIConnectionError as error:
            raise FoundryClientError("Foundry connection failed.") from error
        except APIStatusError as error:
            raise FoundryClientError(
                f"Foundry request failed with HTTP status {error.status_code}."
            ) from error
        except Exception as error:
            raise FoundryClientError("Foundry request failed.") from error

        choices = getattr(result, "choices", None)
        content = (
            getattr(getattr(choices[0], "message", None), "content", None)
            if isinstance(choices, list) and choices
            else None
        )
        if not isinstance(content, str) or not content.strip():
            raise FoundryClientError("Foundry returned no textual response.")

        usage = getattr(result, "usage", None)
        token_usage = None
        if usage is not None:
            token_usage = {
                key: value
                for key, value in {
                    "input_tokens": getattr(usage, "prompt_tokens", None),
                    "output_tokens": getattr(usage, "completion_tokens", None),
                    "total_tokens": getattr(usage, "total_tokens", None),
                }.items()
                if isinstance(value, int)
            } or None
        return {
            "content": content,
            "model_identifier": getattr(result, "model", None),
            "token_usage": token_usage,
        }


def build_smoke_prompt(deployment_role: str) -> str:
    """The single, minimal connectivity prompt used for every deployment."""
    return (
        "Return JSON with status='ok' and identify the deployment role supplied "
        f"in the prompt. deployment_role='{deployment_role}'"
    )


def _is_expected_smoke_response(content: str, deployment_role: str) -> bool:
    try:
        payload = json.loads(content)
    except json.JSONDecodeError:
        return False
    return (
        isinstance(payload, dict)
        and payload.get("status") == "ok"
        and payload.get("deployment_role") == deployment_role
    )


def _is_json_object(content: str) -> bool:
    try:
        return isinstance(json.loads(content), dict)
    except json.JSONDecodeError:
        return False
