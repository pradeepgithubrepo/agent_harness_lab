"""Failure-prone synthetic operations, separated from graph transitions."""

from agent_harness.synthetic_databricks import SyntheticDatabricksClient


def get_job_status(client: SyntheticDatabricksClient, job_id: str):
    return client.get_job_status(job_id)


def get_failed_task_summary(client: SyntheticDatabricksClient, run_id: str):
    return client.get_failed_task_summary(run_id)


def create_diagnosis() -> str:
    return "daily_sales_refresh failed because an expected source field is missing"


def create_approval_request(workflow_id: str, version: int) -> str:
    return f"approval:{workflow_id}:{version}"


def rerun_failed_job(client: SyntheticDatabricksClient, job_id: str, key: str):
    return client.rerun_failed_job(job_id, key)


def verify_job_success(client: SyntheticDatabricksClient, job_id: str):
    return client.verify_job_success(job_id)


def verify_table_freshness(client: SyntheticDatabricksClient, table: str):
    return client.verify_table_freshness(table)
