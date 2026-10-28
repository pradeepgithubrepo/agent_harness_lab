from agent_harness.synthetic_databricks import SyntheticDatabricksClient


def test_duplicate_remediation_key_returns_same_synthetic_operation() -> None:
    client = SyntheticDatabricksClient()
    first = client.rerun_failed_job("daily_sales_refresh", "workflow:rerun:1")
    second = client.rerun_failed_job("daily_sales_refresh", "workflow:rerun:1")
    assert first == second
    assert len(client.operation_results) == 1
