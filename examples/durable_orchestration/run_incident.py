"""Start the synthetic incident and pause at the durable approval gate."""
from datetime import datetime, timezone

from agent_harness.durable_orchestration import build_incident_graph, sqlite_checkpointer, thread_config
from agent_harness.durable_orchestration.clock import SystemClock
from agent_harness.synthetic_databricks import SyntheticDatabricksClient


def main() -> None:
    workflow_id = "demo-incident"
    state = {"workflow_id": workflow_id, "incident_id": "gold-sales-stale", "current_stage": "RECEIVED", "status": "RECEIVED", "completed_steps": [], "retry_counts": {}, "environment": "DEV", "databricks_job_id": "daily_sales_refresh", "approval_version": 0, "evidence_references": [], "artifact_references": [], "executed_operation_keys": [], "processed_approval_event_ids": [], "logical_elapsed_minutes": 0, "created_at": datetime.now(timezone.utc).isoformat(), "updated_at": datetime.now(timezone.utc).isoformat()}
    with sqlite_checkpointer("incident-demo.sqlite") as saver:
        result = build_incident_graph(client=SyntheticDatabricksClient(), clock=SystemClock(), checkpointer=saver).invoke(state, thread_config(workflow_id))
    for key in ("workflow_id", "current_stage", "completed_steps", "retry_counts", "diagnosis_summary", "approval_id", "approval_deadline", "logical_elapsed_minutes"):
        print(f"{key}: {result.get(key)}")
    print("checkpoint: incident-demo.sqlite")


if __name__ == "__main__":
    main()
