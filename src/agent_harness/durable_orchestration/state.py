"""Lean, checkpointed incident state."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TypedDict

from pydantic import BaseModel


class IncidentStage(StrEnum):
    RECEIVED = "RECEIVED"
    TRIAGING = "TRIAGING"
    INVESTIGATING = "INVESTIGATING"
    DIAGNOSIS_READY = "DIAGNOSIS_READY"
    AWAITING_APPROVAL = "AWAITING_APPROVAL"
    REMEDIATING = "REMEDIATING"
    VERIFYING = "VERIFYING"
    RESOLVED = "RESOLVED"
    REJECTED = "REJECTED"
    CHANGES_REQUESTED = "CHANGES_REQUESTED"
    ESCALATED = "ESCALATED"
    FAILED = "FAILED"


class ApprovalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"
    REQUEST_CHANGES = "REQUEST_CHANGES"
    APPROVAL_TIMEOUT = "APPROVAL_TIMEOUT"


class ApprovalEvent(BaseModel):
    event_id: str
    workflow_id: str
    approval_id: str
    expected_approval_version: int
    decision: ApprovalDecision
    actor_id: str
    submitted_at: datetime
    comment: str | None = None


class ArtifactReference(BaseModel):
    reference_id: str
    reference_type: str
    source: str
    version: str


class IncidentState(TypedDict, total=False):
    workflow_id: str
    incident_id: str
    current_stage: str
    status: str
    completed_steps: list[str]
    attempt_count: int
    retry_counts: dict[str, int]
    environment: str
    databricks_job_id: str
    databricks_run_id: str
    diagnosis_summary: str
    proposed_action: str
    latest_error: str | None
    approval_status: str | None
    approval_id: str | None
    approval_version: int
    approval_requested_at: str | None
    approval_deadline: str | None
    evidence_references: list[dict[str, str]]
    artifact_references: list[dict[str, str]]
    executed_operation_keys: list[str]
    processed_approval_event_ids: list[str]
    logical_elapsed_minutes: int
    created_at: str
    updated_at: str
