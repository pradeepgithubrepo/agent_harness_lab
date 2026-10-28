"""Typed synthetic Databricks incident data; no real resources or credentials."""

from __future__ import annotations

from pydantic import BaseModel


class SimulatedDatabricksTimeout(RuntimeError):
    pass


class JobStatus(BaseModel):
    job_id: str
    run_id: str
    status: str
    failed_task: str | None = None
    logical_duration_minutes: int = 0


class ActivityResult(BaseModel):
    summary: str
    logical_duration_minutes: int
    artifact_reference: str
