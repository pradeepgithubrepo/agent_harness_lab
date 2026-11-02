"""Explicit, managed, and hybrid Foundry routing strategies."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from pydantic import ValidationError

from agent_harness.foundry.client import FoundryClient, FoundryClientError
from agent_harness.foundry.config import FoundrySettings
from agent_harness.foundry.models import FoundryRequest

from .models import RoutingCase, RoutingDecision, RoutingOutcome
from .policy import apply_safety_policy, fallback_decision


class BaseRoutingStrategy(ABC):
    name: str

    def __init__(self, client: FoundryClient, settings: FoundrySettings) -> None:
        self.client = client
        self.settings = settings

    @abstractmethod
    def route(self, case: RoutingCase) -> RoutingOutcome: ...

    def _classify(self, case: RoutingCase, deployment: str) -> RoutingOutcome:
        try:
            response = self.client.complete_json(
                FoundryRequest(
                    deployment=deployment,
                    deployment_role="routing_classifier",
                    prompt=_classification_prompt(case, deployment),
                )
            )
            raw_decision = RoutingDecision.model_validate(json.loads(response.content))
        except (FoundryClientError, json.JSONDecodeError, ValidationError):
            return RoutingOutcome(
                decision=fallback_decision(deployment),
                policy_override="invalid_classifier_output",
                validation_error="Classifier response did not match RoutingDecision.",
            )

        decision, override = apply_safety_policy(case, raw_decision)
        return RoutingOutcome(
            decision=decision,
            underlying_model=response.model_identifier,
            token_usage=response.token_usage,
            policy_override=override,
        )

    def _execute(
        self,
        case: RoutingCase,
        outcome: RoutingOutcome,
        deployment: str,
    ) -> RoutingOutcome:
        decision = outcome.decision.model_copy(update={"selected_deployment": deployment})
        if decision.route == "human_review":
            return outcome.model_copy(update={"decision": decision})
        try:
            response = self.client.complete_json(
                FoundryRequest(
                    deployment=deployment,
                    deployment_role="routing_execution",
                    prompt=_execution_prompt(case),
                )
            )
        except FoundryClientError:
            raise
        return outcome.model_copy(
            update={
                "decision": decision,
                "underlying_model": response.model_identifier or outcome.underlying_model,
                "token_usage": _merge_usage(outcome.token_usage, response.token_usage),
            }
        )


class ExplicitRoutingStrategy(BaseRoutingStrategy):
    """Option A: mini classifier, then mini or frontier execution."""

    name = "option_a_explicit"

    def route(self, case: RoutingCase) -> RoutingOutcome:
        outcome = self._classify(case, self.settings.foundry_light_deployment)
        deployment = (
            self.settings.foundry_light_deployment
            if outcome.decision.route == "system_one"
            else self.settings.foundry_frontier_deployment
        )
        return self._execute(case, outcome, deployment)


class ManagedRoutingStrategy(BaseRoutingStrategy):
    """Option B: the managed router receives the request directly."""

    name = "option_b_managed"

    def route(self, case: RoutingCase) -> RoutingOutcome:
        outcome = self._classify(case, self.settings.foundry_router_deployment)
        return outcome.model_copy(
            update={
                "decision": outcome.decision.model_copy(
                    update={"selected_deployment": self.settings.foundry_router_deployment}
                )
            }
        )


class HybridRoutingStrategy(BaseRoutingStrategy):
    """Option C: mini classifier, then mini or managed-router execution."""

    name = "option_c_hybrid"

    def route(self, case: RoutingCase) -> RoutingOutcome:
        outcome = self._classify(case, self.settings.foundry_light_deployment)
        deployment = (
            self.settings.foundry_light_deployment
            if outcome.decision.route == "system_one"
            else self.settings.foundry_router_deployment
        )
        return self._execute(case, outcome, deployment)


def _classification_prompt(case: RoutingCase, selected_deployment: str) -> str:
    return (
        "Return only a JSON RoutingDecision with keys route, confidence, risk_level, "
        "reason_code, selected_deployment, approval_required. Routes are system_one, "
        "system_two, human_review. Use system_one only for a read-only single-target "
        "lookup; use system_two for ambiguity or multiple steps; use human_review for "
        "state changes, approval, or bypass. "
        f"Request ID: {case.request_id}. Request: {case.request}. "
        f"Use selected_deployment='{selected_deployment}'."
    )


def _execution_prompt(case: RoutingCase) -> str:
    return (
        "This is a routing execution smoke check only. Do not call tools or change state. "
        "Return JSON with status='ok' and request_id matching the supplied request. "
        f"request_id='{case.request_id}'. Request: {case.request}"
    )


def _merge_usage(
    first: dict[str, int] | None,
    second: dict[str, int] | None,
) -> dict[str, int] | None:
    if first is None and second is None:
        return None
    return {
        key: (first or {}).get(key, 0) + (second or {}).get(key, 0)
        for key in {"input_tokens", "output_tokens", "total_tokens"}
    }
