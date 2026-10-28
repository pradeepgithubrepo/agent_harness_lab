"""One durable LangGraph workflow for the synthetic Databricks incident."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import interrupt

from agent_harness.context_assembler import ContextAssemblyConfig, ContextRuntime
from agent_harness.durable_orchestration import activities
from agent_harness.durable_orchestration.approvals import validate_approval
from agent_harness.durable_orchestration.clock import Clock
from agent_harness.durable_orchestration.state import (
    ApprovalDecision,
    ApprovalEvent,
    IncidentStage,
    IncidentState,
)
from agent_harness.synthetic_databricks import SimulatedDatabricksTimeout, SyntheticDatabricksClient
from agent_harness.synthetic_databricks.scenarios import TABLE_NAME


def build_incident_graph(
    *,
    client: SyntheticDatabricksClient,
    clock: Clock,
    diagnosis_agent: Any | None = None,
    checkpointer: Any = None,
    interrupt_after: list[str] | None = None,
):
    graph = StateGraph(IncidentState)

    def receive_incident(state: IncidentState) -> dict:
        return _update(state, IncidentStage.TRIAGING, "receive_incident", 10)

    def triage_incident(state: IncidentState) -> dict:
        return _update(state, IncidentStage.INVESTIGATING, "triage_incident", 10)

    def investigate_incident(state: IncidentState) -> dict:
        retries = dict(state.get("retry_counts", {}))
        try:
            status = activities.get_job_status(client, state["databricks_job_id"])
        except SimulatedDatabricksTimeout as error:
            retries["get_job_status"] = retries.get("get_job_status", 0) + 1
            if retries["get_job_status"] > 2:
                return _update(state, IncidentStage.FAILED, "investigate_failed", 0, retry_counts=retries, latest_error=str(error))
            return _update(state, IncidentStage.INVESTIGATING, "get_job_status_retry", 0, retry_counts=retries, latest_error=str(error))
        evidence = activities.get_failed_task_summary(client, status.run_id)
        return _update(
            state, IncidentStage.DIAGNOSIS_READY, "investigate_incident", status.logical_duration_minutes,
            databricks_run_id=status.run_id, latest_error=None,
            evidence_references=[*state.get("evidence_references", []), {"reference_id": evidence.artifact_reference, "reference_type": "EVIDENCE", "source": "synthetic", "version": "v1"}],
        )

    def prepare_diagnosis(state: IncidentState) -> dict:
        if diagnosis_agent is not None:
            runtime = ContextRuntime(
                request_id=state["workflow_id"], agent_role="Builder", task_type="incident_diagnosis",
                workflow_state={"incident_id": state["incident_id"], "stage": state["current_stage"], "environment": state["environment"], "job_id": state["databricks_job_id"], "run_id": state.get("databricks_run_id")},
                context_items=[], permitted_tool_names=set(),
                config=ContextAssemblyConfig(model_context_limit=1000, application_operating_limit=1000, reserved_output_tokens=200, safety_margin_tokens=100),
            )
            diagnosis_agent.invoke({"messages": [HumanMessage(content="Prepare a concise synthetic incident diagnosis.")]}, context=runtime)
        diagnosis = activities.create_diagnosis()
        return _update(state, IncidentStage.DIAGNOSIS_READY, "prepare_diagnosis", 50, diagnosis_summary=diagnosis, proposed_action="rerun failed synthetic job after approval")

    def request_approval(state: IncidentState) -> dict:
        version = state.get("approval_version", 0) + 1
        approval_id = activities.create_approval_request(state["workflow_id"], version)
        now = clock.now()
        return _update(state, IncidentStage.AWAITING_APPROVAL, "request_approval", 10, approval_id=approval_id, approval_version=version, approval_status="PENDING", approval_requested_at=now.isoformat(), approval_deadline=(now + timedelta(days=3)).isoformat())

    def process_approval(state: IncidentState) -> dict:
        raw_event = interrupt({"approval_id": state["approval_id"], "approval_version": state["approval_version"], "deadline": state["approval_deadline"]})
        event = ApprovalEvent.model_validate(raw_event)
        validate_approval(state, event, clock.now())
        updates = {"approval_status": event.decision.value, "processed_approval_event_ids": [*state.get("processed_approval_event_ids", []), event.event_id]}
        if event.decision == ApprovalDecision.APPROVE:
            return _update(state, IncidentStage.REMEDIATING, "approval_approved", 0, **updates)
        if event.decision == ApprovalDecision.REJECT:
            return _update(state, IncidentStage.REJECTED, "approval_rejected", 0, **updates)
        if event.decision == ApprovalDecision.REQUEST_CHANGES:
            return _update(state, IncidentStage.INVESTIGATING, "approval_changes_requested", 0, **updates)
        return _update(state, IncidentStage.ESCALATED, "approval_timed_out", 0, **updates)

    def remediate_incident(state: IncidentState) -> dict:
        key = f"{state['workflow_id']}:rerun_failed_job:{state['approval_version']}"
        result = activities.rerun_failed_job(client, state["databricks_job_id"], key)
        return _update(state, IncidentStage.VERIFYING, "remediate_incident", result.logical_duration_minutes, executed_operation_keys=[*state.get("executed_operation_keys", []), key] if key not in state.get("executed_operation_keys", []) else state.get("executed_operation_keys", []))

    def verify_recovery(state: IncidentState) -> dict:
        job = activities.verify_job_success(client, state["databricks_job_id"])
        table = activities.verify_table_freshness(client, TABLE_NAME)
        return _update(state, IncidentStage.RESOLVED, "verify_recovery", job.logical_duration_minutes + table.logical_duration_minutes)

    def close_incident(state: IncidentState) -> dict:
        return _update(state, IncidentStage.RESOLVED, "close_incident", 0, status="RESOLVED")

    def escalate_incident(state: IncidentState) -> dict:
        return _update(state, IncidentStage.ESCALATED, "escalate_incident", 0, status="ESCALATED")

    for node in (receive_incident, triage_incident, investigate_incident, prepare_diagnosis, request_approval, process_approval, remediate_incident, verify_recovery, close_incident, escalate_incident):
        graph.add_node(node.__name__, node)
    graph.add_edge(START, "receive_incident")
    graph.add_edge("receive_incident", "triage_incident")
    graph.add_edge("triage_incident", "investigate_incident")
    graph.add_conditional_edges("investigate_incident", lambda state: "investigate_incident" if state["current_stage"] == IncidentStage.INVESTIGATING.value else "prepare_diagnosis")
    graph.add_edge("prepare_diagnosis", "request_approval")
    graph.add_edge("request_approval", "process_approval")
    graph.add_conditional_edges("process_approval", lambda state: {
        IncidentStage.REMEDIATING.value: "remediate_incident",
        IncidentStage.REJECTED.value: END,
        IncidentStage.INVESTIGATING.value: "investigate_incident",
        IncidentStage.ESCALATED.value: "escalate_incident",
    }[state["current_stage"]])
    graph.add_edge("remediate_incident", "verify_recovery")
    graph.add_edge("verify_recovery", "close_incident")
    graph.add_edge("close_incident", END)
    graph.add_edge("escalate_incident", END)
    return graph.compile(checkpointer=checkpointer, interrupt_after=interrupt_after or [])


def _update(state: IncidentState, stage: IncidentStage, step: str, minutes: int, **changes: Any) -> dict:
    completed = [*state.get("completed_steps", [])]
    if step not in completed:
        completed.append(step)
    return {
        **changes,
        "current_stage": stage.value,
        "status": stage.value,
        "completed_steps": completed,
        "logical_elapsed_minutes": state.get("logical_elapsed_minutes", 0) + minutes,
        "updated_at": changes.get("updated_at", state.get("updated_at", "")),
    }
