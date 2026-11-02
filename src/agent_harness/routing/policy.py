"""Server-side routing safety rules; model output never bypasses this policy."""

from __future__ import annotations

from .models import RoutingCase, RoutingDecision

SYSTEM_ONE_THRESHOLD = 0.85
HUMAN_REVIEW_THRESHOLD = 0.60


def apply_safety_policy(
    case: RoutingCase,
    decision: RoutingDecision,
) -> tuple[RoutingDecision, str | None]:
    """Return a safe decision and a policy override reason when needed."""
    if decision.confidence < HUMAN_REVIEW_THRESHOLD:
        return _override(decision, "human_review", "low_confidence", True), "low_confidence"
    if case.category == "state_change":
        return _override(decision, "human_review", "state_change_or_approval", True), "state_change_or_approval"
    if case.category in {"ambiguous", "investigation"}:
        return _override(decision, "system_two", "investigation_or_ambiguity", False), "investigation_or_ambiguity"
    if decision.route != "system_one" or decision.confidence < SYSTEM_ONE_THRESHOLD:
        return _override(decision, "system_two", "system_one_threshold_not_met", False), "system_one_threshold_not_met"
    return decision, None


def fallback_decision(selected_deployment: str) -> RoutingDecision:
    """Safe result used when model output cannot be parsed or validated."""
    return RoutingDecision(
        route="human_review",
        confidence=0.0,
        risk_level="high",
        reason_code="invalid_or_missing_classifier_output",
        selected_deployment=selected_deployment,
        approval_required=True,
    )


def _override(
    decision: RoutingDecision,
    route: str,
    reason_code: str,
    approval_required: bool,
) -> RoutingDecision:
    return decision.model_copy(
        update={
            "route": route,
            "reason_code": reason_code,
            "approval_required": approval_required,
            "risk_level": (
                "high"
                if route == "human_review"
                else "medium"
                if decision.risk_level == "low"
                else decision.risk_level
            ),
        }
    )
