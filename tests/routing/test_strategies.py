from __future__ import annotations

import json

from pydantic import SecretStr

from agent_harness.foundry.config import FoundrySettings
from agent_harness.foundry.models import FoundryResponse
from agent_harness.routing.models import RoutingCase
from agent_harness.routing.strategies import ExplicitRoutingStrategy, HybridRoutingStrategy


class FakeFoundryClient:
    def __init__(self, decision: dict[str, object]) -> None:
        self.decision = decision
        self.deployments: list[str] = []

    def complete_json(self, request: object) -> FoundryResponse:
        self.deployments.append(request.deployment)
        is_classifier = request.deployment_role == "routing_classifier"
        return FoundryResponse(
            deployment=request.deployment,
            model_identifier=f"{request.deployment}-model",
            content=json.dumps(self.decision if is_classifier else {"status": "ok"}),
            response_valid=True,
            token_usage={"total_tokens": 10},
        )


def settings() -> FoundrySettings:
    return FoundrySettings(
        foundry_endpoint="https://foundry.example.invalid/api/projects/test",
        foundry_api_key=SecretStr("nonsecret-placeholder"),
        foundry_light_deployment="gpt-5-mini",
        foundry_frontier_deployment="gpt-5.4",
        foundry_router_deployment="agent-router-managed",
    )


def high_confidence_system_one() -> dict[str, object]:
    return {
        "route": "system_one",
        "confidence": 0.95,
        "risk_level": "low",
        "reason_code": "simple_lookup",
        "selected_deployment": "gpt-5-mini",
        "approval_required": False,
    }


def test_explicit_strategy_uses_frontier_for_investigation() -> None:
    client = FakeFoundryClient(high_confidence_system_one())
    strategy = ExplicitRoutingStrategy(client, settings())
    case = RoutingCase(
        request_id="investigation",
        category="investigation",
        request="Investigate two sources.",
        expected_route="system_two",
    )

    outcome = strategy.route(case)

    assert outcome.decision.route == "system_two"
    assert outcome.decision.selected_deployment == "gpt-5.4"
    assert outcome.policy_override == "investigation_or_ambiguity"
    assert client.deployments == ["gpt-5-mini", "gpt-5.4"]


def test_hybrid_strategy_never_executes_state_change() -> None:
    client = FakeFoundryClient(high_confidence_system_one())
    strategy = HybridRoutingStrategy(client, settings())
    case = RoutingCase(
        request_id="state-change",
        category="state_change",
        request="Record a result.",
        expected_route="human_review",
    )

    outcome = strategy.route(case)

    assert outcome.decision.route == "human_review"
    assert outcome.decision.approval_required is True
    assert outcome.policy_override == "state_change_or_approval"
    assert client.deployments == ["gpt-5-mini"]
