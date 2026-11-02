"""Run the three Stage 4 routing strategies against synthetic requests."""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from time import perf_counter

from agent_harness.foundry import FoundryClient, FoundrySettings
from agent_harness.foundry.client import FoundryClientError
from agent_harness.routing.cases import ROUTING_CASES
from agent_harness.routing.models import RoutingEvaluationResult
from agent_harness.routing.policy import fallback_decision
from agent_harness.routing.strategies import (
    ExplicitRoutingStrategy,
    HybridRoutingStrategy,
    ManagedRoutingStrategy,
)


ARTIFACT_PATH = Path("artifacts/stage4_routing_results.json")
COMPARISON_PATH = Path("docs/stage4_routing_comparison.md")


def main() -> int:
    settings = FoundrySettings()
    client = FoundryClient(settings)
    strategies = (
        ExplicitRoutingStrategy(client, settings),
        ManagedRoutingStrategy(client, settings),
        HybridRoutingStrategy(client, settings),
    )
    results = [
        _evaluate(strategy, case)
        for strategy in strategies
        for case in ROUTING_CASES
    ]
    _write_artifact(results)
    _write_comparison(results, settings)
    failures = [result for result in results if result.sanitized_failure]
    print(f"Routing evaluations: {len(results) - len(failures)}/{len(results)} completed")
    return 0 if not failures else 1


def _evaluate(strategy: object, case: object) -> RoutingEvaluationResult:
    started_at = perf_counter()
    try:
        outcome = strategy.route(case)  # type: ignore[attr-defined]
    except FoundryClientError as error:
        decision = fallback_decision("unavailable")
        return RoutingEvaluationResult(
            strategy=strategy.name,  # type: ignore[attr-defined]
            request_id=case.request_id,  # type: ignore[attr-defined]
            expected_route=case.expected_route,  # type: ignore[attr-defined]
            actual_route=decision.route,
            route_correct=decision.route == case.expected_route,  # type: ignore[attr-defined]
            confidence=decision.confidence,
            selected_deployment=decision.selected_deployment,
            latency_ms=_elapsed_ms(started_at),
            policy_override="foundry_failure",
            sanitized_failure=str(error),
        )
    return RoutingEvaluationResult(
        strategy=strategy.name,  # type: ignore[attr-defined]
        request_id=case.request_id,  # type: ignore[attr-defined]
        expected_route=case.expected_route,  # type: ignore[attr-defined]
        actual_route=outcome.decision.route,
        route_correct=outcome.decision.route == case.expected_route,  # type: ignore[attr-defined]
        confidence=outcome.decision.confidence,
        selected_deployment=outcome.decision.selected_deployment,
        underlying_model=outcome.underlying_model,
        latency_ms=_elapsed_ms(started_at),
        token_usage=outcome.token_usage,
        policy_override=outcome.policy_override,
        validation_error=outcome.validation_error,
    )


def _write_artifact(results: list[RoutingEvaluationResult]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    ARTIFACT_PATH.write_text(
        json.dumps([result.model_dump(mode="json") for result in results], indent=2) + "\n"
    )


def _write_comparison(
    results: list[RoutingEvaluationResult],
    settings: FoundrySettings,
) -> None:
    grouped: dict[str, list[RoutingEvaluationResult]] = defaultdict(list)
    for result in results:
        grouped[result.strategy].append(result)

    lines = [
        "# Stage 4 routing comparison",
        "",
        "## Configuration used",
        "",
        "- Authentication mode: API key (value withheld)",
        "- Foundry endpoint: configured (value withheld)",
        f"- Lightweight deployment: `{settings.foundry_light_deployment}`",
        f"- Frontier deployment: `{settings.foundry_frontier_deployment}`",
        f"- Managed router deployment: `{settings.foundry_router_deployment}`",
        "- System-one threshold: 0.85",
        "- Human-review threshold: below 0.60",
        "",
        "## Summary",
        "",
        "| Strategy | Route accuracy | Average latency (ms) | Overrides | Failures |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for strategy, entries in grouped.items():
        accuracy = sum(entry.route_correct for entry in entries) / len(entries)
        average_latency = sum(entry.latency_ms for entry in entries) / len(entries)
        overrides = sum(entry.policy_override is not None for entry in entries)
        failures = sum(entry.sanitized_failure is not None for entry in entries)
        lines.append(
            f"| {strategy} | {accuracy:.0%} | {average_latency:.0f} | {overrides} | {failures} |"
        )

    router_models = sorted(
        {
            result.underlying_model
            for result in results
            if result.strategy == "option_b_managed" and result.underlying_model
        }
    )
    overrides = sorted({result.policy_override for result in results if result.policy_override})
    failures = [result for result in results if result.sanitized_failure]
    router_model_lines = [f"- `{model}`" for model in router_models] or ["- None returned"]
    override_lines = [f"- `{override}`" for override in overrides] or ["- None"]
    failure_lines = [
        f"- {failure.strategy}/{failure.request_id}: {failure.sanitized_failure}"
        for failure in failures
    ] or ["- None"]
    lines.extend(
        [
            "",
            "## Managed-router model selections",
            "",
            *router_model_lines,
            "",
            "## Safety-rule overrides",
            "",
            *override_lines,
            "",
            "## Failures",
            "",
            *failure_lines,
            "",
            "## Initial recommendation",
            "",
            "Use Option C (hybrid) as the initial candidate when it has the best route "
            "accuracy, while retaining Option A as the audit-friendly baseline. Re-evaluate "
            "both with a larger production-like benchmark; this pass does not estimate cost.",
            "",
        ]
    )
    COMPARISON_PATH.write_text("\n".join(lines))


def _elapsed_ms(started_at: float) -> int:
    return int((perf_counter() - started_at) * 1000)


if __name__ == "__main__":
    raise SystemExit(main())
