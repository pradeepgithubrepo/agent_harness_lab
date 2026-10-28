"""Deterministic local activity adapter for the Stage 2 incident scenario."""

from __future__ import annotations

from .models import ActivityResult, JobStatus, SimulatedDatabricksTimeout


class SyntheticDatabricksClient:
    """Fixture-driven operations with deterministic timeout and idempotency."""

    def __init__(self) -> None:
        self.status_attempts = 0
        self.operation_results: dict[str, ActivityResult] = {}

    def get_job_status(self, job_id: str) -> JobStatus:
        self.status_attempts += 1
        if self.status_attempts == 1:
            raise SimulatedDatabricksTimeout("synthetic Databricks API timeout")
        return JobStatus(
            job_id=job_id,
            run_id="run-daily-sales-001",
            status="FAILED",
            failed_task="silver_sales_transform",
            logical_duration_minutes=70,
        )

    def get_failed_task_summary(self, run_id: str) -> ActivityResult:
        return ActivityResult(
            summary=f"{run_id}: expected source field is missing",
            logical_duration_minutes=0,
            artifact_reference="evidence:failed-task-summary:v1",
        )

    def rerun_failed_job(self, job_id: str, idempotency_key: str) -> ActivityResult:
        if idempotency_key not in self.operation_results:
            self.operation_results[idempotency_key] = ActivityResult(
                summary=f"{job_id} rerun completed successfully",
                logical_duration_minutes=50,
                artifact_reference="tool-result:rerun:v1",
            )
        return self.operation_results[idempotency_key]

    def verify_job_success(self, job_id: str) -> ActivityResult:
        return ActivityResult(
            summary=f"{job_id} succeeded",
            logical_duration_minutes=20,
            artifact_reference="validation:job-success:v1",
        )

    def verify_table_freshness(self, table: str) -> ActivityResult:
        return ActivityResult(
            summary=f"{table} freshness restored",
            logical_duration_minutes=20,
            artifact_reference="validation:table-freshness:v1",
        )
