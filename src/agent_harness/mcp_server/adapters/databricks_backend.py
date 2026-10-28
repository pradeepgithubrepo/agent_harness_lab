"""Read-only Databricks adapter using application OAuth credentials."""
from __future__ import annotations

from databricks.sdk import WorkspaceClient

from ..config import ApplicationSettings


class DatabricksReadOnlyBackend:
    def __init__(self, settings: ApplicationSettings) -> None:
        settings.validate_selected_backend()
        self._client = WorkspaceClient(
            host=settings.databricks_host,
            client_id=settings.databricks_client_id,
            client_secret=settings.databricks_client_secret.get_secret_value(),
            auth_type=settings.databricks_auth_type,
            product="agent-harness-lab",
            product_version="0.1.0",
        )

    def validate_read_access(self) -> dict[str, object]:
        """Safely list at most one job; never modifies the workspace."""
        job = next(iter(self._client.jobs.list(limit=1)), None)
        return {"connected": True, "job_metadata_read": job is not None}
