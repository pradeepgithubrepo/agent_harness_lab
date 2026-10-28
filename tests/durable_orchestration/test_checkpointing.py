from datetime import datetime, timezone

from agent_harness.durable_orchestration.checkpointing import sqlite_checkpointer, thread_config
from agent_harness.durable_orchestration.clock import FakeClock
from agent_harness.durable_orchestration.graph import build_incident_graph
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


def test_sqlite_checkpoint_survives_graph_recreation(tmp_path) -> None:
    path = str(tmp_path / "incident.sqlite")
    with sqlite_checkpointer(path) as saver:
        first = build_incident_graph(
            client=SyntheticDatabricksClient(),
            clock=FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
            checkpointer=saver,
        )
        first.invoke(initial("durable"), thread_config("durable"))
    with sqlite_checkpointer(path) as saver:
        second = build_incident_graph(
            client=SyntheticDatabricksClient(),
            clock=FakeClock(datetime(2026, 1, 1, tzinfo=timezone.utc)),
            checkpointer=saver,
        )
        assert second.get_state(thread_config("durable")).values["current_stage"] == "AWAITING_APPROVAL"
