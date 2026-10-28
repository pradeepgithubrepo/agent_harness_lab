from datetime import datetime, timezone

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from agent_harness.durable_orchestration import (
    ApprovalDecision, ApprovalEvent, build_incident_graph, thread_config,
)
from agent_harness.durable_orchestration.clock import FakeClock
from agent_harness.synthetic_databricks import SyntheticDatabricksClient


def initial(workflow_id: str) -> dict:
    return {
        "workflow_id": workflow_id, "incident_id": "incident-1",
        "current_stage": "RECEIVED", "status": "RECEIVED",
        "completed_steps": [], "retry_counts": {}, "environment": "DEV",
        "databricks_job_id": "daily_sales_refresh", "approval_version": 0,
        "evidence_references": [], "artifact_references": [],
        "executed_operation_keys": [], "processed_approval_event_ids": [],
        "logical_elapsed_minutes": 0, "created_at": "now", "updated_at": "now",
    }


def test_timeout_retry_approval_remediation_and_recovery() -> None:
    clock = FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc))
    client = SyntheticDatabricksClient()
    graph = build_incident_graph(client=client, clock=clock, checkpointer=InMemorySaver())
    config = thread_config("workflow-1")
    paused = graph.invoke(initial("workflow-1"), config)
    assert paused["current_stage"] == "AWAITING_APPROVAL"
    assert paused["retry_counts"] == {"get_job_status": 1}
    event = ApprovalEvent(
        event_id="approve-1", workflow_id="workflow-1", approval_id=paused["approval_id"],
        expected_approval_version=1, decision=ApprovalDecision.APPROVE,
        actor_id="synthetic-human", submitted_at=clock.now(),
    )
    resolved = graph.invoke(Command(resume=event.model_dump(mode="json")), config)
    assert resolved["current_stage"] == "RESOLVED"
    assert resolved["logical_elapsed_minutes"] == 240
    assert len(resolved["executed_operation_keys"]) == 1
