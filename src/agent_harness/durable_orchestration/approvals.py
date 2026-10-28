from __future__ import annotations

from datetime import datetime

from .state import ApprovalDecision, ApprovalEvent, IncidentStage


class ApprovalValidationError(ValueError):
    pass


def validate_approval(state: dict, event: ApprovalEvent, now: datetime) -> None:
    if state["current_stage"] != IncidentStage.AWAITING_APPROVAL.value:
        raise ApprovalValidationError("workflow is not awaiting approval")
    if event.workflow_id != state["workflow_id"] or event.approval_id != state["approval_id"]:
        raise ApprovalValidationError("approval does not match workflow")
    if event.expected_approval_version != state["approval_version"]:
        raise ApprovalValidationError("stale approval version")
    if event.event_id in state.get("processed_approval_event_ids", []):
        raise ApprovalValidationError("duplicate approval event")
    if (
        event.decision != ApprovalDecision.APPROVAL_TIMEOUT
        and datetime.fromisoformat(state["approval_deadline"]) < now
    ):
        raise ApprovalValidationError("approval deadline has passed")
