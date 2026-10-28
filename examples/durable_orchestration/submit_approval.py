"""Resume a saved workflow with a synthetic human decision."""
import argparse
from datetime import datetime, timezone

from langgraph.types import Command

from agent_harness.durable_orchestration import (
    ApprovalDecision, ApprovalEvent, build_incident_graph, sqlite_checkpointer, thread_config,
)
from agent_harness.durable_orchestration.clock import SystemClock
from agent_harness.synthetic_databricks import SyntheticDatabricksClient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("workflow_id")
    parser.add_argument("decision", choices=["approve", "reject", "request_changes"])
    parser.add_argument("--database", default="incident-demo.sqlite")
    args = parser.parse_args()
    config = thread_config(args.workflow_id)
    with sqlite_checkpointer(args.database) as saver:
        graph = build_incident_graph(client=SyntheticDatabricksClient(), clock=SystemClock(), checkpointer=saver)
        state = graph.get_state(config).values
        event = ApprovalEvent(
            event_id=f"{args.workflow_id}:{args.decision}:1",
            workflow_id=args.workflow_id, approval_id=state["approval_id"],
            expected_approval_version=state["approval_version"],
            decision=ApprovalDecision(args.decision.upper()),
            actor_id="synthetic-human", submitted_at=datetime.now(timezone.utc),
        )
        result = graph.invoke(Command(resume=event.model_dump(mode="json")), config)
    print(result["current_stage"])


if __name__ == "__main__":
    main()
