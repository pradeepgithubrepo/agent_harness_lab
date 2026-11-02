"""Smoke-test each configured Microsoft Foundry deployment independently."""

from __future__ import annotations

import json
from pathlib import Path
from time import perf_counter

from pydantic import ValidationError

from agent_harness.foundry import DeploymentSmokeTestResult, FoundryClient, FoundryRequest, FoundrySettings
from agent_harness.foundry.client import FoundryClientError, build_smoke_prompt


ARTIFACT_PATH = Path("artifacts/stage4_foundry_smoke_test.json")
FALLBACK_DEPLOYMENTS = (
    ("gpt-5-mini", "lightweight"),
    ("gpt-5.4", "frontier"),
    ("agent-router-managed", "managed_router"),
)


def main() -> int:
    try:
        settings = FoundrySettings()
    except ValidationError:
        results = [
            DeploymentSmokeTestResult(
                deployment=deployment,
                deployment_role=role,
                success=False,
                latency_ms=0,
                sanitized_error="Foundry configuration is incomplete or invalid.",
            )
            for deployment, role in FALLBACK_DEPLOYMENTS
        ]
        _write_results(results)
        print("Foundry configuration is incomplete or invalid; see sanitized artifact results.")
        return 1

    client = FoundryClient(settings)
    results = [_smoke_test_deployment(client, deployment, role) for deployment, role in settings.deployments()]
    _write_results(results)

    for result in results:
        status = "PASSED" if result.success and result.response_valid else "FAILED"
        print(f"{result.deployment} ({result.deployment_role}): {status}")
    return 0 if all(result.success and result.response_valid for result in results) else 1


def _smoke_test_deployment(
    client: FoundryClient,
    deployment: str,
    deployment_role: str,
) -> DeploymentSmokeTestResult:
    started_at = perf_counter()
    try:
        response = client.complete(
            FoundryRequest(
                deployment=deployment,
                deployment_role=deployment_role,
                prompt=build_smoke_prompt(deployment_role),
            )
        )
    except FoundryClientError as error:
        return DeploymentSmokeTestResult(
            deployment=deployment,
            deployment_role=deployment_role,
            success=False,
            latency_ms=_elapsed_ms(started_at),
            sanitized_error=str(error),
        )
    return DeploymentSmokeTestResult(
        deployment=deployment,
        deployment_role=deployment_role,
        success=True,
        latency_ms=_elapsed_ms(started_at),
        model_identifier=response.model_identifier,
        response_valid=response.response_valid,
        sanitized_error=(
            None if response.response_valid else "Foundry response did not match the smoke-test JSON contract."
        ),
    )


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


def _write_results(results: list[DeploymentSmokeTestResult]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps([result.model_dump(mode="json") for result in results], indent=2) + "\n"
    )


if __name__ == "__main__":
    raise SystemExit(main())
