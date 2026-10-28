from datetime import datetime, timedelta, timezone

from agent_harness.durable_orchestration.approvals import validate_approval
from agent_harness.durable_orchestration.state import ApprovalDecision, ApprovalEvent


def test_logical_three_day_timeout_is_accepted() -> None:
    now = datetime(2026, 1, 4, tzinfo=timezone.utc)
    state = {
        "workflow_id": "w", "current_stage": "AWAITING_APPROVAL",
        "approval_id": "a", "approval_version": 1,
        "approval_deadline": (now - timedelta(seconds=1)).isoformat(),
        "processed_approval_event_ids": [],
    }
    event = ApprovalEvent(event_id="timeout", workflow_id="w", approval_id="a", expected_approval_version=1, decision=ApprovalDecision.APPROVAL_TIMEOUT, actor_id="clock", submitted_at=now)
    validate_approval(state, event, now)
